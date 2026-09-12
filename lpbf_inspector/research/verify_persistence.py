"""Vérification HTTP des filtres sur les jobs installés, sans modifier leurs réglages."""
import http.client
import json
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from local_app import Application,ThreadingHTTPServer,make_handler
app=Application(ROOT);app.save_preferences=lambda:None
server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
threading.Thread(target=server.serve_forever,daemon=True).start()

def call(path,data=None,**query):
    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=60)
    try:
        headers={'Origin':f'http://127.0.0.1:{server.server_port}','Content-Type':'application/json'}
        c.request('POST' if data is not None else 'GET',path+'?'+urlencode(query) if query else path,
                  json.dumps(data) if data is not None else None,headers)
        response=c.getresponse();body=json.loads(response.read())
        if response.status!=200:raise ValueError(str(body))
        return body
    finally:c.close()
checks={}
try:
    for library in app.catalog.entries:
        app.select_library(library);initial=call('/api/state');run=initial['run']
        if not initial['analysis']:continue
        started=time.monotonic();counts={}
        for n in [1,2,3,5]:
            state=call('/api/review-settings',{'run':run,'min_consecutive':n})
            assert state['run']==run and state['analysis']==initial['analysis'] and state['calibration']==initial['calibration']
            listing=call('/api/events',run=run);counts[str(n)]=listing['total']
            assert all(e['consecutive_count']>=n for e in listing['items'])
            stack_count=0
            for phase in state['display_phases']:
                stack=call('/api/stack',run=run,phase=phase)
                assert all(e['consecutive_count']>=n for e in stack['events'])
                stack_count+=len(stack['events'])
            assert stack_count==listing['total']
        assert counts['1']>=counts['2']>=counts['3']>=counts['5']
        checks[library]={'visible_by_minimum':counts,'seconds':round(time.monotonic()-started,3),'same_run_and_calibration':True,'list_and_3d_consistent':True}
        print(library,checks[library],flush=True)
    (ROOT/'research/persistence_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
finally:server.shutdown();server.server_close()
