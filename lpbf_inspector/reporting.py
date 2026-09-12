"""Rapports autonomes : instantané des retenues, modèles et vues 3D intégrées."""
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime
import base64
from collections import Counter
from html import escape
import io
import json
from pathlib import Path
import re
import threading
import time
import unicodedata
import uuid

from inspector import Config
from priority import PRIORITY_HELP, priority_text, review_sort
from review import picture
from report_volume import render_volume, score_color
from shape_reconstruction import contrast_value
from source_integrity import file_stamp,verify_source,verify_report_sources

ROOT=Path(__file__).resolve().parent
TEMPLATES={
    'summary':{'name':'Summary','description':'3D views, key figures, register and comments. For a quick overview.'},
    'detailed':{'name':'Detailed review','description':'Overview and an individual sheet for each indication, with before, peak and after photographs.'},
    'presentation':{'name':'Presentation','description':'Dark theme, large 3D views and visual review sheets. For presenting observations.'},
}
PHASES={'fusion':'After melting','etalement':'After spreading','acquisition':'Unidentified stage',
        'sequence0':'Even sequence · unidentified stage','sequence1':'Odd sequence · unidentified stage'}
KINDS={'changement_local':'Local change','derive_locale':'Local drift','luminosite_globale':'Global brightness',
       'derive_globale':'Global drift','niveau_gris':'Initial gray-level deviation'}


def options_for(data,library_name):
    if data is None:data={}
    if not isinstance(data,dict):raise ValueError('Invalid report options.')
    defaults={'job_name':library_name,'author':'','machine':'','material':'','reference':'',
              'date':date.today().isoformat(),'conclusion':'','template':'detailed','order':'layer',
              'include_3d':True,'region':'full','contrast':3,'planes':64}
    options={k:data.get(k,v) for k,v in defaults.items()}
    for field,limit in [('job_name',160),('author',160),('machine',160),('material',160),('reference',100),('conclusion',5000)]:
        value=options[field]
        if not isinstance(value,str) or len(value)>limit or '\x00' in value:raise ValueError('Invalid report field: '+field)
        options[field]=value.strip()
    if not options['job_name']:raise ValueError('Enter a job name.')
    if options['template'] not in TEMPLATES:raise ValueError('Unknown report template.')
    if not isinstance(options['date'],str):raise ValueError('Invalid report date.')
    try:date.fromisoformat(options['date'])
    except ValueError:raise ValueError('Invalid report date.') from None
    review_sort(options['order'])
    if type(options['include_3d']) is not bool:raise ValueError('Invalid 3D-view option.')
    if options['region'] not in {'full','parts'}:raise ValueError('Unknown report region.')
    options['contrast']=contrast_value(options['contrast'])
    if type(options['planes']) is not int or options['planes'] not in {32,64,128}:raise ValueError('Choose 32, 64 or 128 preview planes.')
    return options


def report_context(app,key):
    with app.lock:
        app.require_run(key,writable=True)
        listing=app.events({'run':[key],'status':['retenue']})
        return {'run':key,'revision':app.revision,'library_id':app.library['id'],'library_name':app.library['name'],
                'retained':listing['total'],'before_persistence':listing.get('before_persistence',listing['total']),
                'min_consecutive':app.min_consecutive,'templates':TEMPLATES,'defaults':options_for(None,app.library['name']),
                'has_roi':bool(app.library.get('default_roi')),'acquisition':app.library['mode']=='gallery'}


