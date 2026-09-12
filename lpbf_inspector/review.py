"""Pages HTML locales de revue ; images de contexte chargées uniquement à l'export."""
import base64
import hashlib
from html import escape
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw
import numpy as np
from inspector import Config, connect, event_fingerprint, gray_pixels, metadata, summary
from imaging import context_box
from persistence import minimum_count
from priority import priority_text, PRIORITY_HELP

CSS = """
body{font:16px/1.5 system-ui,sans-serif;background:#f3f5f7;color:#193044;margin:0}
main{max-width:1250px;margin:auto;padding:32px}h1{font-size:32px;margin:0 0 8px}
.toolbar{position:sticky;top:0;background:#193044;color:white;padding:16px;z-index:1}
button,select,textarea{font:inherit;padding:8px;border:1px solid #b5c5d0;border-radius:5px}
button{cursor:pointer;background:#fff;color:#193044;margin:4px}
article{background:white;border:1px solid #d8e0e5;border-radius:8px;margin:24px 0;padding:20px;break-inside:avoid}
.images{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}figure{margin:0}img{width:100%;height:auto}
figcaption,small{font-size:12px;color:#536775;overflow-wrap:anywhere}textarea{display:block;width:96%;margin-top:12px}
.tag{color:#a52020;font-weight:600}.decision{margin-top:16px}pre{white-space:pre-wrap;font-size:12px}
.overview{display:flex;align-items:center;gap:20px;background:#f4f8fa;padding:12px;margin:12px 0}.overview figure{width:180px;flex-shrink:0}.images figure.current{border:2px solid #d93636;padding:4px}.comparison-note{font-size:13px;color:#536775}
@media(max-width:750px){.images{grid-template-columns:1fr}main{padding:15px}}
@media print{.toolbar,.decision,button,details{display:none}body{background:white}main{padding:0}article{border:1px solid #bbb}}
"""

SCRIPT = """
const cards=[...document.querySelectorAll('article')];
function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function decisions(){return cards.map(c=>({id:Number(c.dataset.id),snapshot:c.dataset.snapshot,status:c.querySelector('select').value,comment:c.querySelector('textarea').value}))}
document.getElementById('save').onclick=()=>download('decisions.json',JSON.stringify({project_key:document.body.dataset.project,decisions:decisions()},null,2),'application/json');
document.getElementById('final').onclick=()=>{
 const chosen=cards.filter(c=>c.querySelector('select').value==='retenue');
 const html=document.createElement('html');html.lang='fr';
 const head=document.head.cloneNode(true);head.querySelectorAll('script').forEach(x=>x.remove());html.append(head);
 const body=document.createElement('body');const main=document.createElement('main');
 const title=document.createElement('h1');title.textContent='Rapport des indications retenues';main.append(title);
 const scope=document.getElementById('scope').cloneNode(true);main.append(scope);
 const context=document.getElementById('context').cloneNode(true);context.open=true;main.append(context);
 const counts=document.createElement('p');counts.textContent=chosen.length+' indication(s) retenue(s) sur cette page. '+cards.filter(c=>c.querySelector('select').value==='a_examiner').length+' encore à examiner sur cette page.';main.append(counts);
 for(const c of chosen){const copy=c.cloneNode(true);copy.querySelectorAll('details').forEach(d=>d.open=true);const note=document.createElement('p');note.textContent='Commentaire : '+c.querySelector('textarea').value;copy.querySelector('.decision').replaceWith(note);main.append(copy)}
 body.append(main);html.append(body);download('rapport_indications_retenues.html','<!doctype html>'+html.outerHTML,'text/html');
};
document.getElementById('restore').onchange=async event=>{
 try{const file=event.target.files[0];if(!file)return;const data=JSON.parse(await file.text());
 if(data.project_key!==document.body.dataset.project)throw Error('Ce fichier correspond à un autre projet.');
 const updates=[];for(const item of data.decisions){const card=cards.find(c=>Number(c.dataset.id)===item.id);if(!card)continue;
 if(card.dataset.snapshot!==item.snapshot)throw Error('Une indication a changé : régénérer la revue.');
 if(!['a_examiner','retenue','ecartee'].includes(item.status))throw Error('Statut inconnu');updates.push([card,item]);}
 for(const [card,item] of updates){card.querySelector('select').value=item.status;card.querySelector('textarea').value=item.comment||''}
 }catch(error){alert(error.message)}
};
"""


def picture(row, config, box=None, crop=None, expected_size=None, reference=False):
    if row is None:
        return '<p>Image unavailable for this layer.</p>'
    try:
        with Image.open(row['path']) as source:
            if expected_size and source.size != tuple(expected_size):
                raise ValueError('Different image dimensions: comparison unavailable.')
            if crop:
                if not 0 <= crop[0] < crop[2] <= source.width or not 0 <= crop[1] < crop[3] <= source.height:
                    raise ValueError('Crop outside the image.')
                source = source.crop(crop)
            original_w, original_h = source.size
            source = Image.fromarray(np.rint(gray_pixels(source, config)).astype(np.uint8))
            source.thumbnail((720, 560))
            preview = source.convert('RGB')
        if box:
            xscale, yscale = preview.width/original_w, preview.height/original_h
            left, top = crop[:2] if crop else (0,0)
            coords = [(box[0]-left)*xscale, (box[1]-top)*yscale,
                      (box[2]-left)*xscale, (box[3]-top)*yscale]
            ImageDraw.Draw(preview).rectangle(coords, outline='#64a6c4' if reference else '#ef2b2b', width=2 if reference else 3)
        buf = io.BytesIO()
        preview.save(buf, format='JPEG', quality=85)
        image = '<img alt="Layer photograph" src="data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()+'">'
    except (OSError, ValueError) as error:
        image = '<p>Image unavailable: '+escape(str(error))+'</p>'
    return image+'<figcaption>'+escape(Path(row['path']).name)+'</figcaption>'


