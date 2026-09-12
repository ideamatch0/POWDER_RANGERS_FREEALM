window.createGalleryViewer=function({getState,api,reportError}) {
  const el=id=>document.getElementById(id);
  let key='',offset=0,current=null,serial=0,wasGallery=false;
  const kind={changement_local:'Changement local',derive_locale:'Dérive locale',luminosite_globale:'Variation de luminosité',derive_globale:'Dérive globale',niveau_gris:'Écart au gris initial'};
  const status={a_examiner:'À examiner',retenue:'Retenue',ecartee:'Écartée'};
  const url=(id,prediction,anchor)=>'/api/gallery/image?'+new URLSearchParams({run:getState().run,id,...(prediction===undefined?{}:{prediction}),...(anchor===undefined?{}:{anchor})});
  const svgNode=(name,attrs)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',name);for(const [k,v]of Object.entries(attrs))node.setAttribute(k,v);return node;};
  function photograph(target,record,prediction) {
    target.replaceChildren();
    const cropped=prediction!==undefined,bounds=cropped?record.contexts[prediction]:[0,0,record.width,record.height],w=bounds[2]-bounds[0],h=bounds[3]-bounds[1];
    target.style.aspectRatio=w+'/'+h;
    const a=document.createElement('a');a.href=url(record.id,prediction,record.anchor);a.target='_blank';a.rel='noopener';
    const img=document.createElement('img');img.src=a.href;img.alt='Photo Aalto · acquisition '+record.counter+(cropped?' · gros plan':'');a.append(img);target.append(a);
    const svg=svgNode('svg',{viewBox:bounds[0]+' '+bounds[1]+' '+w+' '+h,'aria-hidden':'true'});
    const indices=cropped?[prediction]:record.predictions.map((_,i)=>i);
    indices.forEach(i=>{const p=record.predictions[i],b=p.box;const rect=svgNode('rect',{x:b[0],y:b[1],width:b[2]-b[0],height:b[3]-b[1],fill:cropped?'none':'#ff334408',stroke:record.anchor?'#80bedc':p.status==='ecartee'?'#929baa':'#ff4054','stroke-dasharray':record.anchor?'5 4':'none','stroke-width':2,'vector-effect':'non-scaling-stroke'});
      if(!cropped){rect.style.pointerEvents='all';rect.style.cursor='pointer';rect.onclick=()=>{el('gallery-prediction').value=String(i);showPrediction();};}svg.append(rect);
    });
    svg.style.display=el('gallery-overlay').checked?'':'none';target.append(svg);
  }
  function showPrediction(){
    if(!current)return;
    const i=Number(el('gallery-prediction').value),p=current.predictions[i];
    el('gallery-decision').hidden=!p;
    if(p){photograph(el('gallery-crop'),current,i);el('gallery-comment').value=p.comment;el('gallery-saved').textContent=status[p.status];
      el('gallery-warning').textContent=(kind[p.kind]||p.kind)+' · dépassement du seuil × '+p.score.toFixed(2)+'. Même cadrage et même échelle de gris avant / après.';
    }else{el('gallery-crop').replaceChildren();el('gallery-crop').textContent=!current.ready?'Lancez « Analyser ce job » pour obtenir les indications.':current.error?'Image non analysée : '+current.error:current.analyzed===false?'Image d’initialisation de l’historique.':'Aucune indication calculée sur cette photo.';el('gallery-warning').textContent='Une absence d’indication ne valide pas la pièce.';}
    ['before','after'].forEach((position,index)=>{
      const target=el('gallery-'+position),neighbor=current.neighbors?.[index],label=index?'Après':'Avant';
      target.replaceChildren();el('gallery-'+position+'-label').textContent=label+(neighbor?' · acquisition '+neighbor.counter:' · acquisition absente');
      if(!p){target.textContent='Sélectionnez une indication.';return;}
      if(!neighbor){target.textContent='Image absente de cette séquence.';return;}
      if(neighbor.width!==current.width||neighbor.height!==current.height){target.textContent='Dimensions différentes : cadrage commun indisponible.';return;}
      photograph(target,{id:neighbor.id,anchor:current.id,counter:neighbor.counter,width:current.width,height:current.height,contexts:current.contexts,predictions:current.predictions},i);
    });
  }
  async function choose(id,prediction=0){
    const token=++serial,run=getState().run;
    const record=await api('/api/gallery/detail?'+new URLSearchParams({run,id}));if(token!==serial||run!==getState().run)return;
    current=record;
    el('gallery-title').textContent='Acquisition '+record.counter+' · '+record.predictions.length+' indication(s) automatique(s)';
    el('gallery-meta').textContent=record.name+' · étape et hauteur non attribuées'+(Number.isFinite(record.mean_gray)?' · gris moyen '+record.mean_gray.toFixed(2)+' / 255':'');
    photograph(el('gallery-photo'),record);
    el('gallery-prediction').replaceChildren(...record.predictions.map((p,i)=>{const o=document.createElement('option');o.value=i;o.textContent=(i+1)+'. '+(kind[p.kind]||p.kind)+' · '+status[p.status];return o;}));
    el('gallery-prediction').disabled=!record.predictions.length;
    if(record.predictions.length)el('gallery-prediction').value=String(Math.min(prediction,record.predictions.length-1));
    showPrediction();
    el('gallery-list').querySelectorAll('button').forEach(b=>b.classList.toggle('selected',Number(b.dataset.id)===id));
  }
  async function load(){
    const run=getState().run,token=++serial;
    const data=await api('/api/gallery?'+new URLSearchParams({run,offset,detected:el('gallery-detected').checked?'1':'0'}));if(run!==getState().run||token!==serial)return;
    el('gallery-total').textContent=data.total;el('gallery-list').replaceChildren();
    for(const item of data.items){const b=document.createElement('button');b.className='event';b.dataset.id=item.id;const strong=document.createElement('strong');strong.textContent='Acquisition '+item.counter;const small=document.createElement('small');small.textContent=item.detections+' indication(s) automatique(s)';b.append(strong,small);b.onclick=()=>choose(item.id).catch(reportError);el('gallery-list').append(b);}
    el('gallery-page').textContent=data.total?(offset+1)+'–'+Math.min(offset+25,data.total)+' / '+data.total:'0';el('gallery-prev').disabled=offset===0;el('gallery-next').disabled=offset+25>=data.total;
    if(data.items.length)await choose(data.items[0].id);
    else{current=null;el('gallery-title').textContent='Aucune photo pour ce filtre';['gallery-photo','gallery-crop','gallery-before','gallery-after','gallery-prediction'].forEach(id=>el(id).replaceChildren());el('gallery-meta').textContent='';el('gallery-warning').textContent='';el('gallery-decision').hidden=true;}
  }
  function evaluation(state){
    const c=state.calibration,m=state.analysis;if(!c)return;
    const metrics=[['Gris initial · / 255',c.mean_gray.toFixed(2)],['Photos de calibration',c.sample_images],['Photos évaluées',m?.evaluated??'—'],['Photos avec indications',m?.flagged_images??'—'],['Indications',m?.detections??'—'],['Images en erreur',m?m.errors.length:'—']];
    el('gallery-metrics').replaceChildren(...metrics.map(([label,value])=>{const div=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('span');strong.textContent=value;small.textContent=label;div.append(strong,small);return div;}));
    el('gallery-protocol').textContent=m?m.measured+' photos mesurées · '+m.warmup_images+' d’initialisation · '+m.gaps+' rupture(s) de séquence · '+m.seconds.toFixed(1)+' s. Seuil local minimal '+m.config.min_change_gray+' / 255, zones '+m.config.tile_px+' × '+m.config.tile_px+' pixels, intervalle '+m.step+'.':'La calibration est prête. Cliquez sur « Analyser ce job » pour parcourir toute la bibliothèque.';
    el('gallery-quality').textContent=m&&m.flagged_images>.8*m.evaluated?'Plus de 80 % des photos évaluées sont signalées. Vérifiez le cadrage du lit, augmentez le seuil ou la taille des zones, et vérifiez l’intervalle d’acquisition. Ces changements ne désignent pas nécessairement des défauts.':'Indications de changement à interpréter visuellement. Calcul effectué uniquement à partir des photos de cette fabrication.';
    el('gallery-evaluation-download').hidden=!m;
    el('gallery-evaluation-download').href='/api/gallery/evaluation?'+new URLSearchParams({run:state.run});el('gallery-evaluation-download').download='analyse_job.json';
  }
  async function decide(value){
    if(!current)return;
    const index=Number(el('gallery-prediction').value),p=current.predictions[index];if(!p)return;
    const run=getState().run,id=current.id,comment=el('gallery-comment').value;
    await api('/api/gallery/decision',{run,id,prediction:p.key,status:value,comment});
    if(run===getState().run&&current?.id===id)await choose(id,index);
  }
  el('gallery-detected').onchange=()=>{offset=0;load().catch(reportError);};
  el('gallery-overlay').onchange=()=>{if(current){photograph(el('gallery-photo'),current);showPrediction();}};
  el('gallery-prev').onclick=()=>{offset=Math.max(0,offset-25);load().catch(reportError);};el('gallery-next').onclick=()=>{offset+=25;load().catch(reportError);};
  el('gallery-prediction').onchange=showPrediction;
  el('gallery-keep').onclick=()=>decide('retenue').catch(reportError);el('gallery-dismiss').onclick=()=>decide('ecartee').catch(reportError);el('gallery-pending').onclick=()=>decide('a_examiner').catch(reportError);
  el('gallery-export').onclick=async()=>{try{const response=await fetch('/api/gallery/report?'+new URLSearchParams({run:getState().run}));if(!response.ok)throw Error((await response.json()).error);const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='rapport_aalto.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch(error){reportError(error);}};
  return {setState(state){const gallery=state.dataset.mode==='gallery';el('gallery-space').hidden=!gallery;
    if(gallery){el('review-space').hidden=true;el('stack-space').hidden=true;
      ['gallery-keep','gallery-dismiss','gallery-pending','gallery-export'].forEach(id=>el(id).disabled=state.running||!state.analysis);
      const next=state.run+':'+(state.calibration?.signature||'')+':'+(state.analysis?.signature||'');
      if(next!==key){key=next;offset=0;serial++;el('gallery-detected').checked=Boolean(state.analysis?.flagged_images);load().catch(reportError);evaluation(state);}}
    else if(wasGallery){el('review-space').hidden=false;key='';current=null;serial++;}
    wasGallery=gallery;
  }};
};
