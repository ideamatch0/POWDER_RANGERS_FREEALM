"""Extrait 100 couches NIST Scan Strategies en PNG sans perte, sans figures annotées."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import time
import zipfile
import zlib

import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from inspector import Config
from remote_images import RangeReader

ROOT=Path(__file__).resolve().parent.parent


def index_from_head(data):
    entries=[];pos=0
    while pos+zipfile.sizeCentralDir<=len(data):
        fields=struct.unpack(zipfile.structCentralDir,data[pos:pos+zipfile.sizeCentralDir])
        if fields[0]!=zipfile.stringCentralDir:raise ValueError('Sommaire ZIP invalide.')
        n,e,c=(fields[k] for k in (zipfile._CD_FILENAME_LENGTH,zipfile._CD_EXTRA_FIELD_LENGTH,zipfile._CD_COMMENT_LENGTH))
        if pos+46+n+e+c>len(data):break
        name=data[pos+46:pos+46+n].decode('utf-8' if fields[zipfile._CD_FLAG_BITS]&2048 else 'cp437')
        row={'name':name,'size':fields[zipfile._CD_UNCOMPRESSED_SIZE],'compressed':fields[zipfile._CD_COMPRESSED_SIZE],
             'offset':fields[zipfile._CD_LOCAL_HEADER_OFFSET],'crc':fields[zipfile._CD_CRC],
             'method':fields[zipfile._CD_COMPRESS_TYPE],'flags':fields[zipfile._CD_FLAG_BITS]}
        extra=data[pos+46+n:pos+46+n+e];ep=0
        while ep+4<=len(extra):
            tag,length=struct.unpack_from('<HH',extra,ep);ep+=4
            if tag==1:
                zp=ep
                for field in ('size','compressed','offset'):
                    if row[field]==0xffffffff:row[field]=struct.unpack_from('<Q',extra,zp)[0];zp+=8
            ep+=length
        if '/Layer Camera/' in name:entries.append(row)
        pos+=46+n+e+c
    return entries


def fetch_entry(reader,row):
    if row['flags']&1 or row['size']>20_000_000:raise ValueError('Entrée ZIP non prise en charge.')
    # Lire l’en-tête pour connaître la longueur exacte, puis uniquement cette image.
    header=reader.range(row['offset'],30)
    fields=struct.unpack('<4s5H3I2H',header)
    if fields[0]!=b'PK\x03\x04':raise ValueError('En-tête ZIP invalide.')
    start=row['offset']+30+fields[-1]+fields[-2]
    compressed=reader.range(start,row['compressed'])
    if row['method']==zipfile.ZIP_DEFLATED:
        dec=zlib.decompressobj(-15);data=dec.decompress(compressed,row['size']+1)
        if not dec.eof:raise ValueError('Décompression incomplète ou excessive.')
    elif row['method']==zipfile.ZIP_STORED:data=compressed
    else:raise ValueError('Compression ZIP inconnue.')
    if len(data)!=row['size'] or zlib.crc32(data)!=row['crc']:raise ValueError('Taille ou CRC invalide.')
    return data


def main():
    dest=ROOT/'datasets'/'nist_scan_2_101';dest.mkdir(parents=True,exist_ok=True)
    meta=json.loads((ROOT/'research/nist_3d_metadata.json').read_text())['ResultData'][0]
    source=next(c for c in meta['components'] if c.get('filepath')=='In-situ Meas Data.zip')
    reader=RangeReader(source['downloadURL'],source['size'],budget=10_000_000)
    # ZIP64 : la fin indique l’offset du sommaire. Son début contient les photos du lit.
    end=zipfile._EndRecData(reader)
    head=reader.range(end[zipfile._ECD_OFFSET],2*1024*1024)
    rows=index_from_head(head);chosen=[]
    for row in rows:
        match=re.fullmatch(r'([AB])(\d{4})\.bmp',Path(row['name']).name,re.I)
        if match and 2<=int(match[2])<=101:chosen.append((row,match[1].upper(),int(match[2])))
    expected={(phase,layer) for phase in 'AB' for layer in range(2,102)}
    if {(p,n) for _,p,n in chosen}!=expected or len(chosen)!=200:raise ValueError('Série A/B incomplète : ne pas importer.')
    if shutil.disk_usage(dest).free<1_700_000_000:raise ValueError('Moins de 1,7 Go libres : extraction différée.')
    started=time.monotonic();results=[]
    def fetch(item):
        row,phase,layer=item;target=dest/f'cam1_layer{layer:04d}_{"spread" if phase=="A" else "fused"}.png'
        record_path=target.with_suffix('.json')
        if target.is_file() and record_path.is_file():
            rec=json.loads(record_path.read_text());data=target.read_bytes()
            if hashlib.sha256(data).hexdigest()==rec['sha256']:return rec
        rr=RangeReader(source['downloadURL'],source['size'],budget=20_000_000)
        raw=fetch_entry(rr,row)
        with Image.open(io.BytesIO(raw)) as original:
            if original.size!=(2000,2000):raise ValueError('Résolution NIST inattendue.')
            image=original.convert('L');pixels=np.asarray(image).copy()
            tmp=target.with_suffix('.part');image.save(tmp,format='PNG',compress_level=4)
        with Image.open(tmp) as saved:
            if not np.array_equal(pixels,np.asarray(saved)):raise ValueError('La conversion PNG a modifié les pixels.')
        tmp.replace(target)
        rec={'file':target.name,'archive_path':row['name'],'source_crc32':row['crc'],'source_sha256':hashlib.sha256(raw).hexdigest(),
             'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'layer':layer,'phase':phase,'pixels_preserved':True}
        record_path.write_text(json.dumps(rec),encoding='utf-8');return rec
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(fetch,item) for item in chosen]):
            results.append(future.result())
            if len(results)%10==0:print(f'NIST : {len(results)}/200 photos vérifiées · {time.monotonic()-started:.0f} s',flush=True)
    config=Config(tile_px=32,layer_thickness_um=20,first_layer=1,first_layer_z_mm=.02)
    provenance={'complete':True,'job':'20180708-HY-3D-Scan-Strategies','images':200,'first_layer':2,'last_layer':101,'subset':True,
                'source_url':'https://doi.org/10.18434/M32044','archive_url':source['downloadURL'],'archive_size':source['size'],
                'archive_sha256_not_verified':source['checksum']['hash'],'license':'https://www.nist.gov/open/license',
                'processing':'BMP vers PNG sans perte. Pixels décodés identiques ; aucun cadre ni annotation ajouté.',
                'config':asdict(config),'files':sorted(results,key=lambda r:r['file'])}
    (dest/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print('NIST terminé :',sum(r['bytes'] for r in results),'octets PNG',flush=True)


if __name__=='__main__':main()