def collect_report(app,key,data=None,expected_revision=None):
    """Copie cohérente sous verrou ; le calcul et les photos sont traités ensuite."""
    with app.lock:
        app.require_run(key,writable=True)
        if expected_revision is not None and expected_revision!=app.revision:
            raise ValueError('The review has changed. Reopen report setup to refresh its scope.')
        options=options_for(data,app.library['name'])
        query={'run':[key],'status':['retenue'],'sort':[options['order']]}
        first=app.events(query);count=first['total']
        if not 1<=count<=500:raise ValueError('Keep between 1 and 500 indications meeting the minimum persistence before exporting a report.')
        events=first['items']
        for offset in range(25,count,25):events.extend(app.events(dict(query,offset=[str(offset)]))['items'])
        acquisition=app.library['mode']=='gallery'
        db=None if acquisition else app.database()
        acquisition_paths={r['id']:str((app.source/r['name']).resolve()) for r in app.gallery} if acquisition else {}
        def source_frame(frame):
            if frame is None:return None
            if acquisition:
                path=acquisition_paths[frame['id']];stamp=file_stamp(path)
            else:
                row=db.execute('SELECT path,size,mtime FROM frames WHERE id=?',(frame['id'],)).fetchone()
                if not row:raise ValueError('Report source frame is missing.')
                path=row['path'];stamp=[row['size'],row['mtime']];verify_source(path,stamp)
            if app.source.resolve() not in Path(path).resolve().parents:raise ValueError('Report image outside the selected library.')
            return dict(frame,path=path,source_stamp=stamp)
        details=[];scenes=[];warnings=[]
        try:
            for i,event in enumerate(events):
                detail=app.detail(key,event['id']);detail['event']['report_label']=f'R{i+1:03d}'
                detail['frames']=[source_frame(f) for f in detail['frames']];details.append(detail)
            if options['include_3d']:
                by_group={}
                for detail in details:
                    event=detail['event'];by_group.setdefault((event['camera'],event['phase']),[]).append(detail)
                for (camera,phase),group in by_group.items():
                    try:
                        stack=app.stack(key,phase,options['region'],camera)
                        model=stack;cyan=False;note='Photographic stack; no post-melting shape assigned.'
                        if not acquisition:
                            try:
                                fusion=app.stack(key,'fusion',options['region'],camera)
                                # Un canal seul, même cadrage et dimensions. Pas de fusion multi-caméras.
                                if (fusion['crop'],fusion['width'],fusion['height'])==(stack['crop'],stack['width'],stack['height']):
                                    model=fusion;cyan=True
                                    note='Cyan shape extracted from post-melting photographs.'
                                    if phase!='fusion':note+=' Markers correspond to post-spreading observations at their layer heights.'
                            except ValueError:pass
                        frames=[]
                        for frame in model['frames']:
                            frames.append(dict(source_frame(frame),position=frame.get('position',frame['z_mm'])))
                        markers=[];lookup={e['id']:e for e in stack['events']}
                        for detail in group:
                            event=detail['event'];mark=lookup.get(event['id'])
                            if mark and frames[0]['position']<=mark.get('position',mark['z_mm'])<=frames[-1]['position']:
                                markers.append(dict(mark,report_label=event['report_label'],position=mark.get('position',mark['z_mm'])))
                            else:warnings.append(event['report_label']+' remains in the register and review sheets but cannot be placed in this 3D crop (dimensions, position or height outside the volume).')
                        if markers:
                            scenes.append({'label':PHASES[phase]+' · '+camera,'phase':phase,'camera':camera,'cyan':cyan,
                                           'frames':frames,'events':markers,'crop':model['crop'],'width':model['width'],
                                           'height':model['height'],'axis':model.get('axis','layer'),'note':note})
                    except (ValueError,OSError) as error:warnings.append('3D view '+PHASES[phase]+' · '+camera+' unavailable: '+str(error))
        finally:
            if db:db.close()
        state=app.state()
        return deepcopy({'options':options,'run':key,'revision':app.revision,'library':{k:app.library.get(k) for k in ('id','name','source_url','license')},
                         'min_consecutive':app.min_consecutive,'before_persistence':first.get('before_persistence',count),
                         'config':asdict(app.config),'acquisition':acquisition,'acquisition_step':app.acquisition_step,
                         'analysis':state['analysis'],'calibration':state['calibration'],'details':details,'scenes':scenes,
                         'warnings':warnings,'created_at':datetime.now().astimezone().isoformat(timespec='seconds')})


def embedded(data,mime='image/png'):
    return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')


