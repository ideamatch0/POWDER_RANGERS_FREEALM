"""Récupère une série NIST cohérente par lectures HTTP partielles parallèles."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import time
import urllib.request
import zipfile
import zlib

from fetch_sample import RemoteZip, SOURCES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first',type=int,default=80)
    parser.add_argument('--last',type=int,default=179)
    parser.add_argument('--workers',type=int,default=4)
    args = parser.parse_args()
    if not 2 <= args.first <= args.last <= 250 or not 1 <= args.workers <= 4:
        parser.error('Couches communes A/B : 2 à 250 ; 1 à 4 téléchargements simultanés.')
    root = Path(__file__).resolve().parent.parent
    dest = root/'datasets'/f'nist_{args.first}_{args.last}'
    dest.mkdir(parents=True,exist_ok=True)
    url, archive_size = SOURCES['nist']
    with zipfile.ZipFile(RemoteZip(url,archive_size)) as archive:
        entries = []
        for info in archive.infolist():
            match = re.fullmatch(r'([AB])(\d{4})a\.PNG',Path(info.filename).name,re.I)
            if match and args.first <= int(match[2]) <= args.last:
                entries.append(info)
    expected = 2*(args.last-args.first+1)
    if len(entries)!=expected:
        raise ValueError('La série ne contient pas les deux étapes de toutes les couches demandées.')
    needed = sum(info.file_size for info in entries)
    if shutil.disk_usage(dest).free < needed + 200_000_000:
        raise ValueError('Espace disque insuffisant pour cette série et les fichiers temporaires.')
    print(f'Série {args.first}–{args.last} : {expected} images, {needed/1e6:.1f} Mo décompressés.',flush=True)

    def fetch(info):
        name = Path(info.filename).name
        target = dest/name
        previous = root/'datasets'/'nist_sample'/name
        for source in (target,previous):
            if source.is_file():
                data = source.read_bytes()
                if len(data)==info.file_size and zlib.crc32(data)==info.CRC:
                    if source!=target:
                        shutil.copy2(source,target)
                    return {'file':name,'archive_path':info.filename,'bytes':len(data),
                            'sha256':hashlib.sha256(data).hexdigest(),'reused':True}
        if info.file_size>50_000_000 or info.flag_bits&1:
            raise ValueError('Entrée ZIP non compatible avec ce téléchargement borné.')
        start = info.header_offset
        # Un seul GET par PNG ; 65 535 octets couvrent la taille maximale du champ extra local.
        end = min(archive_size-1,start+30+len(info.filename.encode('utf-8'))+65535+info.compress_size-1)
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'LPBF-Inspector-Research/0.2','Range':f'bytes={start}-{end}'})
                with urllib.request.urlopen(request,timeout=30) as response:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{archive_size}':
                        raise ValueError('Lecture partielle non respectée ; arrêt sans télécharger l’archive complète.')
                    block=response.read(end-start+2)
                if len(block)!=end-start+1:
                    raise ValueError('Réponse HTTP tronquée.')
                header=struct.unpack('<4s5H3I2H',block[:30])
                if header[0]!=b'PK\x03\x04':
                    raise ValueError('En-tête ZIP invalide.')
                begin=30+header[-2]+header[-1]
                compressed=block[begin:begin+info.compress_size]
                if info.compress_type==zipfile.ZIP_DEFLATED:
                    decoder=zlib.decompressobj(-15)
                    data=decoder.decompress(compressed,info.file_size+1)
                    if not decoder.eof:
                        raise ValueError('Entrée compressée incomplète ou taille excessive.')
                elif info.compress_type==zipfile.ZIP_STORED:
                    data=compressed
                else:
                    raise ValueError('Compression ZIP non prise en charge.')
                if len(data)!=info.file_size or zlib.crc32(data)!=info.CRC:
                    raise ValueError('Échec de la vérification taille/CRC du PNG.')
                temporary=target.with_suffix('.part')
                temporary.write_bytes(data)
                temporary.replace(target)
                return {'file':name,'archive_path':info.filename,'bytes':len(data),
                        'sha256':hashlib.sha256(data).hexdigest(),'reused':False}
            except (OSError,TimeoutError):
                if attempt==2:
                    raise
                time.sleep(1+attempt)

    results=[]
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(fetch,info) for info in entries]
        for future in as_completed(futures):
            result=future.result()
            results.append(result)
            if len(results)%10==0 or len(results)==expected:
                print(f'{len(results)}/{expected} images vérifiées · {(time.monotonic()-started):.0f} s',flush=True)
    provenance={'archive_url':url,'doi':'https://doi.org/10.18434/M32233',
                'selection':f'Couches {args.first} à {args.last}, éclairage a, étapes A et B',
                'first_layer':args.first,'last_layer':args.last,'images':expected,'layer_thickness_um':20,
                'complete':True,'files':sorted(results,key=lambda item:item['file'])}
    (dest/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Série complète : '+str(dest),flush=True)


if __name__=='__main__':
    main()
