window.PlateGeometry={
 normalize(x,y,width,height){return [Math.max(0,Math.min(1,x/width)),Math.max(0,Math.min(1,y/height))];},
 readPreset(value,width,height){
  if(value.version!==1||!Array.isArray(value.points)||value.points.length<3||value.points.length>64||value.points.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)))throw Error('Invalid build plate preset. Export a camera preset from Powder Ranger.');
  const size=value.image_size,changed=Array.isArray(size)&&Math.abs((size[0]/size[1])/(width/height)-1)>.01;
  return {points:value.points.map(p=>p.slice()),warning:changed?'Different image proportions: verify and adjust every point before saving.':'Preset loaded. Check that the outline matches this camera view before saving.'};
 },
 fingerprint(outlines){return JSON.stringify(Object.fromEntries(Object.entries(outlines||{}).filter(([,p])=>p.length).sort(([a],[b])=>a.localeCompare(b))));}
};

window.createBuildPlateUI=function({getState,api,refresh,reportError}){
 const $=id=>document.getElementById(id),svg=$('plate-canvas'),dialog=$('plate-dialog');
 const clone=value=>JSON.parse(JSON.stringify(value));
 let draft={},baseline={},reference=null,run='',library='',storageKey='',drag=null,serial=0,busy=false,previousDraft=null,lastNotice='';
 const camera=()=>$('plate-camera').value,points=()=>draft[camera()]||[];
 const dirty=()=>PlateGeometry.fingerprint(draft)!==PlateGeometry.fingerprint(baseline);
 const outlines=()=>Object.fromEntries(Object.entries(draft).filter(([,p])=>p.length));
 const node=(tag,attributes)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attributes))n.setAttribute(k,v);return n;};

 function remember(){
  if(!storageKey)return;
  try{
   if(dirty())localStorage.setItem(storageKey,JSON.stringify({version:1,baseline:PlateGeometry.fingerprint(baseline),outlines:outlines()}));
   else localStorage.removeItem(storageKey);
  }catch(error){lastNotice='Browser draft storage is unavailable. Use Save outline before leaving this page.';}
 }
 function restore(data){
  storageKey='powder-ranger-buildplate-draft:'+data.profile+':'+data.library;
  previousDraft=null;$('plate-restore-draft').hidden=true;
  try{
   const record=JSON.parse(localStorage.getItem(storageKey)||'null');
   if(!record||record.version!==1||!record.outlines)return;
   for(const [c,p] of Object.entries(record.outlines)){
    if(!data.cameras.includes(c)||!Array.isArray(p)||p.length>64||p.some(point=>!Array.isArray(point)||point.length!==2||point.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)))return;
   }
   if(record.baseline===PlateGeometry.fingerprint(baseline)){
    draft=clone(record.outlines);$('plate-feedback').textContent='Previous draft restored. Close to save a complete outline.';
   }else{
    previousDraft=record.outlines;$('plate-restore-draft').hidden=false;
    $('plate-feedback').textContent='The saved outline changed since your draft. Showing the saved outline; your previous draft is still available.';
   }
  }catch(error){$('plate-feedback').textContent='Could not restore the browser draft. The saved outline is shown.';}
 }
 function draw(){
  if(!reference)return;
  const {width:w,height:h}=reference,vertices=points();svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.style.aspectRatio=w+'/'+h;svg.replaceChildren();
  const params=new URLSearchParams({camera:camera(),phase:$('plate-phase').value});
  svg.append(node('image',{href:'/api/buildplate-image?'+params,width:w,height:h,'pointer-events':'none'}));
  if(vertices.length>=3){const path='M0 0H'+w+'V'+h+'H0Z M'+vertices.map(p=>(p[0]*w)+' '+(p[1]*h)).join('L')+'Z';svg.append(node('path',{d:path,fill:'#000','fill-opacity':'.68','fill-rule':'evenodd','pointer-events':'none'}));}
  if(vertices.length)svg.append(node(vertices.length>=3?'polygon':'polyline',{points:vertices.map(p=>(p[0]*w)+','+(p[1]*h)).join(' '),fill:'none',stroke:'#6be0fc','stroke-width':2,'vector-effect':'non-scaling-stroke','pointer-events':'none'}));
  vertices.forEach((p,i)=>svg.append(node('circle',{cx:p[0]*w,cy:p[1]*h,r:Math.max(w,h)/105,'data-vertex':i})));
  $('plate-description').textContent=reference.name+' · '+w+' × '+h+' pixels · '+vertices.length+' contour points · camera '+camera();
 }
 function edited(){remember();$('plate-feedback').textContent=dirty()?'Draft updated. A complete outline will be saved when you close this editor.':'Saved outline · no changes.';draw();}
 function disable(value){
  busy=value;
  for(const element of dialog.querySelectorAll('button, select, input'))element.disabled=value;
  $('plate-save').disabled=value||!reference;
 }
 async function loadReference(initial=false){
  const ticket=++serial;reference=null;svg.replaceChildren();$('plate-save').disabled=true;
  if(initial)disable(true);
  try{
   const data=await api('/api/buildplate?'+new URLSearchParams({camera:camera(),phase:$('plate-phase').value}));if(ticket!==serial)return;
   if(data.library!==library||data.library!==getState().dataset.id)throw Error('The job changed. Close and reopen this editor.');
   if(initial){run=data.run;baseline=clone(data.outlines);draft=clone(data.outlines);$('plate-feedback').textContent=Object.keys(baseline).length?'Saved outline loaded. Changes will be saved when you close.':'No saved outline. Click the plate corners to define it.';restore(data);}
   reference=data;draw();
  }catch(error){$('plate-feedback').textContent=error.message;}finally{if(ticket===serial){if(initial)disable(false);else $('plate-save').disabled=!reference;}}
 }
 async function save(){
  if(!reference||busy)return false;
  disable(true);remember();
  try{
   const state=await api('/api/buildplate',{run,outlines:outlines()});
   run=state.run;baseline=clone(state.buildplate.outlines);draft=clone(baseline);remember();
   previousDraft=null;$('plate-restore-draft').hidden=true;
   const complete=state.buildplate.cameras.length&&state.buildplate.cameras.every(c=>baseline[c]?.length>=3);
   lastNotice=complete?'Outline saved for this job. Click Analyze this job to apply it to new results.':Object.keys(baseline).length?'Outline saved. Define the remaining cameras before analyzing inside the plate.':'Outline removed. Full image is selected.';
   $('plate-feedback').textContent=lastNotice;setState(state);draw();await refresh();return true;
  }catch(error){
   lastNotice='Outline could not be saved: '+error.message+' Your draft is retained in this browser.';
   $('plate-feedback').textContent=lastNotice;reportError(error);return false;
  }finally{disable(false);}
 }
 async function close(){
  if(busy)return;
  if(dirty()){
   remember();
   if(reference&&!Object.values(outlines()).some(p=>p.length<3))await save();
   else lastNotice='Incomplete draft retained in this browser. Add at least three points per contour to save and use it.';
  }
  dialog.close();serial++;reference=null;drag=null;setState(getState());
 }
 $('define-buildplate').onclick=async()=>{
  const state=getState();library=state.dataset.id;run=state.run;storageKey='';draft={};baseline={};lastNotice='';$('plate-feedback').textContent='Loading saved outline…';$('plate-phase').value='';
  $('plate-camera').replaceChildren(...(state.buildplate?.cameras||[]).map(c=>{const option=document.createElement('option');option.value=c;option.textContent=c;return option;}));
  dialog.showModal();await loadReference(true);
 };
 $('plate-close').onclick=close;
 dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
 $('plate-camera').onchange=$('plate-phase').onchange=()=>loadReference();
 $('plate-restore-draft').onclick=()=>{if(previousDraft){draft=clone(previousDraft);previousDraft=null;$('plate-restore-draft').hidden=true;edited();}};
 function point(event){const matrix=svg.getScreenCTM();if(!matrix||!reference)return null;const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());return PlateGeometry.normalize(p.x,p.y,reference.width,reference.height);}
 svg.onpointerdown=event=>{
  if(!reference||busy)return;event.preventDefault();const p=point(event);if(!p)return;
  if(event.target.hasAttribute('data-vertex')){drag=Number(event.target.getAttribute('data-vertex'));svg.setPointerCapture(event.pointerId);}
  else if(points().length<64){draft[camera()]=[...points(),p];edited();}else $('plate-feedback').textContent='Maximum 64 contour points.';
 };
 svg.onpointermove=event=>{if(drag===null||busy)return;const p=point(event);if(p){draft[camera()][drag]=p;edited();}};
 svg.onpointerup=svg.onpointercancel=()=>{drag=null;};
 $('plate-undo').onclick=()=>{draft[camera()]=points().slice(0,-1);edited();};
 $('plate-clear').onclick=()=>{delete draft[camera()];edited();};
 svg.onkeydown=event=>{if(event.key==='Backspace'||(event.ctrlKey&&event.key==='z')){event.preventDefault();$('plate-undo').click();}};
 $('plate-export').onclick=()=>{
  if(!reference||points().length<3){$('plate-feedback').textContent='Define at least three contour points first.';return;}
  const blob=new Blob([JSON.stringify({version:1,camera:camera(),image_size:[reference.width,reference.height],points:points()},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download='powder-ranger-buildplate-'+camera().replace(/[^a-z0-9_-]/gi,'_')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
 $('plate-import').onchange=async event=>{
  try{
   const file=event.target.files[0];if(!file||!reference)return;
   if(file.size>65536)throw Error('Preset file is too large.');
   const value=PlateGeometry.readPreset(JSON.parse(await file.text()),reference.width,reference.height);draft[camera()]=value.points;edited();$('plate-feedback').textContent=value.warning;
  }catch(error){$('plate-feedback').textContent=error.message;}finally{event.target.value='';}
 };
 $('plate-save').onclick=save;
 function setState(state){
  $('define-buildplate').disabled=state.running||state.dataset.empty;
  const cameras=state.buildplate?.cameras||[],saved=state.buildplate?.outlines||{};
  $('region').querySelector('[value="plate"]').disabled=!cameras.length||!cameras.every(c=>saved[c]?.length>=3);
  const count=cameras.filter(c=>saved[c]?.length>=3).length,active=Object.keys(state.config.plate_by_camera||{}).length>0;
  $('buildplate-status').textContent=(count?'Build plate saved · '+count+' / '+cameras.length+' camera(s). '+(active?(state.summary||state.analysis?'Current results use the saved outline.':'Ready to analyze inside the saved outline.'):'Current results do not use this outline. Select Inside build plate and analyze this job.'):'No build plate saved for this job.')+(library===state.dataset.id&&lastNotice?' '+lastNotice:'');
 }
 return {setState};
};
