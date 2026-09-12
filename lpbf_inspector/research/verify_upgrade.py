"""Vérification HTTP isolée des bibliothèques et indications, sans modifier la revue active."""
import io
import json
from pathlib import Path
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from http.client import HTTPConnection

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from local_app import Application,make_handler

app=Application()
app.save_preferences=lambda:None
server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
connection=HTTPConnection('127.0.0.1',server.server_port,timeout=15)
def get(route,**params):
    connection.request('GET',route+('?' + urlencode(params) if params else ''))
    response=connection.getresponse()
    content=response.read()
    assert response.status==200,content
    return content
def post(route,data):
    connection.request('POST',route,body=json.dumps(data),headers={'Content-Type':'application/json'})
    response=connection.getresponse();content=response.read();assert response.status==200,content
    return json.loads(content)
try:
    state=json.loads(get('/api/state'));original=state['run']
    for route in ('/','/stack.js','/gallery.js','/libraries.js','/dark.css'):assert get(route)
    phase=state['config']['analysis_phases'][0]
    stack=json.loads(get('/api/stack',run=original,phase=phase,region='full'))
    assert len(stack['frames'])==100 and stack['events']
    for event in stack['events']:
        detail=json.loads(get('/api/event',run=original,id=event['id']))
        assert detail['event']['phase']==phase and event['layer']==detail['peak_layer']
        assert abs(event['z_mm']-detail['z_mm'])<1e-9
    gallery_state=post('/api/libraries/select',{'id':'aalto'})
    assert gallery_state['dataset']['images']==2638
    key=gallery_state['run'];listing=json.loads(get('/api/gallery',run=key,annotated=1))
    assert listing['total']==1529 and len(listing['jobs'])==3
    checked=[]
    for job in listing['jobs']:
        listing=json.loads(get('/api/gallery',run=key,job=job,annotated=1))
        record=json.loads(get('/api/gallery/detail',run=key,id=listing['items'][0]['id']))
        print('Checking gallery image',record['id'],job,flush=True)
        with Image.open(io.BytesIO(get('/api/gallery/image',run=key,id=record['id']))) as image:assert image.size==(1280,1024)
        crop=record['contexts'][0]
        with Image.open(io.BytesIO(get('/api/gallery/image',run=key,id=record['id'],annotation=0))) as image:assert image.size==(crop[2]-crop[0],crop[3]-crop[1])
        checked.append(record['name'])
    restored=post('/api/libraries/select',{'id':state['dataset']['id']})
    assert restored['run']==original
    result={'run_preserved':original,'3d_markers':len(stack['events']),'3d_phase':phase,'aalto_photos':2638,'aalto_with_usable_boxes':1529,'jobs_checked':checked}
    Path(__file__).with_name('verification_upgrade.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
finally:
    connection.close()
    server.shutdown();server.server_close()
