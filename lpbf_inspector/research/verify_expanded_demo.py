"""Vérification HTTP en lecture seule de la série, des gros plans et des textures 3D."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from PIL import Image

BASE='http://127.0.0.1:8765'
ROOT=Path(__file__).resolve().parents[1]


def request(route,**params):
    with urlopen(BASE+route+('?' + urlencode(params) if params else ''),timeout=60) as response:
        return response.read()


def main():
    state=json.loads(request('/api/state'))
    assert not state['running'] and not state['error']
    assert state['summary']['images_mesurees']==200
    assert state['summary']['images_en_erreur']==0
    key=state['run']
    page=request('/').decode('utf-8')
    assert 'id="analysis-phase"' in page and 'id="stack-canvas"' in page
    assert request('/stack.js').startswith(b'/* Empilement')
    jobs=[]
    manifests={}
    for phase in ('etalement','fusion'):
        stack=json.loads(request('/api/stack',run=key,phase=phase,region='parts'))
        assert [f['layer'] for f in stack['frames']]==list(range(80,180))
        assert abs(stack['frames'][0]['z_mm']-1.6)<1e-9
        assert abs(stack['frames'][-1]['z_mm']-3.58)<1e-9
        assert stack['phase']==phase and stack['excluded_dimensions']==0
        manifests[phase]=stack
        jobs.extend(stack['frames'])
    started=time.perf_counter()
    def verify_texture(frame):
        raw=request('/api/stack-image',run=key,id=frame['id'],region='parts')
        with Image.open(io.BytesIO(raw)) as picture:
            picture.load()
            assert picture.size==(241,384)
        return len(raw)
    with ThreadPoolExecutor(max_workers=3) as workers:
        texture_bytes=sum(workers.map(verify_texture,jobs))
    listing=json.loads(request('/api/events',run=key))
    event=min(listing['items'],key=lambda e:(json.loads(e['box'])[2]-json.loads(e['box'])[0])*(json.loads(e['box'])[3]-json.loads(e['box'])[1]))
    crops={}
    for context in ('tight','standard','wide'):
        detail=json.loads(request('/api/event',run=key,id=event['id'],context=context))
        crop=detail['crop'];crops[context]=crop
        for index,frame in enumerate(detail['frames']):
            if not frame: continue
            assert frame['comparable']
            raw=request('/api/image',run=key,id=frame['id'],event=event['id'],context=context)
            with Image.open(io.BytesIO(raw)) as picture:
                assert picture.size==(crop[2]-crop[0],crop[3]-crop[1])
            if context=='standard':
                (ROOT/'research'/f'verified_crop_{index}.jpg').write_bytes(raw)
    result={'run':key,'images_analyzed':200,'analysis_seconds':state['progress'].get('elapsed'),
            'textures_verified':len(jobs),'texture_bytes':texture_bytes,
            'http_verification_seconds':round(time.perf_counter()-started,2),
            'indications':listing['total'],'event_checked':event['id'],'crops':crops}
    (ROOT/'research'/'verification_200.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
