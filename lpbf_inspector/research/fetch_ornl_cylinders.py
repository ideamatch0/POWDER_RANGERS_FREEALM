"""Extrait 100 couches ORNL sans annotations depuis les blocs HDF5 d'un miroir public."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT/'.deps'),str(ROOT)]
import h5py
import numpy as np
from PIL import Image
from inspector import Config
from remote_images import RangeReader

REPO='ppak10/ORNL-LPBF-Cylinders'
HDF5='source/2024-05-01 M2 AMMTO Fatigue Blanks 05.hdf5'
SIZE=127808960296
FIRST,LAST=70,169


def merge_spans(rows):
    groups=[]
    for row in sorted(rows,key=lambda r:r['offset']):
        if groups and row['offset']-groups[-1]['end']<=65536 and row['offset']+row['size']-groups[-1]['start']<=8_000_000:
            groups[-1]['end']=row['offset']+row['size'];groups[-1]['rows'].append(row)
        else:groups.append({'start':row['offset'],'end':row['offset']+row['size'],'rows':[row]})
    return groups


def main():
    dest=ROOT/'datasets'/'ornl_cylinders_70_169';dest.mkdir(parents=True,exist_ok=True)
    marker=dest/'provenance.json'
    if marker.is_file() and json.loads(marker.read_text(encoding='utf-8')).get('complete'):
        print('ORNL : bibliothèque déjà complète.',flush=True);return
    if shutil.disk_usage(dest).free<2_200_000_000:raise ValueError('Prévoir au moins 2,2 Go libres pour cette extraction.')
    index_path=ROOT/'research/ornl_chunk_index.json'
    if index_path.is_file():index=json.loads(index_path.read_text(encoding='utf-8'))
    else:
        with urllib.request.urlopen('https://huggingface.co/api/datasets/'+REPO,timeout=30) as r:repo=json.load(r)
        index={'revision':repo['sha'],'blocks':{},'first':FIRST,'last':LAST}
    url='https://huggingface.co/datasets/'+REPO+'/resolve/'+index['revision']+'/'+urllib.parse.quote(HDF5,safe='/')
    reader=RangeReader(url,SIZE,budget=100_000_000,block_size=262144,max_blocks=256,cache_bust=True)
    with h5py.File(reader,'r') as file:
        metadata={k:str(file.attrs[k]) for k in ('core/build_name','core/number_of_layers','material/layer_thickness','material/layer_thickness/units','slices/indexing')}
        for channel in ('0','1'):
            d=file['slices/camera_data/visible/'+channel]
            if d.shape!=(1117,2844,2844) or d.dtype!=np.uint8 or d.chunks!=(35,89,89) or d.compression!='lzf':
                raise ValueError('Format du canal visible inattendu.')
            for start in range(FIRST//35*35,LAST+1,35):
                key=f'{channel}_{start}'
                if key in index['blocks']:continue
                rows=[]
                for y in range(0,2844,89):
                    for x in range(0,2844,89):
                        info=d.id.get_chunk_info_by_coord((start,y,x))
                        if info.byte_offset is None:raise ValueError('Bloc image absent.')
                        rows.append({'offset':info.byte_offset,'size':info.size,'mask':info.filter_mask,'y':y,'x':x})
                # Validation directe d'un morceau de capteur, sans charger un masque de segmentation.
                sample=np.asarray(d[start,0:89,0:89]);sample_hash=hashlib.sha256(sample.tobytes()).hexdigest()
                index['blocks'][key]={'rows':rows,'sample_sha256':sample_hash}
                index_path.write_text(json.dumps(index),encoding='utf-8')
                print('ORNL index',key,'·',round(sum(r['size'] for r in rows)/1e6),'Mo utiles',flush=True)
    results=[];started=time.monotonic();network=reader.received
    # Un seul bloc temporel sur disque ; jamais le HDF5 de 128 Go ni les 200 photos en RAM.
    for channel in ('0','1'):
        phase='fused' if channel=='0' else 'spread'
        for start in range(FIRST//35*35,LAST+1,35):
            layers=range(max(FIRST,start),min(LAST+1,start+35))
            existing=[]
            for layer in layers:
                target=dest/f'cam1_layer{layer:04d}_{phase}.png';record=target.with_suffix('.json')
                if target.is_file() and record.is_file():
                    row=json.loads(record.read_text())
                    if hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']:existing.append(row)
            if len(existing)==len(layers):results.extend(existing);continue
            block=index['blocks'][f'{channel}_{start}'];spans=merge_spans(block['rows'])
            stack_path=dest/'extracting_layers.raw'
            volume=np.memmap(stack_path,dtype=np.uint8,mode='w+',shape=(35,2844,2844))
            print(f'ORNL canal {channel}, couches {start}–{start+34} : {len(spans)} lectures groupées',flush=True)
            def fetch(span):
                r=RangeReader(url,SIZE,budget=9_000_000,cache_bust=True)
                return span,r.range(span['start'],span['end']-span['start'])
            count=0
            try:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    iterator=iter(spans);pending=set()
                    for _ in range(min(4,len(spans))):pending.add(pool.submit(fetch,next(iterator)))
                    while pending:
                        done,pending=wait(pending,return_when=FIRST_COMPLETED)
                        for future in done:
                            span,data=future.result();network+=len(data)
                            for row in span['rows']:
                                offset=row['offset']-span['start'];compressed=data[offset:offset+row['size']]
                                # Un fichier neuf évite la réutilisation du cache de chunks HDF5
                                # quand la taille compressée ou le masque du filtre change.
                                try:
                                    if row['mask']==1:
                                        # LZF ignoré : ce chunk contient directement les pixels.
                                        tile=np.frombuffer(compressed,dtype=np.uint8).reshape(35,89,89)
                                    elif row['mask']==0:
                                      with h5py.File(io.BytesIO(),'w') as scratch:
                                        decoder=scratch.create_dataset('chunk',shape=(35,89,89),chunks=(35,89,89),dtype='u1',compression='lzf')
                                        decoder.id.write_direct_chunk((0,0,0),compressed,filter_mask=row['mask'])
                                        tile=decoder[:]
                                    else:raise ValueError('Masque de filtre HDF5 inconnu.')
                                except OSError:
                                    (ROOT/'research/failed_chunk.bin').write_bytes(compressed)
                                    (ROOT/'research/failed_chunk.json').write_text(json.dumps(row))
                                    raise
                                y,x=row['y'],row['x'];h,w=min(89,2844-y),min(89,2844-x)
                                volume[:,y:y+h,x:x+w]=tile[:,:h,:w]
                            count+=1
                            if count%20==0 or count==len(spans):print(f'ORNL blocs {count}/{len(spans)} · réseau cumulé {network/1e6:.0f} Mo',flush=True)
                            try:pending.add(pool.submit(fetch,next(iterator)))
                            except StopIteration:pass
                            del data
                volume.flush()
                if hashlib.sha256(np.asarray(volume[0,:89,:89]).tobytes()).hexdigest()!=block['sample_sha256']:
                    raise ValueError('Le décodage des blocs diffère de la lecture HDF5 de référence.')
                for layer in layers:
                    target=dest/f'cam1_layer{layer:04d}_{phase}.png';pixels=np.asarray(volume[layer-start])
                    tmp=target.with_suffix('.part');Image.fromarray(pixels).save(tmp,format='PNG',compress_level=4)
                    with Image.open(tmp) as saved:
                        if not np.array_equal(pixels,np.asarray(saved)):raise ValueError('Conversion PNG non fidèle.')
                    tmp.replace(target)
                    row={'file':target.name,'hdf5_dataset':'/slices/camera_data/visible/'+channel,'layer':layer,
                         'phase':'fusion' if channel=='0' else 'etalement','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                         'pixels_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'bytes':target.stat().st_size,'pixels_preserved':True}
                    target.with_suffix('.json').write_text(json.dumps(row),encoding='utf-8');results.append(row)
                print(f'ORNL : {len(results)}/200 photos enregistrées · {time.monotonic()-started:.0f} s',flush=True)
            finally:
                volume.flush();volume._mmap.close();del volume
                if stack_path.resolve().parent!=dest.resolve():raise ValueError('Chemin temporaire inattendu.')
                stack_path.unlink(missing_ok=True)
    if len(results)!=200:raise ValueError('La série extraite est incomplète.')
    config=Config(tile_px=32,layer_thickness_um=100,first_layer=0,first_layer_z_mm=0)
    provenance={'complete':True,'subset':True,'job':'M2 AMMTO Fatigue Blanks 05','images':200,'first_layer':FIRST,'last_layer':LAST,
                'source_url':'https://doi.org/10.13139/ORNLNCCS/2524534','mirror_url':'https://huggingface.co/datasets/'+REPO,
                'mirror_revision':index['revision'],'hdf5_file':HDF5,'hdf5_bytes':SIZE,'metadata':metadata,'config':asdict(config),
                'processing':'Canaux visibles corrigés par les producteurs (éclairage et perspective). Extraction des pixels uint8 en PNG sans perte. Aucune segmentation ni annotation chargée.',
                'license':'README du jeu : aucune restriction de réutilisation indiquée.',
                'z_convention':'Z = indice de couche × 0,1 mm, origine relative à l’indice 0 du jeu.',
                'network_bytes':network,'files':sorted(results,key=lambda r:r['file'])}
    marker.write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print('ORNL terminé :',sum(r['bytes'] for r in results),'octets PNG',flush=True)


if __name__=='__main__':main()
