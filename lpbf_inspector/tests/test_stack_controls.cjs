// Intégration du contrôleur asynchrone avec DOM, réseau et GPU simulés.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
class Node {
 constructor(tag='div'){this.tag=tag;this.children=[];this.style={};this.value='';this.checked=false;this.hidden=false;this.attrs={};}
 append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n);}}
 replaceChildren(...nodes){this.children=[];this.append(...nodes);if(this.tag==='select')this.value=nodes[0]?.value||'';}
 get options(){return this.children;}
 querySelector(selector){return this.children.find(n=>selector==='img'?n.tag==='img':selector==='.shape-mask'?n.className==='shape-mask':selector==='[value="parts"]'?n.value==='parts':false)||null;}
 setAttribute(k,v){this.attrs[k]=v;}
 getAttribute(k){return this[k]??this.attrs[k]??null;}
 remove(){this.parent.children=this.parent.children.filter(n=>n!==this);}
}
let instance;
class FakeRenderer {
 constructor(){instance=this;this.textures=new Map();this.shapes=new Map();this.metadata=null;}
 draw(){}clear(){this.textures.clear();this.clearShapes();this.metadata=null;}clearShapes(){this.shapes.clear();}
 add(id,bitmap,shape=false){(shape?this.shapes:this.textures).set(id,bitmap);}
 visibleEvents(){return [];}
}
const nodes={};const el=id=>nodes[id]||(nodes[id]=new Node());
for(const [id,values,selected] of [
 ['stack-phase',['fusion','etalement'],'fusion'],['stack-camera',[], ''],['stack-region',['full','parts'],'full'],
 ['stack-render',['photos','shape','overlay'],'photos'],['stack-event-filter',['active'],'active'],['stack-step',['1'],'1']]){
 nodes[id]=new Node('select');el(id).replaceChildren(...values.map(value=>Object.assign(new Node('option'),{value})));el(id).value=selected;
}
el('stack-layer').value=0;el('stack-opacity').value='12';el('shape-contrast').value='3';el('stack-score-colors').checked=true;el('stack-markers').checked=true;
const requests=[],errors=[],revoked=[];let sequence=0,pending=null;
let state={run:'job-a',revision:0,running:false,summary:{images_mesurees:3},config:{analysis_phases:['fusion','etalement']},dataset:{has_roi:true}};
const metadata=phase=>({phase,shape_available:phase==='fusion',shape_texture_max_px:512,texture_max_px:384,camera:'cam1',cameras:['cam1'],width:100,height:100,crop:[0,0,100,100],layer_um:60,frames:[1,2,3].map(id=>({id,layer:id,z_mm:id*.06})),events:[]});
const scope={window:{},document:{getElementById:el,createElement:tag=>new Node(tag)},FakeRenderer,URLSearchParams,AbortController,performance,
 URL:{createObjectURL:()=>`blob:${++sequence}`,revokeObjectURL:url=>revoked.push(url)},
 fetch:async(url,{signal}={})=>{requests.push(url);if(pending&&url.includes('shape-image'))await new Promise(resolve=>pending.push(resolve));return {ok:true,headers:{get:()=> '22.5'},blob:async()=>({url,aborted:signal?.aborted})};},
 createImageBitmap:async blob=>({...blob,close(){}})};
vm.createContext(scope);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/stack.js'),'utf8').replace("new PhotoStack(el('stack-canvas'))","new FakeRenderer()"),scope);
const viewer=scope.window.createStackViewer({getState:()=>state,api:async url=>metadata(new URL('http://localhost'+url).searchParams.get('phase')),reportError:e=>errors.push(e)});
const flush=async()=>{for(let i=0;i<30;i++)await new Promise(resolve=>setImmediate(resolve));};
(async()=>{
 viewer.setState(state);el('show-stack').onclick();await flush();assert.equal(instance.textures.size,3);assert.equal(instance.shapes.size,0);
 const photos=requests.filter(u=>u.includes('stack-image')).length;
 el('stack-render').value='shape';await el('stack-render').onchange();await flush();
 assert.equal(instance.shapeMode,'shape');assert.equal(instance.shapes.size,3);assert.ok(el('stack-photo').querySelector('.shape-mask'));
 assert.match(el('shape-cut-status').textContent,/22.5/);assert.match(el('shape-progress').textContent,/3 \/ 3/);
 el('shape-contrast').value='2';await el('shape-contrast').onchange();await flush();
 assert.equal(requests.filter(u=>u.includes('stack-image')).length,photos,'Changer le contraste ne recalcule pas les photographies.');
 assert.ok(requests.some(u=>u.includes('contrast=2')));assert.ok(revoked.length>=3);
 el('stack-layer').value=0;el('stack-layer').oninput();await flush();assert.match(el('stack-layer-label').textContent,/Layer 1/);
 el('stack-score-colors').checked=false;el('stack-score-colors').onchange();await flush();assert.equal(instance.scoreColors,false);assert.equal(el('stack-score-legend').hidden,true);
 // Une réponse de masque tardive ne doit pas contaminer une autre étape.
 pending=[];el('shape-contrast').value='4';el('shape-contrast').onchange();await flush();assert.ok(pending.length>0);
 el('stack-phase').value='etalement';el('stack-phase').onchange();await flush();
 assert.equal(el('stack-render').value,'photos');assert.equal(el('stack-render').options[1].disabled,true);
 for(const finish of pending)finish();pending=null;await flush();assert.equal(instance.shapes.size,0);assert.equal(el('stack-photo').querySelector('.shape-mask'),null);
 assert.equal(errors.length,0,String(errors));
 state={...state,run:'aalto',revision:1,display_phases:['acquisition']};viewer.setState(state);await flush();
 assert.equal(el('stack-render').options[1].disabled,true);
 const count=requests.filter(u=>u.includes('shape-image')).length;el('stack-render').value='shape';await el('stack-render').onchange();await flush();
 assert.equal(el('stack-render').value,'photos');assert.equal(requests.filter(u=>u.includes('shape-image')).length,count);
 console.log('Contrôleur 3D : modes, contraste, masque de coupe, couleurs, réponses tardives et étapes inconnues vérifiés.');
})().catch(error=>{console.error(error);process.exitCode=1});
