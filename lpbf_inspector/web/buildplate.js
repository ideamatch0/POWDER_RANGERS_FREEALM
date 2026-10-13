window.PlateGeometry={
 normalize(x,y,width,height){return [Math.max(0,Math.min(1,x/width)),Math.max(0,Math.min(1,y/height))];},
 readPreset(value,width,height){
  if(value.version!==1||!Array.isArray(value.points)||value.points.length<3||value.points.length>64||value.points.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)))throw Error('Invalid build plate preset. Export a camera preset from Powder Ranger.');
  const size=value.image_size,changed=Array.isArray(size)&&Math.abs((size[0]/size[1])/(width/height)-1)>.01;
  return {points:value.points.map(p=>p.slice()),warning:changed?'Different image proportions: verify and adjust every point before saving.':'Preset loaded. Check that the outline matches this camera view before saving.'};
 }
};
window.createBuildPlateUI=function({getState,api,refresh,reportError}){
 const $=id=>document.getElementById(id),svg=$('plate-canvas');let draft={},reference=null,run='',drag=null,serial=0;
 const node=(tag,attributes)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attributes))n.setAttribute(k,v);return n;};
 const camera=()=>$('plate-camera').value,points=()=>draft[camera()]||[];
 function draw(){if(!reference)return;const {width:w,height:h}=reference,vertices=points();svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.style.aspectRatio=w+'/'+h;svg.replaceChildren();
  const params=new URLSearchParams({camera:camera(),phase:$('plate-phase').value});
  svg.append(node('image',{href:'/api/buildplate-image?'+params,width:w,height:h,'pointer-events':'none'}));
  if(vertices.length>=3){const path='M0 0H'+w+'V'+h+'H0Z M'+vertices.map(p=>(p[0]*w)+' '+(p[1]*h)).join('L')+'Z';svg.append(node('path',{d:path,fill:'#000','fill-opacity':'.68','fill-rule':'evenodd','pointer-events':'none'}));}
  if(vertices.length)svg.append(node(vertices.length>=3?'polygon':'polyline',{points:vertices.map(p=>(p[0]*w)+','+(p[1]*h)).join(' '),fill:'none',stroke:'#6be0fc','stroke-width':2,'vector-effect':'non-scaling-stroke','pointer-events':'none'}));
  vertices.forEach((p,i)=>svg.append(node('circle',{cx:p[0]*w,cy:p[1]*h,r:Math.max(w,h)/105,'data-vertex':i})));
  $('plate-description').textContent=reference.name+' · '+w+' × '+h+' pixels · '+vertices.length+' contour points · camera '+camera();
 }
 async function loadReference(){const ticket=++serial;reference=null;svg.replaceChildren();$('plate-save').disabled=true;try{
  const data=await api('/api/buildplate?'+new URLSearchParams({camera:camera(),phase:$('plate-phase').value}));if(ticket!==serial)return;
  if(data.library!==getState().dataset.id)throw Error('The job changed. Close and reopen this editor.');reference=data;draw();
 }catch(error){$('plate-feedback').textContent=error.message;}finally{if(ticket===serial)$('plate-save').disabled=!reference;}}
 $('define-buildplate').onclick=async()=>{const state=getState();run=state.run;draft=JSON.parse(JSON.stringify(state.buildplate?.outlines||{}));$('plate-feedback').textContent='';$('plate-phase').value='';
  $('plate-camera').replaceChildren(...(state.buildplate?.cameras||[]).map(c=>{const option=document.createElement('option');option.value=c;option.textContent=c;return option;}));
  $('plate-dialog').showModal();await loadReference();};
 $('plate-close').onclick=()=>{$('plate-dialog').close();serial++;};
 $('plate-camera').onchange=$('plate-phase').onchange=loadReference;
 function point(event){const matrix=svg.getScreenCTM();if(!matrix||!reference)return null;const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());return PlateGeometry.normalize(p.x,p.y,reference.width,reference.height);}
 svg.onpointerdown=event=>{if(!reference)return;event.preventDefault();const p=point(event);if(!p)return;
  if(event.target.hasAttribute('data-vertex')){drag=Number(event.target.getAttribute('data-vertex'));svg.setPointerCapture(event.pointerId);}else if(points().length<64){draft[camera()]=[...points(),p];draw();}else $('plate-feedback').textContent='Maximum 64 contour points.';};
 svg.onpointermove=event=>{if(drag===null)return;const p=point(event);if(p){draft[camera()][drag]=p;draw();}};
 svg.onpointerup=svg.onpointercancel=()=>{drag=null;};
 $('plate-undo').onclick=()=>{draft[camera()]=points().slice(0,-1);draw();};$('plate-clear').onclick=()=>{delete draft[camera()];draw();};
 svg.onkeydown=event=>{if(event.key==='Backspace'||(event.ctrlKey&&event.key==='z')){event.preventDefault();$('plate-undo').click();}};
 $('plate-export').onclick=()=>{if(!reference||points().length<3){$('plate-feedback').textContent='Define at least three contour points first.';return;}
  const blob=new Blob([JSON.stringify({version:1,camera:camera(),image_size:[reference.width,reference.height],points:points()},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='powder-ranger-buildplate-'+camera().replace(/[^a-z0-9_-]/gi,'_')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 $('plate-import').onchange=async event=>{try{const file=event.target.files[0];if(!file||!reference)return;if(file.size>65536)throw Error('Preset file is too large.');const value=PlateGeometry.readPreset(JSON.parse(await file.text()),reference.width,reference.height);draft[camera()]=value.points;$('plate-feedback').textContent=value.warning;draw();}catch(error){$('plate-feedback').textContent=error.message;}finally{event.target.value='';}};
 $('plate-save').onclick=async()=>{if(!reference)return;$('plate-save').disabled=true;try{
  const outlines=Object.fromEntries(Object.entries(draft).filter(([key,values])=>values.length));
  const state=await api('/api/buildplate',{run,outlines});run=state.run;await refresh();
  const complete=state.buildplate.cameras.length&&state.buildplate.cameras.every(c=>outlines[c]);
  $('plate-feedback').textContent=complete?'Saved. Close this editor and click Analyze this job. Gray level will be recalibrated inside the plate.':Object.keys(outlines).length?'Saved. Define the other cameras before selecting Inside build plate.':'Outline removed. Full image is selected.';
 }catch(error){$('plate-feedback').textContent=error.message;}finally{$('plate-save').disabled=false;}};
 return {setState(state){$('define-buildplate').disabled=state.running||state.dataset.empty;const cameras=state.buildplate?.cameras||[],outlines=state.buildplate?.outlines||{};$('region').querySelector('[value="plate"]').disabled=!cameras.length||!cameras.every(c=>outlines[c]?.length>=3);}};
};
