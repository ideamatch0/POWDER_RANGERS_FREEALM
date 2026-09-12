"""Installe les photographies PB originales et leurs annotations, sans attribuer de couches."""
import hashlib
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'research'/'aalto_originals.zip.part'
if hashlib.file_digest(archive.open('rb'),'md5').hexdigest()!='9d5ed884aecacb9ada5d0cca7c15d4b7':
    raise ValueError('L’archive diffère de l’empreinte publiée par Zenodo.')
destination=ROOT/'datasets'/'aalto_pb'
destination.mkdir(parents=True,exist_ok=True)
records=[]
with zipfile.ZipFile(archive) as zipped:
    by_name={Path(i.filename).name:i for i in zipped.infolist() if '/PB_label/' in i.filename and i.filename.lower().endswith('.xml')}
    images=sorted([i for i in zipped.infolist() if '/PB/' in i.filename and i.filename.lower().endswith('.jpg')],key=lambda i:i.filename)
    for index,info in enumerate(images,1):
        if info.file_size>20_000_000: raise ValueError('Image trop grande.')
        name=Path(info.filename).name
        data=zipped.read(info)
        (destination/name).write_bytes(data)
        parts=name.split('_')
        record={'id':index,'name':name,'job':parts[0],'counter':int(parts[1]),'timestamp':parts[2].removesuffix('.jpg'),
                'sha256':hashlib.sha256(data).hexdigest(),'annotations':[],'width':1280,'height':1024}
        annotation=by_name.get(Path(name).with_suffix('.xml').name)
        if annotation:
            raw=zipped.read(annotation)
            (destination/Path(annotation.filename).name).write_bytes(raw)
            tree=ET.fromstring(raw)
            record['width']=int(tree.findtext('size/width'))
            record['height']=int(tree.findtext('size/height'))
            record['original_annotations']=[]
            record['annotation_invalid']=0
            for item in tree.findall('object'):
                box=[int(item.findtext('bndbox/'+key)) for key in ('xmin','ymin','xmax','ymax')]
                record['original_annotations'].append(box)
                clipped=[max(0,min(record['width'],box[0])),max(0,min(record['height'],box[1])),
                         max(0,min(record['width'],box[2])),max(0,min(record['height'],box[3]))]
                if clipped!=box: record['annotation_clipped']=True
                if clipped[0]<clipped[2] and clipped[1]<clipped[3]:
                    record['annotations'].append({'label':item.findtext('name'),'box':clipped,'original_box':box})
                else:record['annotation_invalid']+=1
        records.append(record)
info={'complete':True,'images':len(records),'annotated_images':sum(bool(r['annotations']) for r in records),
      'doi':'10.5281/zenodo.14996806','source_url':'https://zenodo.org/records/14996806',
      'authors':'Xinyi Yin, Jan Sher Akmal, Mika Salmi, Roy Björkstrand (2025)','license':'CC BY 4.0',
      'archive_md5':'9d5ed884aecacb9ada5d0cca7c15d4b7','mode':'gallery',
      'note':'Trois jobs. Compteurs d’acquisition conservés ; correspondance couche/étape non qualifiée. Les cadres sont les annotations des auteurs, pas des détections du logiciel.',
      'records':records}
(destination/'provenance.json').write_text(json.dumps(info,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in info.items() if k!='records'},ensure_ascii=False,indent=2))
