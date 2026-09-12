/* Empilement de plans photographiques. Rendu WebGL local, sans bibliothèque externe. */
(function () {
  'use strict';
  const position=frame=>frame.position??frame.z_mm;
  const phaseLabel={fusion:'after melting',etalement:'after spreading',acquisition:'unidentified stage',sequence0:'even sequence',sequence1:'odd sequence'};
  const scorePalette=[[255,223,98],[255,181,71],[255,139,62],[255,96,57],[255,48,71]];
  const scoreBand=score=>Math.min(4,Math.max(0,Math.floor((Number(score)||0)/20)));
  window.priorityColorCSS=score=>'rgb('+scorePalette[scoreBand(score)].join(',')+')';
  class PhotoStack {
    constructor(canvas) {
      this.canvas = canvas;
      this.gl = canvas.getContext('webgl', {alpha: false, antialias: true});
      if (!this.gl) throw Error('The 3D view requires WebGL in this browser. The 2D views remain available.');
      const gl = this.gl;
      const shader = (type, source) => {
        const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error('3D initialization: ' + gl.getShaderInfoLog(s));
        return s;
      };
      const vertex = shader(gl.VERTEX_SHADER, `
        attribute vec2 uv; varying vec2 tex;
        uniform vec2 plane; uniform vec2 angle;
        uniform float height; uniform float zoom; uniform float aspect;
        void main() {
          vec2 p = (uv - vec2(0.5)) * plane * vec2(1.0,-1.0);
          float x = cos(angle.x)*p.x - sin(angle.x)*p.y;
          float y = sin(angle.x)*p.x + cos(angle.x)*p.y;
          float screenY = sin(angle.y)*y + cos(angle.y)*height;
          gl_Position = vec4(x*zoom/aspect, screenY*zoom, 0.0, 1.0);
          gl_PointSize = 7.0;
          tex = uv;
        }`);
      const fragment = shader(gl.FRAGMENT_SHADER, `
        precision mediump float; varying vec2 tex;
        uniform sampler2D photograph; uniform float opacity; uniform bool border; uniform bool silhouette; uniform vec4 tint;
        void main() {
          vec4 sampleColor=texture2D(photograph,tex);
          gl_FragColor = border ? tint : vec4(sampleColor.rgb,silhouette ? sampleColor.a*opacity : opacity);
        }`);
      this.program = gl.createProgram(); gl.attachShader(this.program, vertex); gl.attachShader(this.program, fragment);
      gl.linkProgram(this.program);
      if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) throw Error('Could not initialize the 3D renderer.');
      gl.deleteShader(vertex); gl.deleteShader(fragment); gl.useProgram(this.program);
      this.attribute = gl.getAttribLocation(this.program, 'uv'); gl.enableVertexAttribArray(this.attribute);
      this.uniform = {};
      for (const name of ['plane','angle','height','zoom','aspect','opacity','border','photograph','tint','silhouette']) this.uniform[name] = gl.getUniformLocation(this.program, name);
      const buffer = data => {const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);return b;};
      this.triangles = buffer([0,0,1,0,0,1,0,1,1,0,1,1]);
      this.outline = buffer([0,0,1,0,1,1,0,1]);
      this.markBuffer=buffer([0,0]);this.showEvents=true;this.eventFilter='active';
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
      gl.disable(gl.DEPTH_TEST); gl.uniform1i(this.uniform.photograph,0);
      this.textures = new Map(); this.shapes=new Map();this.shapeMode='photos';this.scoreColors=true;
      this.metadata = null; this.cut = 0; this.step = 1; this.opacity = .12;
      this.yaw = -.35; this.pitch = .55; this.zoom = .68; this.queued = false;
      let drag = null,origin=null;
      canvas.addEventListener('pointerdown',e=>{origin=[e.clientX,e.clientY];drag=origin;canvas.setPointerCapture(e.pointerId);});
      canvas.addEventListener('pointermove',e=>{if(!drag)return;this.yaw+=(e.clientX-drag[0])*.008;this.pitch=Math.max(.12,Math.min(Math.PI/2,this.pitch-(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];this.draw();});
      canvas.addEventListener('pointerup',e=>{if(origin&&Math.hypot(e.clientX-origin[0],e.clientY-origin[1])<5)this.pick(e.clientX,e.clientY);drag=null;origin=null;});
      for (const event of ['pointercancel','lostpointercapture']) canvas.addEventListener(event,()=>{drag=null;origin=null;});
      canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.25,Math.min(4,this.zoom*Math.exp(-e.deltaY*.001)));this.draw();},{passive:false});
      canvas.addEventListener('keydown',e=>{
        if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','='].includes(e.key))return;
        e.preventDefault();if(e.key==='ArrowLeft')this.yaw-=.1;if(e.key==='ArrowRight')this.yaw+=.1;
        if(e.key==='ArrowUp')this.pitch=Math.min(Math.PI/2,this.pitch+.1);if(e.key==='ArrowDown')this.pitch=Math.max(.12,this.pitch-.1);
        if(e.key==='+'||e.key==='=')this.zoom=Math.min(4,this.zoom*1.1);if(e.key==='-')this.zoom=Math.max(.25,this.zoom/1.1);this.draw();
      });
      new ResizeObserver(()=>this.draw()).observe(canvas);
    }
    clearShapes() {for(const texture of this.shapes.values())this.gl.deleteTexture(texture);this.shapes.clear();this.draw();}
    clear() {for(const texture of this.textures.values())this.gl.deleteTexture(texture);this.textures.clear();this.clearShapes();this.metadata=null;this.draw();}
    visibleEvents() {
      if(!this.metadata||!this.showEvents)return [];
      const layer=this.metadata.frames[this.cut]?.layer;
      return (this.metadata.events||[]).filter(e=>e.layer<=layer && (this.eventFilter==='retained'?e.status==='retenue':e.status!=='ecartee') && (this.eventFilter!=='layer'||e.layer===layer));
    }
    project(x,y,z) {
      const m=this.metadata,rect=this.canvas.getBoundingClientRect(),max=Math.max(m.width,m.height);
      const px=((x-m.crop[0])/m.width-.5)*2*m.width/max,py=(.5-(y-m.crop[1])/m.height)*2*m.height/max;
      const low=position(m.frames[0]),range=position(m.frames[m.frames.length-1])-low,height=range?(z-low)/range*1.4-.7:0;
      const sx=Math.cos(this.yaw)*px-Math.sin(this.yaw)*py;
      const sy=Math.sin(this.pitch)*(Math.sin(this.yaw)*px+Math.cos(this.yaw)*py)+Math.cos(this.pitch)*height;
      return [rect.width/2+sx*this.zoom*rect.height/2,rect.height/2-sy*this.zoom*rect.height/2];
    }
    pick(clientX,clientY) {
      const rect=this.canvas.getBoundingClientRect(),x=clientX-rect.left,y=clientY-rect.top;
      let best=null,distance=18;
      for(const event of this.visibleEvents().sort((a,b)=>(b.priority_score||0)-(a.priority_score||0))) {
        const p=this.project((event.box[0]+event.box[2])/2,(event.box[1]+event.box[3])/2,position(event));
        const d=Math.hypot(p[0]-x,p[1]-y);if(d<distance){best=event;distance=d;}
      }
      if(best)this.onPick?.(best);
    }
    add(id,image,shape=false) {
      const gl=this.gl,texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
      const format=shape?gl.RGBA:gl.RGB,textures=shape?this.shapes:this.textures;
      gl.texImage2D(gl.TEXTURE_2D,0,format,format,gl.UNSIGNED_BYTE,image);
      if(textures.has(id))gl.deleteTexture(textures.get(id));textures.set(id,texture);this.draw();
      while(textures.size>160){const first=textures.keys().next().value;gl.deleteTexture(textures.get(first));textures.delete(first);}
    }
    draw() {if(this.queued)return;this.queued=true;requestAnimationFrame(()=>{this.queued=false;this.render();});}
    render() {
      const gl=this.gl,canvas=this.canvas,rect=canvas.getBoundingClientRect();
      if(rect.width<1||rect.height<1)return;
      const ratio=Math.min(devicePixelRatio||1,1.5),w=Math.round(rect.width*ratio),h=Math.round(rect.height*ratio);
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
      gl.viewport(0,0,w,h);gl.clearColor(.035,.043,.055,1);gl.clear(gl.COLOR_BUFFER_BIT);
      if(!this.metadata)return;
      const m=this.metadata,max=Math.max(m.width,m.height),frames=m.frames;
      gl.useProgram(this.program);gl.uniform2f(this.uniform.plane,2*m.width/max,2*m.height/max);
      gl.uniform2f(this.uniform.angle,this.yaw,this.pitch);gl.uniform1f(this.uniform.zoom,this.zoom);gl.uniform1f(this.uniform.aspect,w/h);
      const first=position(frames[0]),range=position(frames[frames.length-1])-first;
      const setHeight=frame=>gl.uniform1f(this.uniform.height,range?(position(frame)-first)/range*1.4-.7:0);
      const bind=buffer=>{gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.vertexAttribPointer(this.attribute,2,gl.FLOAT,false,0,0);};
      bind(this.triangles);gl.uniform1i(this.uniform.border,0);gl.uniform1i(this.uniform.silhouette,0);
      // La caméra reste au-dessus des plans : leur ordre Z croissant est l'ordre de transparence.
      for(let i=0;i<=this.cut;i++) {
        if(this.shapeMode==='shape')break;
        if(i!==this.cut&&i%this.step!==0)continue;
        const frame=frames[i],texture=this.textures.get(frame.id);if(!texture)continue;
        setHeight(frame);gl.bindTexture(gl.TEXTURE_2D,texture);gl.uniform1f(this.uniform.opacity,this.shapeMode==='overlay'?Math.min(this.opacity,.08):i===this.cut?1:this.opacity);
        gl.drawArrays(gl.TRIANGLES,0,6);
      }
      if(this.shapeMode==='shape'||this.shapeMode==='overlay'){
        gl.uniform1i(this.uniform.silhouette,1);
        for(let i=0;i<=this.cut;i++){
          if(i!==this.cut&&i%this.step!==0)continue;
          const frame=frames[i],texture=this.shapes.get(frame.id);if(!texture)continue;
          setHeight(frame);gl.bindTexture(gl.TEXTURE_2D,texture);gl.uniform1f(this.uniform.opacity,i===this.cut?1:Math.max(.3,this.opacity*3));gl.drawArrays(gl.TRIANGLES,0,6);
        }
        gl.uniform1i(this.uniform.silhouette,0);
      }
      const current=frames[this.cut];
      if(current&&(this.textures.has(current.id)||this.shapes?.has(current.id))){setHeight(current);bind(this.outline);gl.uniform1i(this.uniform.border,1);gl.uniform4f(this.uniform.tint,.23,.78,.94,1);gl.drawArrays(gl.LINE_LOOP,0,4);}
      // Les repères sont dessinés après les photographies pour rester visibles à travers les plans.
      // Ils occupent uniquement le plan au pic : le cadre n'est pas extrapolé sur toute la durée.
      gl.uniform1i(this.uniform.border,1);bind(this.markBuffer);
      const upload=values=>gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.DYNAMIC_DRAW);
      const groups=new Map();
      for(const event of this.visibleEvents()) {
        const b=event.box,c=m.crop,u0=(b[0]-c[0])/m.width,v0=(b[1]-c[1])/m.height,u1=(b[2]-c[0])/m.width,v1=(b[3]-c[1])/m.height;
        const band=this.scoreColors?scoreBand(event.priority_score):-1,key=event.layer+':'+band;
        if(!groups.has(key))groups.set(key,{frame:event,band,fill:[],lines:[],points:[]});
        const group=groups.get(key);
        group.fill.push(u0,v0,u1,v0,u0,v1,u0,v1,u1,v0,u1,v1);
        group.lines.push(u0,v0,u1,v0,u1,v0,u1,v1,u1,v1,u0,v1,u0,v1,u0,v0);
        group.points.push((u0+u1)/2,(v0+v1)/2);
      }
      // Trois appels par couche et tranche de score, quel que soit le nombre d'indications.
      for(const group of [...groups.values()].sort((a,b)=>a.band-b.band)){
        const color=group.band<0?[1,.2,.23]:scorePalette[group.band].map(v=>v/255);
        setHeight(group.frame);upload(group.fill);gl.uniform4f(this.uniform.tint,...color,.28);gl.drawArrays(gl.TRIANGLES,0,group.fill.length/2);
        upload(group.lines);gl.uniform4f(this.uniform.tint,...color,1);gl.drawArrays(gl.LINES,0,group.lines.length/2);
        upload(group.points);gl.drawArrays(gl.POINTS,0,group.points.length/2);
      }
    }
  }

  window.createStackViewer = function({getState,api,reportError,openIndication}) {
    const el=id=>document.getElementById(id);
    let renderer=null,metadata=null,active=false,loadedKey='',generation=0,abort=null,lastRun='',lastRevision=-1,cutAbort=null,cutKey='';
    let shapeKey='',shapeSerial=0,shapeAbort=null,cutShapeBusy=false;
    const shapeRecords=new Map(),shapeRequests=new Map();
    const imageURL=id=>'/api/stack-image?'+new URLSearchParams({run:getState().run,id,region:el('stack-region').value});
    function clearShapes(){
      shapeSerial++;shapeAbort?.abort();shapeKey='';shapeRequests.clear();
      for(const record of shapeRecords.values())URL.revokeObjectURL(record.url);
      shapeRecords.clear();renderer?.clearShapes();
      el('stack-photo').querySelector('.shape-mask')?.remove();el('shape-cut-status').hidden=true;el('shape-progress').hidden=true;
    }
    async function ensureShape(frame){
      if(shapeRecords.has(frame.id)&&renderer.shapes.has(frame.id))return shapeRecords.get(frame.id);
      if(shapeRequests.has(frame.id))return shapeRequests.get(frame.id);
      const serial=shapeSerial,signal=shapeAbort.signal,run=getState().run;
      const request=(async()=>{
        const params={run,id:frame.id,region:el('stack-region').value,contrast:el('shape-contrast').value};
        const response=await fetch('/api/shape-image?'+new URLSearchParams(params),{signal});
        if(!response.ok)throw Error('Photographic section unavailable.');
        const blob=await response.blob(),bitmap=await createImageBitmap(blob);
        if(serial!==shapeSerial||signal.aborted){bitmap.close();return null;}
        const coverage=Number(response.headers.get('X-Shape-Coverage'));
        const record={url:URL.createObjectURL(blob),coverage};
        if(shapeRecords.has(frame.id))URL.revokeObjectURL(shapeRecords.get(frame.id).url);
        shapeRecords.set(frame.id,record);renderer.add(frame.id,bitmap,true);bitmap.close();
        while(shapeRecords.size>160){const first=shapeRecords.keys().next().value;URL.revokeObjectURL(shapeRecords.get(first).url);shapeRecords.delete(first);}
        return record;
      })();
      shapeRequests.set(frame.id,request);
      try{return await request;}finally{if(serial===shapeSerial)shapeRequests.delete(frame.id);}
    }
    function updateShapeCut(){
      const enabled=metadata?.shape_available&&el('stack-render').value!=='photos'&&shapeKey;
      el('shape-cut-status').hidden=!enabled;
      if(!enabled){el('stack-photo').querySelector('.shape-mask')?.remove();return;}
      const frame=metadata.frames[Number(el('stack-layer').value)],serial=shapeSerial;
      el('stack-photo').querySelector('.shape-mask')?.remove();el('shape-cut-status').textContent='Extracting the current cross-section…';
      if(cutShapeBusy)return;cutShapeBusy=true;
      ensureShape(frame).then(record=>{
        if(!record||serial!==shapeSerial||metadata?.frames[Number(el('stack-layer').value)]?.id!==frame.id)return;
        let img=el('stack-photo').querySelector('.shape-mask');if(!img){img=document.createElement('img');img.className='shape-mask';img.alt='Extracted cyan section overlaid on the photograph';el('stack-photo').append(img);}img.src=record.url;
        const warning=record.coverage===0?'No section extracted. Try a lower minimum contrast.':record.coverage>65?'Very extensive extraction: check the background and increase minimum contrast.':'Cyan: extracted section. Check that it matches the photograph.';
        el('shape-cut-status').textContent=record.coverage.toFixed(1)+' % de la coupe · '+warning;
      }).catch(error=>{if(serial===shapeSerial){el('shape-cut-status').textContent=error.message;reportError(error);}}).finally(()=>{cutShapeBusy=false;if(serial!==shapeSerial||metadata?.frames[Number(el('stack-layer').value)]?.id!==frame.id)updateShapeCut();});
    }
    async function loadShapes(){
      const available=Boolean(metadata?.shape_available);
      for(const option of el('stack-render').options)if(option.value!=='photos')option.disabled=!available;
      if(!available)el('stack-render').value='photos';
      const mode=el('stack-render').value,enabled=available&&mode!=='photos';
      if(renderer){renderer.shapeMode=mode;renderer.draw();}
      el('shape-contrast-field').hidden=!enabled;
      el('shape-help').textContent=available?'Extracted shape: cyan photographic sections stacked at their layer heights. Local-contrast extraction is approximate; shadows, reflections, cavities and low-contrast areas can distort the outline. Check the overlay on the cross-section photograph.':metadata?.axis==='acquisition'?'Shape reconstruction requires an identified post-melting stage. These acquisitions have no melting / spreading labels; the photographic stack and scores remain available.':'Select After melting to extract visible part sections.';
      if(!enabled){if(shapeKey)clearShapes();updateShapeCut();return;}
      const key=getState().run+'/'+metadata.phase+'/'+metadata.camera+'/'+el('stack-region').value+'/'+el('shape-contrast').value;
      if(shapeKey===key){updateShapeCut();return;}
      clearShapes();shapeKey=key;shapeAbort=new AbortController();const serial=shapeSerial,signal=shapeAbort.signal,data=metadata;
      const stride=Math.max(1,Math.ceil(data.frames.length/128));const sample=data.frames.filter((f,i)=>i%stride===0||i===data.frames.length-1);
      const queue=[...sample].reverse(),start=performance.now();let done=0,failed=0;
      el('shape-progress').hidden=false;
      const progress=()=>{
        if(serial!==shapeSerial)return;
        const complete=done+failed,seconds=complete?Math.ceil((performance.now()-start)/1000/complete*(sample.length-complete)):null;
        el('shape-progress').textContent='Cyan shape: '+done+' / '+sample.length+' sections'+(failed?' · '+failed+' unavailable':'')+(complete===sample.length?' · extraction complete.':' · '+(seconds===null?'processing…':'estimated remaining '+seconds+' s'))+' · preview ≤ '+(data.shape_texture_max_px||512)+' px, approximate geometry.';
      };
      progress();updateShapeCut();
      async function worker(){while(queue.length&&!signal.aborted){const frame=queue.shift();try{await ensureShape(frame);if(serial!==shapeSerial)return;done++;}catch(error){if(signal.aborted||serial!==shapeSerial)return;failed++;}progress();}}
      await Promise.all([worker(),worker()]);
    }
    function setView(show) {
      active=show;el('review-space').hidden=show;el('stack-space').hidden=!show;
      el('show-review').setAttribute('aria-pressed',String(!show));el('show-stack').setAttribute('aria-pressed',String(show));
      if(show){renderer?.draw();load().catch(reportError);}
    }
    function updateCut() {
      if(!metadata||!renderer)return;
      const index=Number(el('stack-layer').value),frame=metadata.frames[index];
      renderer.cut=index;renderer.step=Number(el('stack-step').value);renderer.opacity=Number(el('stack-opacity').value)/100;renderer.draw();
      renderer.showEvents=el('stack-markers').checked;renderer.eventFilter=el('stack-event-filter').value;
      renderer.scoreColors=el('stack-score-colors').checked;el('stack-score-legend').hidden=!renderer.scoreColors;
      el('stack-events-count').textContent=renderer.visibleEvents().length+' visible indication(s) · minimum persistence: '+(metadata.min_consecutive||1)+(renderer.scoreColors?' · yellow → red: increasing priority score.':' · red markers.')+' Markers are placed at the peak and visible through the planes. Click a point to open its review and score.';
      const acquisition=metadata.axis==='acquisition';
      el('stack-layer-label').textContent=acquisition?'Acquisition '+frame.layer+' · capture order':'Layer '+frame.layer+' · Z = '+frame.z_mm.toFixed(3)+' mm';
      const photo=el('stack-photo');photo.style.aspectRatio=metadata.width+'/'+metadata.height;
      let img=photo.querySelector('img');if(!img){img=document.createElement('img');photo.replaceChildren(img);}
      img.alt=(acquisition?'Acquisition ':'Layer ')+frame.layer+' · '+phaseLabel[metadata.phase];
      const url=imageURL(frame.id);if(img.getAttribute('src')!==url)img.src=url;
      updateShapeCut();
      el('stack-original').href='/api/image?'+new URLSearchParams({run:getState().run,id:frame.id});el('stack-original').hidden=false;
      // La coupe courante reste disponible même entre les plans d’aperçu espacés.
      const key=getState().run+'/'+frame.id+'/'+el('stack-region').value;
      if(!renderer.textures.has(frame.id)&&cutKey!==key){
        cutKey=key;cutAbort?.abort();cutAbort=new AbortController();const signal=cutAbort.signal,current=metadata;
        (async()=>{try{const response=await fetch(url,{signal});if(!response.ok)throw Error('Cross-section unavailable.');const bitmap=await createImageBitmap(await response.blob());if(metadata===current&&!signal.aborted)renderer.add(frame.id,bitmap);bitmap.close();}catch(e){if(!signal.aborted)reportError(e);}})();
      }
    }
    async function load() {
      const state=getState();if(!active||!state)return;
      if(state.running){el('stack-status').textContent='Analysis is preparing the layers. The 3D view will be available when it finishes.';return;}
      if(!state.summary?.images_mesurees&&!state.analysis?.measured){el('stack-status').textContent='Run an analysis first to prepare the layers.';return;}
      const phases=state.display_phases||state.config.analysis_phases;
      const previous=el('stack-phase').value;el('stack-phase').replaceChildren(...phases.map(phase=>{const o=document.createElement('option');o.value=phase;o.textContent=phaseLabel[phase];return o;}));el('stack-phase').value=phases.includes(previous)?previous:phases[0];
      if(!phases.includes(el('stack-phase').value))el('stack-phase').value=phases[0];
      const phase=el('stack-phase').value,region=el('stack-region').value,camera=el('stack-camera').value,key=state.run+'/'+phase+'/'+region+'/'+camera;
      if(key===loadedKey)return;
      loadedKey=key;const serial=++generation;abort?.abort();abort=new AbortController();const signal=abort.signal;
      clearShapes();metadata=null;renderer?.clear();el('stack-photo').replaceChildren();el('stack-original').hidden=true;
      el('stack-status').textContent='Preparing photographic planes…';
      try {
        if(!renderer){renderer=new PhotoStack(el('stack-canvas'));renderer.onPick=e=>{setView(false);openIndication?.(e.id);};}
        const parameters={run:state.run,phase,region};if(camera)parameters.camera=camera;
        const data=await api('/api/stack?'+new URLSearchParams(parameters));
        if(serial!==generation)return;
        metadata=data;renderer.metadata=data;
        el('stack-camera').replaceChildren(...data.cameras.map(name=>{const o=document.createElement('option');o.value=name;o.textContent=name;return o;}));el('stack-camera').value=data.camera;
        loadedKey=state.run+'/'+phase+'/'+region+'/'+data.camera;
        el('stack-layer').max=data.frames.length-1;el('stack-layer').value=data.frames.length-1;
        el('stack-count').textContent=data.frames.length+(data.axis==='acquisition'?' acquisitions':' layers')+' · '+phaseLabel[phase];
        el('stack-height').textContent=data.axis==='acquisition'?'Stack in acquisition order: '+data.frames[0].layer+' to '+data.frames[data.frames.length-1].layer+'. Physical height is not assigned.':'Heights: '+data.frames[0].z_mm.toFixed(3)+' to '+data.frames[data.frames.length-1].z_mm.toFixed(3)+' mm · nominal step '+data.layer_um+' µm.';
        el('stack-geometry-note').textContent=data.axis==='acquisition'?'The vertical axis represents acquisition order, not millimeters. Indications are placed on their acquisition.':'Photos are placed at their layer heights. X and Y remain in pixels; 3D proportions are adjusted for readability.';
        el('stack-axis-hint').textContent=data.axis==='acquisition'?'Drag: rotate · scroll: zoom · vertical axis: acquisitions':'Drag: rotate · scroll: zoom · Z exaggerated for clarity';
        const stride=Math.max(1,Math.ceil(data.frames.length/128)),sample=data.frames.filter((f,i)=>i%stride===0||i===data.frames.length-1);
        el('stack-resolution').textContent=sample.length+' preview planes distributed through the volume, limited to '+data.texture_max_px+' pixels. Move the cut to load any image; all indications remain represented.';
        updateCut();
        loadShapes().catch(reportError);
        const queue=[...sample].reverse();let done=0,failed=0;
        const progress=()=>{el('stack-status').textContent=done+' / '+sample.length+' previews loaded'+(failed?' · '+failed+' unavailable':'')+(done+failed===sample.length?' · move the cut to explore.':' · you can already rotate the view.')+(data.excluded_dimensions?' · '+data.excluded_dimensions+' excluded: different dimensions.':'');};
        // Trois décodages au maximum : mémoire et accès disque bornés sur un PC standard.
        async function worker() {
          while(queue.length&&!signal.aborted) {
            const frame=queue.shift();
            try {
              const response=await fetch('/api/stack-image?'+new URLSearchParams({run:state.run,id:frame.id,region}),{signal});
              if(!response.ok)throw Error('Image indisponible');
              const bitmap=await createImageBitmap(await response.blob());
              if(serial!==generation){bitmap.close();return;}
              renderer.add(frame.id,bitmap);bitmap.close();done++;
            }catch(error){if(signal.aborted||serial!==generation)return;failed++;}
            if(serial===generation)progress();
          }
        }
        await Promise.all([worker(),worker(),worker()]);
      }catch(error){if(serial!==generation)return;el('stack-status').textContent=error.message;reportError(error);}
    }
    el('show-review').onclick=()=>setView(false);el('show-stack').onclick=()=>setView(true);
    el('stack-phase').onchange=()=>{el('stack-camera').replaceChildren();load().catch(reportError);};
    el('stack-region').onchange=el('stack-camera').onchange=()=>load().catch(reportError);
    el('stack-layer').oninput=el('stack-step').onchange=el('stack-opacity').oninput=updateCut;
    el('stack-markers').onchange=el('stack-event-filter').onchange=updateCut;
    el('stack-score-colors').onchange=updateCut;
    el('stack-render').onchange=()=>loadShapes().catch(reportError);
    el('shape-contrast').oninput=()=>{el('shape-contrast-label').textContent=el('shape-contrast').value;};
    el('shape-contrast').onchange=()=>loadShapes().catch(reportError);
    el('stack-oblique').onclick=()=>{if(renderer){renderer.yaw=-.35;renderer.pitch=.55;renderer.zoom=.68;renderer.draw();}};
    el('stack-top').onclick=()=>{if(renderer){renderer.yaw=0;renderer.pitch=Math.PI/2;renderer.zoom=.9;renderer.draw();}};
    return {setState(state){
      if(state.run!==lastRun)el('stack-camera').replaceChildren();
      if(state.run!==lastRun||state.revision!==lastRevision||(state.running&&loadedKey)){
        generation++;abort?.abort();cutAbort?.abort();cutKey='';clearShapes();renderer?.clear();metadata=null;loadedKey='';el('stack-photo').replaceChildren();el('stack-original').hidden=true;el('stack-count').textContent='';el('stack-layer-label').textContent='—';
      }
      lastRun=state.run;lastRevision=state.revision;
      el('show-stack').disabled=state.running;
      el('stack-region').querySelector('[value="parts"]').disabled=!state.dataset.has_roi;
      if(!state.dataset.has_roi)el('stack-region').value='full';
      if(active)load().catch(reportError);
    }};
  };
  if(typeof module!=='undefined')module.exports={PhotoStack};
})();
