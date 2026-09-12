const assert=require('node:assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.style={};this.attributes={};this.dataset={};this.value='';this.checked=false;this.classList={toggle(){}};}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=[...children];}
  setAttribute(k,v){this.attributes[k]=v;}
  querySelectorAll(){return this.children.filter(c=>c.tag==='button');}
}
const nodes=new Map();
global.document={getElementById(id){if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);},createElement(tag){return new Element(tag);},createElementNS(_,tag){return new Element(tag);}};
global.window={};
require('../web/gallery.js');
const get=id=>document.getElementById(id);
get('gallery-overlay').checked=true;
let state={run:'job-a',dataset:{mode:'gallery'},running:false,calibration:null};
const record={id:21,name:'raw.jpg',counter:9,width:1280,height:1024,ready:true,contexts:[[200,200,600,600]],
  predictions:[{box:[300,300,350,310],score:12,kind:'strie',key:'detected',status:'a_examiner',comment:''}]};
Object.defineProperty(record,'annotations',{get(){throw Error('Le rendu a tenté de lire les annotations !');}});
const errors=[];
const viewer=window.createGalleryViewer({getState:()=>state,reportError:e=>errors.push(e),api:async path=>path.startsWith('/api/gallery/detail')?record:{total:1,items:[{id:21,counter:9,detections:1}]}});
viewer.setState(state);
setImmediate(()=>{
  assert.deepEqual(errors,[]);
  const svg=get('gallery-photo').children[1];
  assert.equal(svg.children.length,1);
  assert.equal(svg.children[0].attributes.stroke,'#ff4054');
  assert.equal(svg.children[0].attributes.x,300);
  get('gallery-overlay').checked=false;get('gallery-overlay').onchange();
  assert.equal(get('gallery-photo').children[1].style.display,'none');
  state={...state,run:'nist',dataset:{mode:'temporal'}};viewer.setState(state);
  assert.equal(get('gallery-space').hidden,true);
  assert.equal(get('review-space').hidden,false);
  console.log('Aalto : seuls les rectangles prédits sont rendus ; masquage et changement de bibliothèque vérifiés.');
});
