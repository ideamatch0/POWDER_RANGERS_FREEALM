"""Contrôle HTTP des données réelles, sans changer les réglages ou décisions actifs."""
import http.client
import io
import json
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from local_app import Application,make_handler,ThreadingHTTPServer
from PIL import Image,ImageDraw

app=Application(ROOT);app.save_preferences=lambda:None
settings=(ROOT/'web_settings.json').read_bytes()
server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
threading.Thread(target=server.serve_forever,daemon=True).start()
checks={};overlays=[]

def get(route,expected=200,**params):
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=60)
    try:
        connection.request('GET',route+'?'+urlencode(params))
        response=connection.getresponse();content=response.read()
        assert response.status==expected,(response.status,content[:500])
        if response.getheader('Content-Type','').startswith('image'):
            with Image.open(io.BytesIO(content)) as photo:photo.load();return photo.copy(),dict(response.getheaders())
        return json.loads(content)
    finally:connection.close()

try:
    for library in app.catalog.entries:
        app.select_library(library);state=get('/api/state');run=state['run']
        start=time.perf_counter();listing=get('/api/events',run=run,sort='priority')
        elapsed=time.perf_counter()-start
        scores=[e['priority_score'] for e in listing['items']]
        assert scores==sorted(scores,reverse=True),library
        phase_checks={}
        for phase in state['display_phases']:
            stack=get('/api/stack',run=run,phase=phase)
            if stack['events']:
                mark=stack['events'][0];detail=get('/api/event',run=run,id=mark['id'])
                assert mark['priority_score']==detail['event']['priority_score']
            samples=[]
            if phase=='fusion':
                assert stack['shape_available']
                frames=stack['frames']
                for frame in (frames[0],frames[len(frames)//2],frames[-1]):
                    tick=time.perf_counter()
                    shape,headers=get('/api/shape-image',run=run,id=frame['id'],contrast=3)
                    assert shape.mode=='RGBA' and max(shape.size)<=512
                    coverage=float(headers['X-Shape-Coverage']);assert 0<=coverage<=100
                    samples.append({'layer':frame['layer'],'coverage_percent':coverage,'seconds':round(time.perf_counter()-tick,3)})
                    if frame==frames[len(frames)//2]:
                        photo,_=get('/api/stack-image',run=run,id=frame['id'])
                        photo=photo.convert('RGBA').resize(shape.size)
                        shape.putalpha(shape.getchannel('A').point(lambda x:round(x*.6)))
                        photo.alpha_composite(shape);photo.thumbnail((380,380))
                        overlays.append((library+' / couche '+str(frame['layer']),photo.copy()))
            else:
                assert not stack.get('shape_available',False)
                get('/api/shape-image',expected=400,run=run,id=stack['frames'][0]['id'])
            phase_checks[phase]={'frames':len(stack['frames']),'events':len(stack['events']),'shape_samples':samples}
        after=get('/api/state')
        assert after['run']==run and after['analysis']==state['analysis'] and after['calibration']==state['calibration']
        checks[library]={'events':listing['total'],'top_scores':scores[:5],'listing_seconds':round(elapsed,3),'phases':phase_checks}
        print(library,'OK',checks[library],flush=True)
    sheet=Image.new('RGB',(780,420*((len(overlays)+1)//2)), '#141b23');draw=ImageDraw.Draw(sheet)
    for i,(label,im) in enumerate(overlays):
        x=(i%2)*390;y=(i//2)*420;draw.text((x+10,y+8),label,fill='white');sheet.paste(im,(x+5,y+30))
    sheet.save(ROOT/'research/shape_real_jobs.jpg')
    (ROOT/'research/priority_shape_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    assert (ROOT/'web_settings.json').read_bytes()==settings
finally:server.shutdown();server.server_close()
