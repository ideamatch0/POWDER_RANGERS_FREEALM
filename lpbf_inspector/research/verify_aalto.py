"""Vérification HTTP des trois jobs réels, sans modifier les préférences utilisateur."""
import http.client
import io
import json
from pathlib import Path
import sys
import threading
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app import Application,make_handler
from aalto_detector import detect_image

app=Application(ROOT)
app.save_preferences=lambda:None
assert app.aalto_result is not None,'Attendre la calibration complète.'
server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
threading.Thread(target=server.serve_forever,daemon=True).start()
connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15)


def request(path,body=None):
    connection.request('POST' if body is not None else 'GET',path,
                       None if body is None else json.dumps(body),
                       {} if body is None else {'Content-Type':'application/json'})
    response=connection.getresponse();data=response.read()
    assert response.status==200,(response.status,data[:300])
    return json.loads(data) if response.getheader('Content-Type').startswith('application/json') else data


try:
    checks=[];seen=set();runs=set()
    libraries=[item for item in app.catalog.list() if item['id'].startswith('aalto_')]
    assert len(libraries)==3
    for library in libraries:
        state=request('/api/libraries/select',{'id':library['id']});run=state['run'];runs.add(run)
        assert state['calibration'] is not None
        ids=[]
        for offset in range(0,state['dataset']['images'],25):
            page=request('/api/gallery?'+urlencode({'run':run,'offset':offset}))
            assert page['job']==library['job']
            assert all(item['job']==library['job'] and 'annotations' not in item for item in page['items'])
            ids.extend(item['id'] for item in page['items'])
        assert len(ids)==state['dataset']['images']
        assert not seen.intersection(ids);seen.update(ids)
        page=request('/api/gallery?'+urlencode({'run':run,'detected':'1'}))
        item=page['items'][0]
        detail=request('/api/gallery/detail?'+urlencode({'run':run,'id':item['id']}))
        assert 'annotations' not in json.dumps(detail)
        assert detail['predictions']
        raw=request('/api/gallery/image?'+urlencode({'run':run,'id':item['id']}))
        crop=request('/api/gallery/image?'+urlencode({'run':run,'id':item['id'],'prediction':0}))
        with Image.open(io.BytesIO(raw)) as image:assert image.size==(1280,1024)
        with Image.open(io.BytesIO(crop)) as image:
            box=detail['contexts'][0];assert image.size==(box[2]-box[0],box[3]-box[1])
        profile=json.loads((ROOT/'aalto_runs'/f"profile_{library['job']}.json").read_text(encoding='utf-8'))
        predicted=detect_image(ROOT/'datasets'/'aalto_pb'/detail['name'],profile)
        displayed=[{k:p[k] for k in ('box','score','kind')} for p in detail['predictions']]
        assert predicted==displayed,'Les prédictions affichées doivent provenir de la seule image.'
        evaluation=request('/api/gallery/evaluation?'+urlencode({'run':run}))
        assert evaluation['job']['job']==library['job']
        checks.append({'library':library['name'],'run':run,'images':len(ids),'independent_inference':True,
                       'annotations_hidden':True,'crop_verified':True,'metrics':evaluation['job']})
    assert len(runs)==3 and len(seen)==2638
    result={'verified':True,'images':len(seen),'jobs':checks}
    (ROOT/'research'/'verification_aalto_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'verified':True,'images':len(seen),'libraries':[c['library'] for c in checks]},ensure_ascii=False))
finally:
    connection.close();server.shutdown();server.server_close()
