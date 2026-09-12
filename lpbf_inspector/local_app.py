"""Interface locale LPBF : bibliothèques, analyse, revue et empilement 3D."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import threading

import numpy as np
from PIL import Image

from inspector import VERSION as ENGINE_VERSION, Config, analyze, connect, event_fingerprint, gray_pixels, metadata, summary
from imaging import context_box
from libraries import LibraryCatalog, inventory as scan_inventory
import job_analysis
from job_views import AcquisitionViews
from persistence import minimum_count
from priority import with_priority, priority_value, priority_text, PRIORITY_HELP, review_sort
from shape_reconstruction import shape_preview, MAX_EDGE as SHAPE_EDGE
from reporting import ReportTasks, collect_report, create_report
from http_api import make_handler
from previews import preview
from storage import atomic_json
from source_integrity import verify_source
from copy import deepcopy

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'datasets' / 'nist_sample'


def preferred_source(root):
    expanded = Path(root)/'datasets'/'nist_80_179'
    marker = expanded/'provenance.json'
    if marker.is_file():
        info = json.loads(marker.read_text(encoding='utf-8'))
        if info.get('complete') and info.get('images')==200:
            return expanded
    return Path(root)/'datasets'/'nist_sample'


class Application(ReportTasks,AcquisitionViews):
    def __init__(self, root=ROOT, source=None):
        self.root = Path(root)
        self.catalog=LibraryCatalog(root,source)
        self.lock = threading.RLock()
        self.running = False
        self.stop_event = threading.Event()
        self.progress = {'stage': 'pret', 'done': 0, 'total': None}
        self.error = None
        self.operation='analysis'
        self.revision=0
        self.project = self.root / 'results_nist_16bit'
        settings = self.root/'web_settings.json'
        saved=json.loads(settings.read_text(encoding='utf-8')) if settings.is_file() else {}
        selected=saved.get('library',next(iter(self.catalog.entries)))
        if selected=='aalto':selected=next((key for key in self.catalog.entries if key.startswith('aalto_')), selected)
        if selected not in self.catalog.entries:selected=next(iter(self.catalog.entries))
        self.preferences=saved.get('by_library',{selected:saved})
        self.library=self.catalog.entries[selected]
        self.source=Path(self.library['source'])
        self.config=self.make_config(self.preferences.get(selected,{}))
        self.acquisition_step=self.make_step(self.preferences.get(selected,{}))
        self.min_consecutive=minimum_count(self.preferences.get(selected,{}).get('min_consecutive',1))
        self.gallery=[]
        self.aalto_result=None
        self.gray_calibration=None
        self.dataset=self.inventory()
        self.load_job_results()
        # Les anciens résultats restent dans leur projet. Un jeu étendu a un autre identifiant.
        legacy = self.database()
        try:
            compatible = (legacy is not None
                and metadata(legacy,'definition',{}).get('version')==ENGINE_VERSION
                and metadata(legacy,'definition',{}).get('source')==str(self.source)
                and legacy.execute('SELECT COUNT(*) FROM frames').fetchone()[0]==self.dataset['images']
                and asdict(Config(**metadata(legacy,'definition')['config']))==asdict(self.config))
        finally:
            if legacy:
                legacy.close()
        if not compatible:
            self.project = self.project_for(self.config)

    def inventory(self):
        if self.library.get('empty'):
            return self.describe_inventory({'images':0,'layers':0,'first':None,'last':None,'layer_um':60,
                'fingerprint':'empty-library','bytes':0,'unmatched':0,'empty':True})
        if self.library['mode']=='gallery':
            record=json.loads((self.source/'provenance.json').read_text(encoding='utf-8'))
            fields=('id','name','job','counter','timestamp','width','height')
            # Le moteur ne reçoit ni les labels, ni les rectangles, ni les autres jobs.
            self.gallery=job_analysis.check_records([{k:r[k] for k in fields} for r in record['records'] if r['job']==self.library['job']])
            stamps=[]
            for r in self.gallery:
                path=job_analysis.source_path(self.source,r)
                stat=path.stat() if path.is_file() else None
                stamps.append([r,stat.st_size if stat else None,stat.st_mtime_ns if stat else None])
            info={'images':len(self.gallery),'layers':None,'first':None,'last':None,'layer_um':None,
                  'fingerprint':job_analysis.signature([str(self.source.resolve()),stamps]),'job':self.library['job']}
        else:
            info=scan_inventory(self.source,self.config)
        return self.describe_inventory(info)

    def describe_inventory(self,info):
        return {**info,**{k:self.library.get(k) for k in ('id','name','mode','note','source_url','license')},
                'has_roi':bool(self.library.get('default_roi')),'source':str(self.source),'empty':bool(self.library.get('empty'))}

    def render_preview(self,path,white,crop=None,edge=1400):
        return preview(path,white,crop,edge)

    def save_preferences(self):
        self.preferences[self.library['id']]={'threshold':self.config.min_change_gray,'tile':self.config.tile_px,
                      'region':'parts' if self.config.roi_by_camera else 'full',
                      'analysis_phase':self.config.analysis_phases[0] if len(self.config.analysis_phases)==1 else 'both',
                      'acquisition_step':self.acquisition_step,'min_consecutive':self.min_consecutive}
        atomic_json(self.root/'web_settings.json',{'library':self.library['id'],'by_library':self.preferences})

    def select_library(self,key,_from_import=False):
        with self.lock:
            if self.running and not _from_import:raise ValueError('Wait for processing to finish before switching libraries.')
            if key not in self.catalog.entries:raise ValueError('Unknown library.')
            attributes=('library','source','config','acquisition_step','min_consecutive','gallery','dataset','gray_calibration','aalto_result','project','error','progress','revision','preferences')
            previous={name:getattr(self,name) for name in attributes}
            previous['preferences']=deepcopy(self.preferences)
            try:
                self.save_preferences()
                self.library=self.catalog.entries[key]
                self.source=Path(self.library['source'])
                self.config=self.make_config(self.preferences.get(key,{}))
                self.acquisition_step=self.make_step(self.preferences.get(key,{}))
                self.min_consecutive=minimum_count(self.preferences.get(key,{}).get('min_consecutive',1))
                self.gallery=[]
                self.dataset=self.describe_inventory(self.library['summary']) if self.library.get('summary') else self.inventory()
                self.load_job_results()
                self.project=self.project_for(self.config)
                self.error=None;self.progress={'stage':'pret','done':0,'total':None}
                self.revision+=1;self.save_preferences()
                return self.state()
            except Exception:
                for name,value in previous.items():setattr(self,name,value)
                self._acquisition_events_cache=None;self._persistence_cache=None
                raise

    def import_library(self,data):
        with self.lock:
            if self.running:raise ValueError('Processing is already running.')
            self.running=True;self.operation='import';self.error=None;self.stop_event.clear()
            self.progress={'stage':'inventaire','done':0,'total':None}
        def worker():
            try:
                def progress(**values):
                    with self.lock:self.progress=values
                entry=self.catalog.add(data,progress,self.stop_event.is_set)
                with self.lock:
                    self.select_library(entry['id'],_from_import=True)
                    self.running=False
            except InterruptedError:
                with self.lock:self.error=None;self.progress['stage']='interrompu';self.running=False
            except Exception as error:
                with self.lock:
                    self.error=str(error);self.progress['stage']='erreur';self.running=False
        threading.Thread(target=worker,daemon=True).start()
        return self.state()

    def project_for(self, config):
        signature={'dataset':self.dataset['fingerprint'],'config':asdict(config)}
        if self.library['mode']=='gallery':signature.update(engine=job_analysis.VERSION,step=self.acquisition_step)
        else:signature['engine']=ENGINE_VERSION
        digest=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()[:16]
        return self.root/'web_runs'/('essai_'+digest)

    def make_config(self, data):
        base=self.library['config']
        threshold=float(data.get('threshold',base.get('min_change_gray',12)))
        tile=int(data.get('tile',base.get('tile_px',32)))
        region=data.get('region','parts' if self.library['mode']=='gallery' and self.library.get('default_roi') else 'full')
        phase=data.get('analysis_phase','both')
        if not np.isfinite(threshold) or not 6 <= threshold <= 40 or tile not in {16,32,64} or region not in {'full','parts'} or phase not in {'both','etalement','fusion'}:
            raise ValueError('Settings are outside the supported limits.')
        config=Config(**base)
        config.min_change_gray=threshold
        config.min_texture_change=threshold*(2/3)
        config.tile_px=tile
        config.roi_by_camera=self.library.get('default_roi',{}) if region=='parts' else {}
        config.analysis_phases=['etalement','fusion'] if phase=='both' else [phase]
        return config.validate()

    def make_step(self,data):
        step=data.get('acquisition_step',1)
        if isinstance(step,bool) or step not in (1,2):raise ValueError('Choose an interval of 1 or 2 acquisitions.')
        return int(step)

    def job_folder(self):
        # Un répertoire distinct par fabrication, sans accès aux anciens profils croisés.
        return self.root/'job_runs'/self.library['id']

    def load_job_results(self):
        self.gray_calibration=None;self.aalto_result=None
        if self.library['mode']!='gallery':return
        fingerprint=self.dataset['fingerprint'];step=self.acquisition_step
        cal_sig=job_analysis.calibration_signature(fingerprint,self.config,step)
        run_sig=job_analysis.analysis_signature(fingerprint,self.config,step)
        for name,expected,attribute in [('gray_'+cal_sig,cal_sig,'gray_calibration'),('analysis_'+run_sig,run_sig,'aalto_result')]:
            path=self.job_folder()/(name+'.json')
            if path.is_file():
                value=json.loads(path.read_text(encoding='utf-8'))
                if value.get('signature',value.get('report',{}).get('signature'))==expected:setattr(self,attribute,value)

    @property
    def key(self):
        return self.project.name

    def database(self):
        if self.library['mode']=='gallery':return None
        if not (self.project/'project.sqlite').is_file():
            return None
        db = sqlite3.connect(self.project/'project.sqlite', timeout=20)
        db.row_factory = sqlite3.Row
        return db

    def state(self):
        with self.lock:
            db = self.database()
            try:
                report = summary(db) if db else None
                return {'running': self.running, 'progress': dict(self.progress), 'error': self.error,
                        'run': self.key, 'summary': report, 'config': asdict(self.config),
                        'dataset':dict(self.dataset),'libraries':self.catalog.list(),
                        'revision':self.revision,'operation':self.operation,
                        'review_settings':{'min_consecutive':self.min_consecutive},
                        'acquisition_step':self.acquisition_step,'calibration':metadata(db,'gray_calibration') if db else self.gray_calibration,
                        'display_phases':self.acquisition_phases() if self.library['mode']=='gallery' else self.config.analysis_phases,
                        'analysis':self.aalto_result['report']['jobs'].get(self.library.get('job')) if self.aalto_result else metadata(db,'analysis_report') if db else None}
            finally:
                if db:
                    db.close()

    def start(self, data):
        with self.lock:
            if self.running:
                raise ValueError('An analysis is already running.')
            if self.library['mode']!='temporal':
                return self.start_aalto(data)
            config = self.make_config(data)
            self.running, self.error = True, None
            self.operation='analysis'
            self.progress = {'stage': 'inventaire', 'done': 0, 'total': None}
            self.stop_event.clear()
            threading.Thread(target=self._prepare_work, args=(config,), daemon=True).start()
            return self.state()

    def calibrate_job(self,data):
        with self.lock:
            if self.running:raise ValueError('Processing is already running.')
            if self.library['mode']!='gallery':
                config=self.make_config(data)
                self.running=True;self.error=None;self.operation='calibration';self.stop_event.clear()
                self.progress={'stage':'inventaire','done':0,'total':None}
                threading.Thread(target=self._prepare_work,args=(config,True),daemon=True).start()
                return self.state()
            return self.start_aalto(data,calibration_only=True)

    def start_aalto(self,data,calibration_only=False):
        config=self.make_config(data);step=self.make_step(data)
        self.dataset=self.inventory()
        self.config=config;self.acquisition_step=step;self.project=self.project_for(config)
        self.load_job_results();self.save_preferences()
        self.running=True;self.error=None;self.operation='calibration' if calibration_only else 'analysis';self.stop_event.clear()
        self.progress={'stage':'gris' if calibration_only or not self.gray_calibration else 'analyse_job','done':0,'total':len(self.gallery)}
        source=self.source;records=list(self.gallery);fingerprint=self.dataset['fingerprint'];folder=self.job_folder()
        def worker():
            try:
                def progress(**values):
                    with self.lock:self.progress=values
                calibration=self.gray_calibration
                if calibration_only or calibration is None:
                    calibration=job_analysis.calibrate(source,records,config,step,fingerprint,progress,self.stop_event.is_set)
                    job_analysis.write_json(folder/('gray_'+calibration['signature']+'.json'),calibration)
                    with self.lock:self.gray_calibration=calibration;self.revision+=1
                if not calibration_only:
                    result=job_analysis.analyze_job(source,records,config,step,fingerprint,calibration,folder,progress,self.stop_event.is_set)
                    with self.lock:self.aalto_result=result;self.revision+=1
                with self.lock:self.progress['stage']='termine'
            except InterruptedError:
                with self.lock:self.progress['stage']='interrompu'
            except Exception as error:
                with self.lock:self.error=str(error);self.progress['stage']='erreur'
            finally:
                with self.lock:self.running=False
        threading.Thread(target=worker,daemon=True).start()
        return self.state()

    def _prepare_work(self,config,calibration_only=False):
        try:
            def progress(**values):
                with self.lock:self.progress=values
            info=scan_inventory(self.source,config,progress,self.stop_event.is_set)
            with self.lock:
                self.dataset=self.describe_inventory(info)
                project=self.project_for(config)
                prepared=connect(project);prepared.close()
                self.project=project;self.config=config;self.save_preferences()
            self._work(project,config,calibration_only)
        except InterruptedError:
            with self.lock:self.error=None;self.progress['stage']='interrompu';self.running=False
        except Exception as error:
            with self.lock:
                self.error=str(error);self.progress['stage']='erreur';self.running=False

    def _work(self, project, config, calibration_only=False):
        def progress(**values):
            with self.lock:
                self.progress = values
        try:
            result = analyze(self.source, project, config, progress=progress, stop=self.stop_event.is_set, calibration_only=calibration_only)
            with self.lock:
                self.progress['stage'] = 'termine' if result['parcours_termine'] or (calibration_only and not self.stop_event.is_set()) else 'interrompu'
                self.revision+=1
        except Exception as error:
            with self.lock:
                self.error = str(error)
                self.progress['stage'] = 'erreur'
        finally:
            with self.lock:
                self.running = False

    def require_run(self, key, writable=False):
        if key != self.key:
            raise ValueError('Results have changed. Refresh the page.')
        if writable and self.running:
            raise ValueError('Wait for analysis to finish before saving a decision.')

    def events(self, query):
        with self.lock:
            self.require_run(query.get('run', [''])[0])
            if self.library['mode']=='gallery':return self.acquisition_listing(query)
            order = review_sort(query.get('sort', ['layer'])[0])
            offset = max(0, int(query.get('offset', ['0'])[0]))
            clauses, parameters = [], []
            for field, allowed in [('phase', {'etalement','fusion'}), ('status', {'a_examiner','retenue','ecartee'})]:
                value = query.get(field, [''])[0]
                if value:
                    if value not in allowed:
                        raise ValueError('Unknown filter.')
                    clauses.append(field+'=?')
                    parameters.append(value)
            where = ' WHERE '+' AND '.join(clauses) if clauses else ''
            db = self.database()
            if not db:
                return {'items': [], 'total': 0}
            try:
                db.create_function('priority_value',2,priority_value,deterministic=True)
                columns = '-priority_value(score,end_layer-start_layer+1),start_layer,id' if order=='priority' else 'start_layer,id'
                before = db.execute('SELECT COUNT(*) FROM events'+where, parameters).fetchone()[0]
                where += (' AND ' if where else ' WHERE ')+'end_layer-start_layer+1>=?'
                parameters.append(self.min_consecutive)
                total = db.execute('SELECT COUNT(*) FROM events'+where, parameters).fetchone()[0]
                after=query.get('after',[None])[0];next_id=None
                if after is not None:
                    anchor=db.execute('SELECT * FROM events WHERE id=?',(after,)).fetchone()
                    if anchor is None:raise ValueError('Starting indication not found.')
                    values=[anchor['start_layer'],anchor['id']]
                    if order=='priority':values.insert(0,-priority_value(anchor['score'],anchor['end_layer']-anchor['start_layer']+1))
                    placeholders=','.join('?' for _ in values)
                    successor=db.execute('SELECT id FROM events'+where+f' AND ({columns})>({placeholders}) ORDER BY {columns} LIMIT 1',[*parameters,*values]).fetchone()
                    next_id=successor['id'] if successor else None
                    index=db.execute('SELECT COUNT(*) FROM events'+where+f' AND ({columns})<=({placeholders})',[*parameters,*values]).fetchone()[0]
                    offset=(index//25)*25
                offset=min(offset,((total-1)//25)*25 if total else 0)
                rows = db.execute('SELECT * FROM events'+where+f' ORDER BY {columns} LIMIT 25 OFFSET ?', [*parameters,offset])
                items = [with_priority(row) for row in rows]
                result={'items':items, 'total':total, 'offset':offset,'sort':order,'before_persistence':before,'min_consecutive':self.min_consecutive}
                if after is not None:result['next_id']=next_id
                return result
            finally:
                db.close()

    def detail(self, key, event_id, context='standard'):
        with self.lock:
            self.require_run(key)
            if self.library['mode']=='gallery':return self.acquisition_detail(event_id,context)
            db = self.database()
            if not db:
                raise ValueError('No analysis available.')
            try:
                row = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
                if not row:
                    raise ValueError('Indication not found.')
                event = with_priority(row)
                event.update(consecutive_count=row['end_layer']-row['start_layer']+1,persistence_start=row['start_layer'],persistence_end=row['end_layer'])
                event['snapshot'] = event_fingerprint(row)
                peak = db.execute('SELECT * FROM frames WHERE id=?', (row['peak_frame'],)).fetchone()
                geometry=json.loads(peak['geometry'])
                crop=context_box(json.loads(event['box']),geometry['width'],geometry['height'],context)
                frames = []
                for step in [-1,0,1]:
                    frame = db.execute('SELECT id,layer,phase,geometry,path FROM frames WHERE camera=? AND phase=? AND layer=?',
                                       (peak['camera'],peak['phase'],peak['layer']+step)).fetchone()
                    if frame:
                        frame_geometry=json.loads(frame['geometry']) if frame['geometry'] else None
                        comparable=frame_geometry is not None and all(frame_geometry[k]==geometry[k] for k in ('width','height'))
                        frames.append({'id':frame['id'],'layer':frame['layer'],'phase':frame['phase'],
                                       'geometry':frame_geometry,'comparable':comparable,
                                       'name':Path(frame['path']).name})
                    else:
                        frames.append(None)
                other = 'fusion' if peak['phase']=='etalement' else 'etalement'
                pair = db.execute('SELECT id,geometry FROM frames WHERE camera=? AND phase=? AND layer=?',
                                  (peak['camera'],other,peak['layer'])).fetchone()
                pair_geometry=json.loads(pair['geometry']) if pair and pair['geometry'] else None
                pair_comparable=pair_geometry and all(pair_geometry[k]==geometry[k] for k in ('width','height'))
                return {'event':event, 'frames':frames, 'peak_layer':peak['layer'],
                        'z_mm':self.config.z(peak['layer']), 'pair':pair['id'] if pair_comparable else None,
                        'crop':crop,'context':context,'geometry':geometry}
            finally:
                db.close()

    def decide(self, data):
        with self.lock:
            self.require_run(data.get('run'), writable=True)
            if self.library['mode']=='gallery':return self.acquisition_decision(data)
            status, comment = data.get('status'), data.get('comment','')
            if status not in {'retenue','ecartee','a_examiner'} or not isinstance(comment,str) or len(comment)>10000:
                raise ValueError('Invalid decision or comment.')
            db = self.database()
            if not db:
                raise ValueError('No analysis available.')
            try:
                with db:
                    row = db.execute('SELECT * FROM events WHERE id=?', (int(data['id']),)).fetchone()
                    if not row or data.get('snapshot') != event_fingerprint(row):
                        raise ValueError('This indication has changed. Reload it before saving a decision.')
                    db.execute('UPDATE events SET status=?,comment=? WHERE id=?',(status,comment,row['id']))
                    db.execute('INSERT INTO decisions(event_id,status,comment) VALUES(?,?,?)',(row['id'],status,comment))
                    self.revision+=1
            finally:
                db.close()
            return {'saved':True}

    def set_review_settings(self,data):
        with self.lock:
            self.require_run(data.get('run'),writable=True)
            self.min_consecutive=minimum_count(data.get('min_consecutive'))
            self.revision+=1;self.save_preferences()
            return self.state()

    def image(self, key, frame_id, event_id=None, context='standard'):
        with self.lock:
            self.require_run(key)
            if self.library['mode']=='gallery':return self.acquisition_image(frame_id,event_id,context)
            db = self.database()
            if not db:
                raise ValueError('No image available.')
            try:
                row = db.execute('SELECT path,size,mtime FROM frames WHERE id=?', (frame_id,)).fetchone()
                if not row:
                    raise ValueError('Image not found.')
                path = Path(row['path']).resolve()
                if self.source not in path.parents:
                    raise ValueError('Image outside the selected dataset.')
                verify_source(path,(row['size'],row['mtime']))
                white = self.config.intensity_white_level
                crop=None
                if event_id is not None:
                    detail=self.detail(key,event_id,context)
                    allowed={frame['id'] for frame in detail['frames'] if frame and frame['comparable']}
                    if detail['pair']:
                        allowed.add(detail['pair'])
                    if frame_id not in allowed:
                        raise ValueError('This image does not match the compared layers.')
                    crop=tuple(detail['crop'])
            finally:
                db.close()
        return preview(str(path), white, crop)

    def stack(self,key,phase,region='full',camera=None):
        """Plans photographiques d'une seule caméra et d'une seule étape."""
        with self.lock:
            self.require_run(key)
            if self.library['mode']=='gallery':return self.acquisition_stack(phase,region,camera)
            if phase not in {'etalement','fusion'}:
                raise ValueError('Unknown 3D stage.')
            db=self.database()
            if not db:
                raise ValueError('Run an analysis to prepare the stack.')
            try:
                phases=[r[0] for r in db.execute('SELECT DISTINCT phase FROM frames ORDER BY phase')]
                if phase not in phases:
                    raise ValueError('This stage is not included in the analysis.')
                channels=[r[0] for r in db.execute('SELECT DISTINCT camera FROM frames WHERE phase=?',(phase,))]
                camera=camera or channels[0]
                if camera not in channels:raise ValueError('Unknown camera.')
                rows=db.execute('SELECT id,layer,geometry FROM frames WHERE phase=? AND camera=? AND features IS NOT NULL AND error IS NULL ORDER BY layer',(phase,camera)).fetchall()
                if not rows:
                    raise ValueError('No measured layers for this stage.')
                geometry=json.loads(rows[0]['geometry'])
                crop=self.stack_crop(geometry,region,camera)
                frames=[]
                for row in rows:
                    dimensions=json.loads(row['geometry'])
                    if any(dimensions[k]!=geometry[k] for k in ('width','height')):
                        continue
                    frames.append({'id':row['id'],'layer':row['layer'],'z_mm':self.config.z(row['layer'])})
                events=[]
                frame_layers={f['layer'] for f in frames}
                for event in db.execute('SELECT events.*,frames.layer peak_layer FROM events JOIN frames ON frames.id=events.peak_frame WHERE events.phase=? AND events.camera=? ORDER BY events.id',(phase,camera)):
                    if event['end_layer']-event['start_layer']+1<self.min_consecutive:continue
                    box=json.loads(event['box'])
                    clipped=[max(crop[0],box[0]),max(crop[1],box[1]),min(crop[2],box[2]),min(crop[3],box[3])]
                    if clipped[0]>=clipped[2] or clipped[1]>=clipped[3] or event['peak_layer'] not in frame_layers:continue
                    events.append(with_priority({'id':event['id'],'box':clipped,'layer':event['peak_layer'],'z_mm':self.config.z(event['peak_layer']),
                                   'start_layer':event['start_layer'],'end_layer':event['end_layer'],'status':event['status'],'kind':event['kind'],'score':event['score'],
                                   'consecutive_count':event['end_layer']-event['start_layer']+1}))
                return {'phase':phase,'phases':phases,'camera':camera,'cameras':channels,'frames':frames,'events':events,
                        'shape_available':phase=='fusion','shape_texture_max_px':SHAPE_EDGE,
                        'crop':crop,'width':crop[2]-crop[0],'height':crop[3]-crop[1],
                        'excluded_dimensions':len(rows)-len(frames),'layer_um':self.config.layer_thickness_um,
                        'texture_max_px':384,'min_consecutive':self.min_consecutive}
            finally:
                db.close()

    def stack_crop(self,geometry,region,camera):
        if region not in {'full','parts'}:raise ValueError('Unknown 3D region.')
        full=[0,0,geometry['width'],geometry['height']]
        crop=self.library.get('default_roi',{}).get(camera,full) if region=='parts' else full
        if not 0<=crop[0]<crop[2]<=geometry['width'] or not 0<=crop[1]<crop[3]<=geometry['height']:
            raise ValueError('The preset region is outside this image.')
        return crop

    def stack_image(self,key,frame_id,region='full'):
        with self.lock:
            self.require_run(key)
            if self.library['mode']=='gallery':return self.acquisition_image(frame_id,stack_region=region)
            db=self.database()
            if not db:
                raise ValueError('No analysis available.')
            try:
                row=db.execute('SELECT path,size,mtime,geometry,camera FROM frames WHERE id=? AND features IS NOT NULL AND error IS NULL',(frame_id,)).fetchone()
                if not row:
                    raise ValueError('Layer unavailable.')
                path=Path(row['path']).resolve()
                if self.source not in path.parents:
                    raise ValueError('Image outside the selected dataset.')
                verify_source(path,(row['size'],row['mtime']))
                crop=tuple(self.stack_crop(json.loads(row['geometry']),region,row['camera']))
                white=self.config.intensity_white_level
            finally:
                db.close()
        return preview(str(path),white,crop,384)

    def shape_image(self,key,frame_id,region='full',contrast=3):
        with self.lock:
            self.require_run(key)
            if self.library['mode']=='gallery':
                raise ValueError('Part reconstruction requires identified post-melting photographs. The stage of these acquisitions is unknown.')
            db=self.database()
            if not db:raise ValueError('Run an analysis to prepare the reconstruction.')
            try:
                row=db.execute('SELECT path,size,mtime,geometry,camera,phase FROM frames WHERE id=? AND features IS NOT NULL AND error IS NULL',(frame_id,)).fetchone()
                if not row or row['phase']!='fusion':raise ValueError('Select a measured post-melting layer.')
                path=Path(row['path']).resolve()
                if self.source.resolve() not in path.parents:raise ValueError('Image outside the library.')
                verify_source(path,(row['size'],row['mtime']))
                crop=tuple(self.stack_crop(json.loads(row['geometry']),region,row['camera']))
                white=self.config.intensity_white_level
            finally:db.close()
        return shape_preview(path,white,crop,contrast)

    def report(self, key, options=None):
        return create_report(collect_report(self,key,options))

    def gallery_predictions(self, image_id):
        if not self.aalto_result:return []
        row=self.aalto_result['images'].get(str(image_id),{})
        if row.get('job')!=self.library.get('job'):return []
        return row.get('predictions',[])

    def gallery_reviews(self):
        folder=self.root/'aalto_runs';folder.mkdir(exist_ok=True)
        db=sqlite3.connect(folder/'review.sqlite',timeout=20)
        db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS decisions(signature TEXT,job TEXT,image INTEGER,prediction TEXT,status TEXT,comment TEXT,PRIMARY KEY(signature,job,image,prediction))')
        db.commit()
        return db

    def gallery_items(self,key,offset=0,job='',detected=False):
        with self.lock:
            self.require_run(key)
            if self.library['mode']!='gallery':raise ValueError('This library is a time series.')
            if job and job!=self.library['job']:raise ValueError('This job belongs to another library.')
            rows=[r for r in self.gallery if not detected or self.gallery_predictions(r['id'])]
            return {'total':len(rows),'offset':max(0,offset),'job':self.library['job'],
                    'items':[{'id':r['id'],'counter':r['counter'],'job':r['job'],'name':r['name'],
                              'detections':len(self.gallery_predictions(r['id']))} for r in rows[max(0,offset):max(0,offset)+25]]}

    def gallery_detail(self,key,image_id):
        with self.lock:
            self.require_run(key)
            source_record=next((r for r in self.gallery if r['id']==image_id),None)
            if self.library['mode']!='gallery' or source_record is None:raise ValueError('Photograph not found in this job.')
            # Liste blanche : aucun rectangle, label ou compteur d'annotation n'est envoyé au navigateur.
            record={k:source_record[k] for k in ('id','name','job','counter','timestamp','width','height')}
            record['predictions']=[dict(p) for p in self.gallery_predictions(image_id)]
            record['ready']=self.aalto_result is not None
            measurement=self.aalto_result['images'].get(str(image_id),{}) if self.aalto_result else {}
            for field in ('analyzed','mean_gray','calibration_gray','error'):record[field]=measurement.get(field)
            by_counter={r['counter']:r for r in self.gallery}
            record['neighbors']=[({k:by_counter[counter][k] for k in ('id','counter','width','height')}
                                  if counter in by_counter else None)
                                 for counter in (record['counter']-self.acquisition_step,record['counter']+self.acquisition_step)]
            signature=self.aalto_result['report']['signature'] if self.aalto_result else ''
            db=self.gallery_reviews()
            try:
                for p in record['predictions']:
                    p['key']=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()[:24]
                    saved=db.execute('SELECT status,comment FROM decisions WHERE signature=? AND job=? AND image=? AND prediction=?',
                        (signature,self.library['job'],image_id,p['key'])).fetchone()
                    p['status']=saved['status'] if saved else 'a_examiner'
                    p['comment']=saved['comment'] if saved else ''
            finally:db.close()
            record['contexts']=[context_box(a['box'],record['width'],record['height']) for a in record['predictions']]
            return record

    def gallery_image(self,key,image_id,prediction=None,anchor=None):
        with self.lock:
            record=self.gallery_detail(key,image_id)
            path=(self.source/record['name']).resolve()
            if self.source not in path.parents:raise ValueError('Image outside the library.')
            crop=None
            if prediction is not None:
                reference=self.gallery_detail(key,anchor) if anchor is not None else record
                if anchor is not None and image_id not in [n['id'] for n in reference['neighbors'] if n]+[anchor]:
                    raise ValueError('This photograph is not adjacent to the indication.')
                if (record['width'],record['height'])!=(reference['width'],reference['height']):
                    raise ValueError('Different dimensions: matching crop unavailable.')
                if not 0<=prediction<len(reference['contexts']):raise ValueError('Indication not found.')
                crop=tuple(reference['contexts'][prediction])
        return preview(str(path),255,crop)

    def gallery_decide(self,data):
        with self.lock:
            self.require_run(data.get('run'),writable=True)
            record=self.gallery_detail(self.key,int(data['id']))
            prediction=next((p for p in record['predictions'] if p['key']==data.get('prediction')),None)
            if prediction is None:raise ValueError('Indication changed or missing.')
            status,comment=data.get('status'),data.get('comment','')
            if status not in {'a_examiner','retenue','ecartee'} or not isinstance(comment,str) or len(comment)>10000:
                raise ValueError('Invalid decision or comment.')
            db=self.gallery_reviews()
            try:
                with db:db.execute('INSERT OR REPLACE INTO decisions VALUES(?,?,?,?,?,?)',
                    (self.aalto_result['report']['signature'],self.library['job'],record['id'],prediction['key'],status,comment))
            finally:db.close()
            self.revision+=1
            return {'saved':True}

    def gallery_report(self,key):
        return self.report(key)




def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    app = Application()
    server = ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(app))
    print(f'Powder Ranger : http://127.0.0.1:{server.server_port}/',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        app.stop_event.set()
    finally:
        server.server_close()


if __name__=='__main__':
    main()
