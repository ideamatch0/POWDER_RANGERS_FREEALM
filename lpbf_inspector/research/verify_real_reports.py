"""Read existing review decisions without changing the user's job or settings."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from unittest.mock import patch
from local_app import Application
from reporting import collect_report,create_report,TEMPLATES
from report_volume import render_volume

root=Path(__file__).resolve().parents[1];out=root/'research/report-validation';out.mkdir(exist_ok=True)
app=Application();snapshot=collect_report(app,app.key,{'job_name':'NIST · 3D Scan Strategies','planes':64})
volumes=[]
for i,scene in enumerate(snapshot['scenes']):
    volume=render_volume(scene,app.config.intensity_white_level,planes=64)
    volumes.append(volume)
    (out/f'volume-{i}-oblique.png').write_bytes(volume['oblique'])
    (out/f'volume-{i}-top.png').write_bytes(volume['top'])
for key in TEMPLATES:
    snapshot['options']['template']=key
    with patch('reporting.render_volume',side_effect=volumes):data=create_report(snapshot)
    (out/f'{key}.html').write_bytes(data)
result={'run':app.key,'retained':len(snapshot['details']),'templates':list(TEMPLATES),
        'scenes':[{**{k:s[k] for k in ['label','cyan','axis']},**{k:v[k] for k in ['loaded','sampled','total','markers','warnings']}} for s,v in zip(snapshot['scenes'],volumes)]}
(out/'checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
