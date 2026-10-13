const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/buildplate.js','utf8');
const copy=value=>JSON.parse(JSON.stringify(value));
const storage=new Map();
class Element{
 constructor(){this.attributes={};this.children=[];this.value='';this.open=false;this.handlers={};this.style={};}
 setAttribute(k,v){this.attributes[k]=v;}
 getAttribute(k){return this.attributes[k];}
 hasAttribute(k){return k in this.attributes;}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;if(items[0]?.value)this.value=items[0].value;}
 querySelector(){return this.option||(this.option=new Element());}
 querySelectorAll(){return [];}
 addEventListener(k,fn){this.handlers[k]=fn;}
 getScreenCTM(){return {inverse:()=>({})};}
 setPointerCapture(){}
 showModal(){this.open=true;}
 close(){this.open=false;}
}
function harness(server={library:'job1',run:'initial',profile:'profile1',cameras:['cam1'],outlines:{}}){
 const elements={},el=id=>elements[id]||(elements[id]=new Element());let state={dataset:{id:server.library},run:server.run,buildplate:{cameras:server.cameras,outlines:copy(server.outlines)},config:{plate_by_camera:copy(server.outlines)}};
 const sandbox={window:{},document:{getElementById:el,createElement:()=>new Element(),createElementNS:()=>new Element()},URLSearchParams,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},DOMPoint:class{constructor(x,y){this.x=x;this.y=y;}matrixTransform(){return this;}}};
 vm.createContext(sandbox);vm.runInContext(source,sandbox);sandbox.PlateGeometry=sandbox.window.PlateGeometry;
 let posts=0,fail=false,errors=[];
 const ui=sandbox.window.createBuildPlateUI({getState:()=>state,refresh:async()=>{},reportError:e=>errors.push(e),api:async(path,body)=>{
  if(!body)return {...copy(server),width:100,height:100,name:'camera.jpg'};
  posts++;assert.equal(body.run,server.run);
  if(fail)throw Error('Disk unavailable');
  server.outlines=copy(body.outlines);server.run='saved-'+posts;
  return {dataset:{id:server.library},run:server.run,buildplate:{outlines:copy(server.outlines),cameras:server.cameras},config:{plate_by_camera:copy(server.outlines)}};
 }});
 ui.setState(state);
 return {el,server,ui,get posts(){return posts;},get errors(){return errors;},set fail(v){fail=v;},
  open:()=>el('define-buildplate').onclick(),close:()=>el('plate-close').onclick(),
  point(x,y){el('plate-canvas').onpointerdown({clientX:x,clientY:y,pointerId:1,target:new Element(),preventDefault(){}});},
  shape(){return el('plate-canvas').children.find(n=>n.attributes.points)?.attributes.points;},
  update(){state={...state,run:server.run,buildplate:{outlines:copy(server.outlines),cameras:server.cameras}};}
 };
}
(async()=>{
 storage.clear();const a=harness();await a.open();a.point(10,10);a.point(90,10);a.point(90,90);const traced=a.shape();
 await a.close();assert.equal(a.posts,1);assert.equal(a.el('plate-dialog').open,false);assert.equal(storage.size,0);
 // The app's poll is deliberately stale: reopening must use authoritative server metadata.
 await a.open();assert.equal(a.shape(),traced);await a.close();assert.equal(a.posts,1);
 await a.open();a.el('plate-clear').onclick();a.point(15,15);await a.close();assert.equal(a.posts,1);assert.match(a.el('buildplate-status').textContent,/Incomplete draft retained/);
 const b=harness(a.server);await b.open();assert.equal(b.shape(),'15,15');b.point(80,15);b.point(80,80);
 let prevented=false;b.el('plate-dialog').handlers.cancel({preventDefault(){prevented=true;}});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(prevented,true);assert.equal(b.posts,1);assert.equal(b.el('plate-dialog').open,false);
 await b.open();b.point(15,80);b.fail=true;await b.close();assert.equal(b.errors.length,1);assert.equal(storage.size,1);
 const c=harness(b.server);await c.open();assert.equal(c.shape(),'15,15 80,15 80,80 15,80');await c.close();assert.equal(c.posts,1);assert.equal(storage.size,0);
 // Unsaved drafts cannot cross jobs or profiles, even if camera names match.
 await c.open();c.el('plate-clear').onclick();c.point(20,20);await c.close();
 const other=harness({...copy(c.server),profile:'other',outlines:{}});await other.open();assert.equal(other.shape(),undefined);await other.close();
 const job=harness({...copy(c.server),library:'job2',outlines:{}});await job.open();assert.equal(job.shape(),undefined);await job.close();
 // A newer saved contour wins over an older draft until explicitly restored.
 c.server.outlines={cam1:[[.3,.3],[.7,.3],[.7,.7]]};const d=harness(c.server);await d.open();assert.equal(d.shape(),'30,30 70,30 70,70');assert.equal(d.el('plate-restore-draft').hidden,false);
 d.el('plate-restore-draft').onclick();assert.equal(d.shape(),'20,20');await d.close();assert.equal(d.posts,0);
 console.log('Build plate UI: close/Escape autosave, authoritative reopen, reload drafts, save failure, job/profile isolation and conflict recovery passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
