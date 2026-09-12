"""Vérifie les routes de revue/3D sur les sept bibliothèques sans changer le navigateur."""
import http.client
import io
import json
from pathlib import Path
import sys
import threading
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from local_app import Application,make_handler,ThreadingHTTPServer
from PIL import Image

app=Application(ROOT);app.save_preferences=lambda:None
server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
threading.Thread(target=server.serve_forever,daemon=True).start()
checks={}
def get(route,**params):
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
    try:
        connection.request('GET',route+'?'+urlencode(params))
        response=connection.getresponse();content=response.read()
        if response.status!=200:raise ValueError(str(response.status)+' '+content.decode())
        if response.getheader('Content-Type','').startswith('image'):
            with Image.open(io.BytesIO(content)) as photo:photo.load();return photo.size
        return json.loads(content)
    finally:connection.close()
try:
    for library in app.catalog.entries:
        app.select_library(library);state=get('/api/state');run=state['run']
        assert state['analysis'] and not state['error'],library
        events=get('/api/events',run=run)
        detail=None
        if events['items']:
            event=events['items'][0];detail=get('/api/event',run=run,id=event['id'],context='standard')
            for frame in detail['frames']:
                if frame and frame['comparable']:get('/api/image',run=run,id=frame['id'],event=event['id'],context='standard')
        phases={}
        for phase in state['display_phases']:
            stack=get('/api/stack',run=run,phase=phase,region='full')
            assert stack['frames'] and all('box' in e for e in stack['events'])
            for frame in (stack['frames'][0],stack['frames'][-1]):assert max(get('/api/stack-image',run=run,id=frame['id']))<=384
            phases[phase]={'frames':len(stack['frames']),'indications':len(stack['events']),'axis':stack.get('axis','layer')}
        checks[library]={'analysis':state['analysis'],'calibration':state['calibration'],'review_events':events['total'],'phases':phases,'same_crop_for_neighbors':bool(detail)}
        print(library,'OK',state['analysis']['measured'],'images',phases,flush=True)
    (ROOT/'research/unified_jobs_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
finally:server.shutdown();server.server_close()
