"""Catalogues locaux et inventaire de fichiers sans copier les images de production."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from inspector import Config, jpeg_paths
from storage import atomic_json


def inventory(source,config,progress=lambda **kw:None,stop=lambda:False):
    source=Path(source).resolve()
    if not source.is_dir(): raise ValueError('Source folder not found.')
    expression=re.compile(config.filename_regex,re.I)
    aliases={k.casefold():v for k,v in config.phase_aliases.items()}
    count=0;unmatched=0;examples=[]
    # Le tri se fait sur disque : pas de liste Python proportionnelle à plusieurs To.
    with tempfile.TemporaryDirectory(prefix='lpbf-inventory-') as temporary:
        db=sqlite3.connect(Path(temporary)/'inventory.sqlite')
        try:
            db.execute('PRAGMA temp_store=FILE')
            db.execute('CREATE TABLE files(name TEXT PRIMARY KEY,size INTEGER,mtime INTEGER,camera TEXT,phase TEXT,layer INTEGER)')
            for path in jpeg_paths(source):
                if stop(): raise InterruptedError('Import interrompu.')
                count+=1
                name=path.relative_to(source).as_posix();match=expression.fullmatch(name)
                if match and match['phase'].casefold() in aliases:
                    stat=path.stat()
                    layer=int(match['layer'])
                    if layer<config.first_layer: raise ValueError('Layer precedes the configured origin: '+name)
                    db.execute('INSERT INTO files VALUES(?,?,?,?,?,?)',(name,stat.st_size,stat.st_mtime_ns,match['camera'].casefold(),aliases[match['phase'].casefold()],layer))
                    if len(examples)<5: examples.append({'file':name,'camera':match['camera'],'phase':aliases[match['phase'].casefold()],'layer':layer,'z_mm':config.z(layer)})
                else: unmatched+=1
                if count%250==0:
                    db.commit();progress(stage='inventaire',done=count,total=None)
            db.commit()
            duplicate=db.execute('SELECT camera,phase,layer,COUNT(*) FROM files GROUP BY camera,phase,layer HAVING COUNT(*)>1 LIMIT 1').fetchone()
            if duplicate: raise ValueError(f'Duplicate camera/stage/layer: {duplicate[:3]}. Correct the filename pattern or separate the jobs.')
            n,first,last,layers,total_bytes=db.execute('SELECT COUNT(*),MIN(layer),MAX(layer),COUNT(DISTINCT layer),SUM(size) FROM files').fetchone()
            if not n: raise ValueError('No images recognized. Check the filename pattern and stage aliases.')
            digest=hashlib.sha256()
            digest.update(('['+json.dumps(str(source))+', [').encode())
            for index,row in enumerate(db.execute('SELECT name,size,mtime FROM files ORDER BY name')):
                digest.update(((', ' if index else '')+json.dumps(list(row))).encode())
            digest.update(b']]')
            return {'first':first,'last':last,'images':n,'layers':layers,'layer_um':config.layer_thickness_um,
                    'fingerprint':digest.hexdigest(),'bytes':total_bytes,'unmatched':unmatched,'examples':examples,
                    'cameras':[row[0] for row in db.execute('SELECT DISTINCT camera FROM files ORDER BY camera')],
                    'phases':[row[0] for row in db.execute('SELECT DISTINCT phase FROM files ORDER BY phase')]}
        finally: db.close()


class LibraryCatalog:
    def __init__(self,root,source=None):
        self.root=Path(root);self.path=self.root/'libraries.json';self.entries={}
        config_path=self.root/'config.nist_sample.json'
        base=json.loads(config_path.read_text(encoding='utf-8')) if config_path.is_file() else asdict(Config())
        for key,folder,name in [('nist200','nist_80_179','NIST · 100 layers / 200 photos'),('nist20','nist_sample','NIST · starter sample / 20 photos')]:
            location=self.root/'datasets'/folder
            if location.is_dir() and (location/'provenance.json').is_file():
                self.entries[key]={'id':key,'name':name,'source':str(location.resolve()),'config':base,'mode':'temporal',
                  'source_url':'https://doi.org/10.18434/M32233','license':'NIST','default_roi':{'a':[1000,820,1470,1570]},'note':'One camera, illumination a. Documented layers and stages.'}
        if source is not None:
            self.entries={'custom':{'id':'custom','name':'Local images','source':str(Path(source).resolve()),'config':base,'mode':'temporal','default_roi':{},'note':''}}
        else:
            for key,folder,name,note in [
                ('nist_scan','nist_scan_2_101','NIST · 3D Scan Strategies · 200 photos','Separate build: layers 2–101, 20 µm. Post-spreading and post-melting photographs, original pixels converted losslessly to PNG.'),
                ('ornl_cylinders','ornl_cylinders_70_169','ORNL · 64 cylinders · 200 photos','One build: layers 70–169, 100 µm. Unannotated visible channels, corrected by the producers for illumination and perspective. Public Hugging Face mirror; height relative to index 0.')]:
                location=self.root/'datasets'/folder;marker=location/'provenance.json'
                if not marker.is_file():continue
                provenance=json.loads(marker.read_text(encoding='utf-8'))
                if not provenance.get('complete'):continue
                config={**provenance['config'],'filename_regex':r'(?P<camera>cam[0-9]+)_layer(?P<layer>[0-9]+)_(?P<phase>spread|fused)\.png'}
                self.entries[key]={'id':key,'name':name,'source':str(location.resolve()),'config':config,'mode':'temporal',
                    'source_url':provenance['source_url'],'license':provenance.get('license','NIST'),'default_roi':{},'note':note}
        aalto=self.root/'datasets'/'aalto_pb'
        if source is None and (aalto/'provenance.json').is_file():
            provenance=json.loads((aalto/'provenance.json').read_text(encoding='utf-8'))
            if provenance.get('complete'):
                for job in sorted({r['job'] for r in provenance['records']}):
                    count=sum(r['job']==job for r in provenance['records'])
                    date=next(r['timestamp'][:8] for r in provenance['records'] if r['job']==job)
                    key='aalto_'+job
                    self.entries[key]={'id':key,'name':f'Aalto · {date[:4]}-{date[4:6]}-{date[6:8]} · {count:,} photos',
                        'job':job,'source':str(aalto.resolve()),'mode':'gallery','config':asdict(Config(tile_px=32)),
                        'source_url':provenance['source_url'],'license':provenance['license'],
                        'default_roi':{'aalto':[230,170,1280,895]} if all(r['width']>=1280 and r['height']>=895 for r in provenance['records'] if r['job']==job) else {},
                        'note':'Single-job analysis: initial gray level, changes and drift across acquisitions. Stages and physical heights are not assigned.'}
        if self.path.is_file():
            for item in json.loads(self.path.read_text(encoding='utf-8')):
                if item['id']!='aalto' and item['id'] not in self.entries:self.entries[item['id']]=item
        if not self.entries:
            location=self.root/'empty-library';location.mkdir(parents=True,exist_ok=True)
            self.entries['empty']={'id':'empty','name':'Import your first job','source':str(location.resolve()),
                'config':asdict(Config()),'mode':'temporal','default_roi':{},'empty':True,
                'note':'No image library is installed. Use Import folder to add one build from this computer.'}

    def list(self):
        return [{k:v for k,v in e.items() if k not in {'config','summary','gallery_info'}} for e in list(self.entries.values())]

    def add(self,data,progress,stop):
        source=Path(str(data.get('path','')).strip()).expanduser()
        if not source.is_absolute() or not source.is_dir(): raise ValueError('Enter the absolute path to an existing folder on this computer.')
        name=str(data.get('name','')).strip() or source.name
        if len(name)>120: raise ValueError('Library name is too long.')
        config=Config(**data['config']).validate()
        info=inventory(source,config,progress,stop)
        signature=json.dumps([str(source.resolve()),asdict(config)],sort_keys=True)
        key='local_'+hashlib.sha256(signature.encode()).hexdigest()[:16]
        entry={'id':key,'name':name,'source':str(source.resolve()),'mode':'temporal','config':asdict(config),
               'default_roi':config.roi_by_camera,'note':'Local folder referenced without copying its images.','summary':info}
        updated={**self.entries,key:entry};updated.pop('empty',None)
        atomic_json(self.path,[e for e in updated.values() if e['id'].startswith('local_')])
        self.entries=updated
        return entry
