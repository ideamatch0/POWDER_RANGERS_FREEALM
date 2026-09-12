"""Compare des tuiles PNG avec le lecteur HDF5 original, dont un chunk sans LZF."""
import hashlib
import json
import urllib.parse
from fetch_ornl_cylinders import ROOT,REPO,HDF5,SIZE,h5py,np,Image,RangeReader
index=json.loads((ROOT/'research/ornl_chunk_index.json').read_text())
url='https://huggingface.co/datasets/'+REPO+'/resolve/'+index['revision']+'/'+urllib.parse.quote(HDF5,safe='/')
reader=RangeReader(url,SIZE,budget=60_000_000,block_size=262144,max_blocks=128,cache_bust=True)
checked=[]
with h5py.File(reader,'r') as source:
    for channel,layer,y,x in [('0',70,267,2136),('0',169,2759,2759),('1',70,0,0),('1',169,1246,1335)]:
        ds=source['slices/camera_data/visible/'+channel]
        expected=np.asarray(ds[layer,y:min(2844,y+89),x:min(2844,x+89)])
        phase='fused' if channel=='0' else 'spread'
        file=ROOT/'datasets/ornl_cylinders_70_169'/f'cam1_layer{layer:04d}_{phase}.png'
        with Image.open(file) as image:actual=np.asarray(image)[y:y+expected.shape[0],x:x+expected.shape[1]]
        if not np.array_equal(actual,expected):raise ValueError('Pixels différents : '+file.name)
        checked.append({'file':file.name,'x':x,'y':y,'sha256':hashlib.sha256(actual.tobytes()).hexdigest()})
result={'identical':True,'checks':checked,'bytes_read':reader.received}
(ROOT/'research/ornl_pixels_verified.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
