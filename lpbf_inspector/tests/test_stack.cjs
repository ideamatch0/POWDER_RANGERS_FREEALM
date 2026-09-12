const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const scope={window:{},module:{exports:{}},devicePixelRatio:1,Float32Array,Math};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/stack.js'),'utf8'),scope);
const {PhotoStack}=scope.module.exports;
const renderer=Object.create(PhotoStack.prototype);
const frame={id:1,layer:10,z_mm:.6};
renderer.metadata={width:200,height:100,crop:[100,200,300,300],frames:[frame,{id:2,layer:11,z_mm:.66}],events:[
  {id:40,box:[180,230,220,270],layer:10,z_mm:.6,status:'a_examiner'},
  {id:41,box:[180,230,220,270],layer:11,z_mm:.66,status:'retenue'},
  {id:42,box:[180,230,220,270],layer:10,z_mm:.6,status:'ecartee'}]};
renderer.canvas={width:800,height:400,getBoundingClientRect:()=>({left:10,top:20,width:800,height:400})};
renderer.cut=0;renderer.step=1;renderer.opacity=.12;renderer.showEvents=true;renderer.eventFilter='active';
renderer.yaw=0;renderer.pitch=Math.PI/2;renderer.zoom=1;
assert.equal(renderer.visibleEvents().length,1,'Les indications au-dessus de la coupe et les ecartées doivent être exclues.');
const point=renderer.project(200,250,.6);
assert.ok(Math.abs(point[0]-400)<1e-6&&Math.abs(point[1]-200)<1e-6,'La projection doit tenir compte du décalage du cadrage.');
let selected=null;renderer.onPick=e=>selected=e.id;renderer.pick(410,220);assert.equal(selected,40,'Le clic doit retrouver la bonne indication.');
renderer.eventFilter='retained';assert.equal(renderer.visibleEvents().length,0);
renderer.cut=1;assert.equal(renderer.visibleEvents()[0].id,41);
renderer.eventFilter='layer';assert.equal(renderer.visibleEvents().length,1);
renderer.showEvents=false;assert.equal(renderer.visibleEvents().length,0);
renderer.showEvents=true;renderer.cut=0;renderer.eventFilter='active';
// Vérifie que la passe rouge survient après les images opaques et conserve une opacité visible.
const draws=[];let tint=null,border=false;
renderer.gl={ARRAY_BUFFER:1,STATIC_DRAW:2,DYNAMIC_DRAW:3,FLOAT:4,TEXTURE_2D:5,TRIANGLES:6,LINE_LOOP:7,POINTS:8,COLOR_BUFFER_BIT:9,LINES:10,
  viewport(){},clearColor(){},clear(){},useProgram(){},uniform2f(){},uniform1f(){},bindBuffer(){},vertexAttribPointer(){},bindTexture(){},bufferData(){},
  uniform1i(name,value){if(name==='border')border=Boolean(value);},uniform4f(name,...value){tint=value;},
  drawArrays(mode,first,count){draws.push({mode,count,border,tint});}};
renderer.uniform=Object.fromEntries(['plane','angle','zoom','aspect','height','opacity','border','tint'].map(k=>[k,k]));
renderer.textures=new Map([[1,{}]]);renderer.render();
const photo=draws.findIndex(d=>!d.border&&d.mode===6),red=draws.findIndex(d=>d.border&&d.tint?.[0]===1&&d.mode===6);
assert.ok(photo>=0&&red>photo,'Les cadres rouges doivent rester visibles à travers les photographies.');
assert.ok(draws[red].tint[3]>.2);assert.ok(draws.some(d=>d.mode===8),'Un repère ponctuel rend les petites indications visibles.');
console.log('3D : filtres, coupe, projection, sélection et passe rouge vérifiés.');
renderer.metadata={...renderer.metadata,axis:'acquisition',frames:renderer.metadata.frames.map(f=>({...f,position:f.layer,z_mm:null})),events:renderer.metadata.events.map(e=>({...e,id:'image:'+e.id,position:e.layer,z_mm:null}))};
renderer.pick(410,220);assert.equal(selected,'image:40','Les acquisitions sans hauteur doivent rester sélectionnables.');
draws.length=0;renderer.render();assert.ok(draws.some(d=>d.border&&d.tint?.[0]===1&&d.mode===6),'Les acquisitions Aalto ont la même passe rouge.');
console.log('Aalto : axe par acquisition et indications rouges sélectionnables vérifiés.');

// La forme cyan utilise l'alpha du masque ; les repères restent dessinés ensuite.
renderer.shapeMode='shape';renderer.shapes=new Map([[1,{}]]);renderer.scoreColors=true;
renderer.metadata.events=[
 {id:'high',box:[180,230,220,270],layer:10,position:10,status:'a_examiner',priority_score:85},
 {id:'low',box:[180,230,220,270],layer:10,position:10,status:'a_examiner',priority_score:15}];
renderer.uniform.silhouette='silhouette';let silhouette=false;
renderer.gl.uniform1i=(name,value)=>{if(name==='border')border=Boolean(value);if(name==='silhouette')silhouette=Boolean(value);};
renderer.gl.drawArrays=(mode,first,count)=>draws.push({mode,count,border,tint,silhouette});
draws.length=0;renderer.render();
const cyan=draws.findIndex(d=>d.silhouette&&!d.border);
assert.ok(cyan>=0);assert.ok(!draws.some(d=>!d.border&&!d.silhouette),'Le mode forme doit retirer les fonds photographiques opaques.');
const marks=draws.filter(d=>d.border&&d.mode===6);
assert.equal(marks.length,2);assert.ok(marks[0].tint[1]>marks[1].tint[1],'Le score faible est jaune et le score élevé rouge.');
assert.ok(draws.indexOf(marks[0])>cyan,'Les indications restent visibles après le masque de pièce.');
renderer.pick(410,220);assert.equal(selected,'high','Si les centres coïncident, ouvrir en priorité le score élevé.');
renderer.scoreColors=false;draws.length=0;renderer.render();assert.equal(draws.filter(d=>d.border&&d.mode===6).length,1);
// Bornes GPU indépendantes des photos et des sections, et libération complète.
renderer.textures=new Map();renderer.shapes=new Map();renderer.draw=()=>{};let deleted=0;
Object.assign(renderer.gl,{RGB:11,RGBA:12,UNSIGNED_BYTE:13,createTexture:()=>({}),deleteTexture:()=>deleted++,texParameteri(){},texImage2D(...args){this.lastFormat=args[2];}});
for(let i=0;i<170;i++)renderer.add(i,{},true);
assert.equal(renderer.shapes.size,160);assert.equal(renderer.textures.size,0);assert.equal(renderer.gl.lastFormat,12);
renderer.add(1,{});assert.equal(renderer.gl.lastFormat,11);renderer.clear();assert.equal(renderer.shapes.size,0);assert.equal(renderer.textures.size,0);assert.equal(deleted,171);
console.log('3D : masque alpha cyan, palette de priorité, ordre de dessin, sélection et limites GPU vérifiés.');
