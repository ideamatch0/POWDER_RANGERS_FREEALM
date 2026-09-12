"""Restore this PC's existing public libraries into the empty desktop profile.

Images stay at their existing paths. Current result snapshots are copied, never
linked or moved. The installed 0.3.1 importer preserves entries prefixed local_.
Run 'prepare' first, then 'install' only while the empty desktop app is closed.
"""
from pathlib import Path
import sys,os,json,shutil,sqlite3
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from libraries import LibraryCatalog
from local_app import Application
from storage import atomic_json

WORK=ROOT/'research/desktop_library_restore_2026-09-10'
STAGE=WORK/'staging'
TARGET=Path(os.environ['LOCALAPPDATA'])/'PowderRanger'

def backup_database(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    a=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);b=sqlite3.connect(destination)
    try:a.backup(b)
    finally:b.close();a.close()

def prepare():
    assert not STAGE.exists(),'A prepared restoration already exists; inspect it instead of overwriting'
    STAGE.mkdir(parents=True)
    original=LibraryCatalog(ROOT);saved=json.loads((ROOT/'web_settings.json').read_text())
    mapping={key:'local_'+key for key in original.entries}
    entries=[{**e,'id':mapping[e['id']]} for e in original.entries.values()]
    atomic_json(STAGE/'libraries.json',entries)
    prefs={mapping[k]:v for k,v in saved.get('by_library',{}).items() if k in mapping}
    selected=mapping[saved['library']]
    manifest=[]
    for old,new in mapping.items():
        atomic_json(STAGE/'web_settings.json',{'library':new,'by_library':prefs})
        app=Application(STAGE)
        assert app.library['id']==new and app.dataset['images']>0
        if app.library['mode']=='gallery':
            original_folder=ROOT/'job_runs'/old
            if original_folder.is_dir():
                for source in original_folder.glob('*.json'):
                    destination=STAGE/'job_runs'/new/source.name;destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,destination)
        else:
            source=ROOT/'web_runs'/app.key/'project.sqlite'
            if source.is_file():backup_database(source,STAGE/'web_runs'/app.key/'project.sqlite')
        # Reload with the restored snapshots and the original per-job settings.
        restored=Application(STAGE);state=restored.state()
        manifest.append({'id':new,'original_id':old,'name':restored.library['name'],'images':restored.dataset['images'],
                         'run':restored.key,'analysis_loaded':bool(state['analysis']),
                         'indications':state['summary']['indications'] if state['summary'] else None})
    source=ROOT/'aalto_runs/review.sqlite'
    if source.is_file():backup_database(source,STAGE/'aalto_runs/review.sqlite')
    atomic_json(STAGE/'web_settings.json',{'library':selected,'by_library':prefs})
    final=Application(STAGE);state=final.state()
    result={'libraries':manifest,'selected':selected,'run':final.key,'selected_indications':state['summary']['indications'],
            'images_copied':0,'prepared_bytes':sum(p.stat().st_size for p in STAGE.rglob('*') if p.is_file())}
    atomic_json(WORK/'prepared.json',result);print(json.dumps(result,indent=2,ensure_ascii=False))

def install():
    expected=json.loads((WORK/'prepared.json').read_text(encoding='utf-8'))
    assert TARGET.resolve()==(Path(os.environ['LOCALAPPDATA'])/'PowderRanger').resolve()
    # Do not overwrite user work that might have been created since diagnosis.
    allowed={'empty-library','instance.json','instance.lock','launcher.log'}
    unexpected=[p.name for p in TARGET.iterdir() if p.name not in allowed]
    assert not unexpected,'Desktop profile now contains data; merge must be reviewed: '+str(unexpected)
    archive=WORK/'original-empty-profile';archive.mkdir(exist_ok=False)
    for p in TARGET.iterdir():
        if p.is_file():shutil.copy2(p,archive/p.name)
    for name in ('job_runs','web_runs','aalto_runs'):
        source=STAGE/name
        if source.exists():shutil.copytree(source,TARGET/name)
    # Publish the catalogue/settings only after all prepared result copies exist.
    for name in ('libraries.json','web_settings.json'):
        atomic_json(TARGET/name,json.loads((STAGE/name).read_text(encoding='utf-8')))
    actual=Application(TARGET);state=actual.state()
    assert len(actual.catalog.entries)==len(expected['libraries'])
    assert state['summary']['indications']==expected['selected_indications']
    assert actual.key==expected['run']
    result={'profile':str(TARGET),'library_count':len(actual.catalog.entries),'selected':actual.library['name'],
            'images':actual.dataset['images'],'run':actual.key,'indications':state['summary']['indications'],'images_copied':0}
    atomic_json(WORK/'installed.json',result);print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':
    {'prepare':prepare,'install':install}[sys.argv[1]]()