def create_report(snapshot,progress=lambda text:None):
    verify_report_sources(snapshot)
    options=snapshot['options'];details=snapshot['details'];config=Config(**snapshot['config'])
    volumes=[];warnings=list(snapshot['warnings'])
    for scene in snapshot['scenes']:
        volume=render_volume(scene,config.intensity_white_level,options['contrast'],options['planes'],progress)
        volumes.append((scene,volume));warnings.extend(scene['label']+' : '+w for w in volume['warnings'])
    out=io.StringIO();write=out.write;template=options['template'];title=escape(options['job_name'])
    css=(ROOT/'web/report-document.css').read_text(encoding='utf-8')
    logo=embedded((ROOT/'web/powder-ranger-icon.svg').read_bytes(),'image/svg+xml')
    write('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+' · Powder Ranger</title><style>'+css+'</style></head><body class="template-'+template+'"><main>')
    write('<header class="cover"><div class="brand"><img alt="Powder Ranger" src="'+logo+'"><div><strong>POWDER RANGER</strong><span>Every layer under watch.</span></div><b>'+escape(TEMPLATES[template]['name'])+'</b></div><p class="eyebrow">Build image review report</p><h1>'+title+'</h1>')
    write('<p class="subtitle">Operator-retained indications · single-job analysis</p><dl class="identity">')
    for label,field in [('Date','date'),('Reference','reference'),('Prepared by','author'),('Machine','machine'),('Material','material')]:
        if options[field]:write('<div><dt>'+label+'</dt><dd>'+escape(options[field])+'</dd></div>')
    write('</dl></header>')
    count=len(details);scores=[d['event']['priority_score'] for d in details];positions=[d['peak_layer'] for d in details]
    unit='Acquisitions' if snapshot['acquisition'] else 'Layers'
    write('<section class="metrics"><div><strong>'+str(count)+'</strong><span>retained indication(s)</span></div><div><strong>'+f'{max(scores):.1f}'+'</strong><span>maximum priority / 100</span></div><div><strong>'+str(min(positions))+'–'+str(max(positions))+'</strong><span>'+unit.lower()+' flagged</span></div><div><strong>'+str(snapshot['min_consecutive'])+'</strong><span>minimum persistence</span></div></section>')
    write('<p class="scope">Minimum persistence: '+str(snapshot['min_consecutive'])+' '+('comparable acquisitions' if snapshot['acquisition'] else 'layers')+' consecutive. '+str(snapshot['before_persistence']-count)+' retained hidden by this filter. Pending and dismissed indications are excluded from this report. Snapshot taken on '+escape(snapshot['created_at'])+'.</p>')
    if options['conclusion']:
        write('<section class="conclusion"><p class="eyebrow">Review conclusion</p><p>'+escape(options['conclusion']).replace('\n','<br>')+'</p></section>')
    for i,(scene,volume) in enumerate(volumes):
        write('<section class="volume"><div class="section-title"><span>'+f'{i+1:02d}'+'</span><div><h2>3D view of retained indications</h2><p>'+escape(scene['label'])+'</p></div></div><div class="volume-images"><figure><img alt="Oblique volume view with retained indications" src="'+embedded(volume['oblique'])+'"><figcaption>Oblique view · complete volume</figcaption></figure><figure><img alt="Top view of retained indications" src="'+embedded(volume['top'])+'"><figcaption>Top view · all heights overlaid</figcaption></figure></div>')
        write('<div class="palette"><span>'+('Cyan: photographic shape' if scene['cyan'] else 'Gray: photographs')+'</span><span>Priority / 100</span>')
        for low in (0,20,40,60,80):
            color=score_color(low);write('<i style="--score:rgb('+','.join(map(str,color))+')">'+str(low)+'–'+str(low+20)+'</i>')
        write('</div><p class="volume-note">'+escape(scene['note'])+' '+str(volume['loaded'])+' planes loaded out of '+str(volume['sampled'])+' sampled, from '+str(volume['total'])+' images. '+str(volume['markers'])+' retained marker(s), placed at indication peaks and visible through the sections.</p>')
        write('<p class="fine">'+('Vertical axis: acquisition order; physical height and process stage are not assigned.' if scene['axis']=='acquisition' else 'Z follows layer heights and is exaggerated for clarity. X/Y remain in uncalibrated pixels.')+' Approximate photographic reconstruction: reflections and shadows may distort outlines. Fixed views are embedded in the file for offline use.</p></section>')
    if warnings:write('<section class="warnings"><h2>Exported-view limitations</h2><ul>'+''.join('<li>'+escape(w)+'</li>' for w in warnings)+'</ul></section>')
    write('<section class="register"><h2>Retained-indications register</h2><p class="fine">Order: '+('highest priority first' if options['order']=='priority' else 'chronological')+'. References R001, R002… identify the report review sheets.</p><table><thead><tr><th>Ref. / '+unit[:-1].lower()+'</th><th>Observation</th><th>Priority</th><th>Persistence</th><th>Comment</th></tr></thead><tbody>')
    for detail in details:
        e=detail['event'];color=','.join(map(str,score_color(e['priority_score'])))
        write('<tr><td><a href="#'+e['report_label']+'">'+e['report_label']+'</a><small>'+str(detail['peak_layer'])+'</small></td><td>'+escape(KINDS.get(e['kind'],e['kind']))+'<small>'+escape(PHASES[e['phase']]+' · '+e['camera'])+'</small></td><td class="score" style="--score:rgb('+color+')">'+f"{e['priority_score']:.1f}"+' / 100</td><td>'+str(e['consecutive_count'])+'</td><td class="comment">'+(escape(e['comment']) if e['comment'] else '—')+'</td></tr>')
    write('</tbody></table></section>')
    if template!='summary':
        for i,detail in enumerate(details):
            progress('Review sheet '+str(i+1)+' / '+str(len(details)))
            e=detail['event'];box=json.loads(e['box']);size=(detail['geometry']['width'],detail['geometry']['height']);crop=detail['crop']
            write('<article class="indication" id="'+e['report_label']+'"><div class="section-title"><span>'+e['report_label']+'</span><div><h2>'+escape(KINDS.get(e['kind'],e['kind']))+'</h2><p>'+escape(PHASES[e['phase']]+' · '+e['camera'])+' · '+unit[:-1].lower()+' '+str(detail['peak_layer'])+(' · Z = '+f"{detail['z_mm']:.3f}"+' mm' if detail['z_mm'] is not None else ' · physical height not assigned')+'</p></div></div>')
            write('<p class="priority-line">'+escape(priority_text(e))+'</p><div class="overview"><figure>'+picture(detail['frames'][1],config,box=box)+'</figure><div><h3>Overview</h3><p>The red box locates the flagged area.</p><p>Peak region: '+escape(str(box))+' pixels.</p></div></div>')
            write('<p class="fine">Close-ups: matching crop, same gray-level scale. The blue box marks the same location before and after.</p><div class="images">')
            for j,(frame,label) in enumerate(zip(detail['frames'],('Before','Flagged image','After'))):
                write('<figure'+(' class="current"' if j==1 else '')+'><h3>'+label+'</h3>'+picture(frame if frame and frame['comparable'] else None,config,box,crop,size,reference=j!=1)+'</figure>')
            write('</div><div class="observation"><strong>Retained · comment</strong><p>'+escape(e['comment'] or 'No comment.').replace('\n','<br>')+'</p></div></article>')
    else:
        # Les ancres restent valides dans le modèle sans fiches photographiques.
        write(''.join('<span id="'+d['event']['report_label']+'"></span>' for d in details))
    analysis=snapshot['analysis'] or {};cal=snapshot['calibration'] or {}
    write('<section class="method"><h2>Settings and traceability</h2><dl class="identity">')
    fields=[('Source library',snapshot['library']['name']),('Analysis',snapshot['run']),('Decision revision',snapshot['revision']),
            ('Measured photos',analysis.get('measured','—')),('Evaluated photos',analysis.get('evaluated','—')),
            ('Initial gray level / 255',f"{cal['mean_gray']:.2f}" if cal.get('mean_gray') is not None else 'Unavailable'),
            ('Minimum threshold / 255',config.min_change_gray),('Tile size',str(config.tile_px)+' px'),('3D contrast',options['contrast'])]
    for label,value in fields:write('<div><dt>'+label+'</dt><dd>'+escape(str(value))+'</dd></div>')
    write('</dl><p>'+escape(PRIORITY_HELP)+'</p><p>Researcher annotations are not used for these indications. The report records observations retained by the operator; it does not determine material conformity.</p>')
    source=snapshot['library'].get('source_url');license=snapshot['library'].get('license')
    if source and re.match(r'^https?://',source):write('<p>Images : <a href="'+escape(source,quote=True)+'">library provenance</a>'+(' · '+escape(license) if license else '')+'</p>')
    write('</section><footer>Powder Ranger · Every layer under watch.<span>'+title+' · '+escape(options['date'])+'</span></footer></main></body></html>')
    progress('Report ready')
    verify_report_sources(snapshot)
    return out.getvalue().encode('utf-8')


def report_filename(options,identifier):
    name=unicodedata.normalize('NFKD',options['job_name']).encode('ascii','ignore').decode()
    name=re.sub(r'[^a-zA-Z0-9_-]+','_',name).strip('_')[:60] or 'job'
    return f"Powder_Ranger_{name}_{options['date']}_{options['template']}_{identifier[:8]}.html"


class ReportTasks:
    def report_context(self,key):return report_context(self,key)

    def start_report(self,data):
        with self.lock:
            tasks=getattr(self,'_report_tasks',{})
            if any(t['status']=='running' for t in tasks.values()):raise ValueError('A report is already being generated. Wait for completion or cancel it.')
            snapshot=collect_report(self,data.get('run'),data.get('options'),data.get('revision'))
            identifier=uuid.uuid4().hex
            task={'id':identifier,'status':'running','message':'Preparing views','progress':0,'run':snapshot['run'],
                  'job_name':snapshot['options']['job_name'],'filename':report_filename(snapshot['options'],identifier),'started':time.monotonic(),
                  'cancel':threading.Event(),'error':None,'eta':None}
            tasks[identifier]=task;self._report_tasks=tasks
            # Les fichiers exportés restent disponibles ; seuls les états anciens sont bornés.
            while len(tasks)>20:tasks.pop(next(iter(tasks)))
        def worker():
            count=sum(min(len(s['frames']),snapshot['options']['planes']) for s in snapshot['scenes'])
            count+=0 if snapshot['options']['template']=='summary' else len(snapshot['details'])
            done=0
            def progress(message):
                nonlocal done
                if task['cancel'].is_set():raise InterruptedError('Generation cancelled.')
                done+=1
                with self.lock:
                    task['message']=message;task['progress']=min(99,round(done/max(1,count+1)*100))
                    task['eta']=max(0,round((time.monotonic()-task['started'])/done*(count+1-done)))
            try:
                content=create_report(snapshot,progress)
                if task['cancel'].is_set():raise InterruptedError('Generation cancelled.')
                folder=self.root/'report_exports';folder.mkdir(exist_ok=True)
                path=folder/task['filename'];path.write_bytes(content)
                with self.lock:task.update(status='ready',progress=100,eta=0,message='Report ready',path=path)
            except InterruptedError:
                with self.lock:task.update(status='cancelled',message='Generation cancelled.')
            except Exception as error:
                with self.lock:task.update(status='error',error=str(error),message='Export failed.')
        threading.Thread(target=worker,daemon=True).start()
        return self.report_status(identifier)

    def report_status(self,identifier):
        with self.lock:
            task=getattr(self,'_report_tasks',{}).get(identifier)
            if not task:raise ValueError('Report not found. Generate a new export.')
            return {k:task[k] for k in ('id','status','message','progress','run','job_name','filename','error','eta')}

    def cancel_report(self,identifier):
        with self.lock:
            self.report_status(identifier);task=self._report_tasks[identifier]
            if task['status']=='running':task['cancel'].set()
        return self.report_status(identifier)

    def report_file(self,identifier):
        with self.lock:
            status=self.report_status(identifier)
            if status['status']!='ready':raise ValueError('The report is not ready yet.')
            path=self._report_tasks[identifier]['path']
        return path.read_bytes(),status['filename']