def create_review(project, offset=0, limit=100, retained_only=False, min_consecutive=1):
    min_consecutive=minimum_count(min_consecutive)
    if offset < 0 or not 1 <= limit <= 500:
        raise ValueError('offset >= 0 et 1 <= limit <= 500 requis ; exporter par pages pour borner la mémoire.')
    db = connect(project)
    try:
        definition = metadata(db, 'definition')
        if not definition:
            raise ValueError('Projet non initialisé.')
        config = Config(**definition['config'])
        key = hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()
        where = "WHERE status='retenue'" if retained_only else ''
        where += (' AND ' if where else 'WHERE ')+'end_layer-start_layer+1>=?'
        total = db.execute('SELECT COUNT(*) FROM events '+where,(min_consecutive,)).fetchone()[0]
        events = db.execute('SELECT * FROM events '+where+' ORDER BY start_layer,camera,phase,id LIMIT ? OFFSET ?', (min_consecutive,limit, offset))
        out = Path(project)/(('retained' if retained_only else 'review')+f'_{offset:06d}.html')
        with out.open('w', encoding='utf-8') as stream:
            stream.write('<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LPBF · revue des indications</title><style>'+CSS+'</style></head><body data-project="'+key+'">')
            stream.write('<div class="toolbar"><button id="save">Sauvegarder les décisions JSON</button><button id="final">Exporter les indications retenues</button><label>Recharger des décisions <input id="restore" type="file" accept=".json"></label></div><main><h1>LPBF · revue des indications</h1>')
            scope = f'Page : indications {min(offset+1,total)} à {min(offset+limit,total)} sur {total}. '
            scope += 'Périmètre : indications retenues en base.' if retained_only else 'Périmètre : ensemble des indications détectées.'
            scope += f' Persistance minimale : {min_consecutive} couches consécutives. Les indications plus brèves sont masquées, sans effacer leurs décisions.'
            stream.write('<p id="scope">'+escape(scope)+'</p>')
            stream.write('<p>Prototype exploratoire. Les cadres indiquent des zones dont l’aspect a changé. Le score exprime un dépassement de seuil, pas une probabilité de défaut.'+('' if retained_only else ' Les décisions ne sont conservées qu’après sauvegarde JSON.')+'</p>')
            stream.write('<details id="context"><summary>Paramètres et couverture de l’analyse</summary><pre>'+escape(json.dumps({'definition': definition, 'couverture': summary(db)}, ensure_ascii=False, indent=2))+'</pre></details>')
            for event in events:
                peak = db.execute('SELECT * FROM frames WHERE id=?', (event['peak_frame'],)).fetchone()
                box = json.loads(event['box'])
                geometry = json.loads(peak['geometry'])
                size = (geometry['width'],geometry['height'])
                crop = context_box(box,*size)
                camera, phase, layer = peak['camera'], peak['phase'], peak['layer']
                stream.write(f'<article data-id="{event["id"]}" data-snapshot="{event_fingerprint(event)}"><h2>Indication {event["id"]} · '+escape(event['kind'].replace('_', ' '))+'</h2>')
                stream.write('<p>'+escape(f"Canal {camera} · {phase} · couches {event['start_layer']}–{event['end_layer']} · pic couche {layer}, z = {config.z(layer):.3f} mm")+'</p>')
                stream.write('<p>'+escape(priority_text(event))+'</p><details><summary>Calcul du score</summary>'+escape(PRIORITY_HELP)+'</details>')
                stream.write('<div class="overview"><figure>'+picture(peak,config,box)+'</figure><p>Vue d’ensemble de la couche signalée.<br>Le cadre rouge situe l’indication.</p></div>')
                stream.write('<p class="tag">Zone au pic, pixels [x0,y0,x1,y1] : '+escape(str(box))+'</p>')
                stream.write(f'<p class="comparison-note">Gros plans : même cadrage de {crop[2]-crop[0]} × {crop[3]-crop[1]} pixels et même échelle de gris. Le cadre bleu repère le même emplacement avant et après.</p><div class="images">')
                for step, label in ((-1,'Couche précédente'), (0,'Couche au pic'), (1,'Couche suivante')):
                    row = db.execute('SELECT * FROM frames WHERE camera=? AND phase=? AND layer=?', (camera,phase,layer+step)).fetchone()
                    stream.write('<figure'+(' class="current"' if step==0 else '')+'><strong>'+label+f' · {layer+step}</strong>'+picture(row,config,box,crop,size,reference=step!=0)+'</figure>')
                stream.write('</div><details><summary>Autre étape à la même couche</summary>')
                other = 'fusion' if phase == 'etalement' else 'etalement'
                counterpart = db.execute('SELECT * FROM frames WHERE camera=? AND phase=? AND layer=?', (camera,other,layer)).fetchone()
                stream.write('<figure>'+escape(other)+picture(counterpart,config,crop=crop,expected_size=size)+'</figure></details><div class="decision"><label>Décision <select>')
                for value, label in (('a_examiner','À examiner'),('retenue','Retenue'),('ecartee','Écartée')):
                    stream.write('<option value="'+value+'"'+(' selected' if event['status']==value else '')+'>'+label+'</option>')
                stream.write('</select></label><textarea aria-label="Commentaire" placeholder="Observation de l’opérateur">'+escape(event['comment'])+'</textarea></div></article>')
            stream.write('</main><script>'+SCRIPT+'</script></body></html>')
        return out.resolve()
    finally:
        db.close()
