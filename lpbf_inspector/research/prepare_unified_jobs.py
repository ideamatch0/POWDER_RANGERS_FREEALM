"""Recalcule les bibliothèques installées, sans changer la sélection du navigateur."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from local_app import Application
from inspector import analyze
import job_analysis

app=Application(ROOT)
app.save_preferences=lambda:None
report_path=ROOT/'research/unified_jobs_verification.json'
summary=json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
keys=sys.argv[1:] or list(app.catalog.entries)
for key in keys:
    app.select_library(key)
    print('Analyse',key,app.dataset['images'],'photos',flush=True)
    last=[-1]
    def progress(**p):
        bucket=p.get('done',0)//100
        if bucket!=last[0]:print(key,p['stage'],p.get('done'), '/',p.get('total'),flush=True);last[0]=bucket
    if app.library['mode']=='gallery':
        cal=app.gray_calibration or job_analysis.calibrate(app.source,app.gallery,app.config,app.acquisition_step,app.dataset['fingerprint'])
        job_analysis.write_json(app.job_folder()/('gray_'+cal['signature']+'.json'),cal)
        value=job_analysis.analyze_job(app.source,app.gallery,app.config,app.acquisition_step,app.dataset['fingerprint'],cal,app.job_folder(),progress)
        summary[key]=value['report']['jobs'][app.library['job']]
    else:
        summary[key]=analyze(app.source,app.project,app.config,progress)
    print('Terminé',key,flush=True)
report_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
