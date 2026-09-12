const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
for(const script of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(script[1]);
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.style={};this.classList={add(){}};}
 append(...children){this.children.push(...children)}
 replaceChildren(...children){this.children=children}
 setAttribute(k,v){this.attrs[k]=v}
}
const nodes={};const scope={document:{createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t)},
 $:id=>nodes[id]||(nodes[id]=new Element('div')),JSON,Math,
 phaseName:{fusion:'Fusion',acquisition:'Acquisition'},axisName:()=>scope.selected.axis==='acquisition'?'Acquisition':'Couche',imageURL:(id,crop)=>'/image/'+id+'?crop='+crop};
vm.createContext(scope);
vm.runInContext(html.slice(html.indexOf('function svgElement'),html.indexOf('async function choose')),scope);
for(const axis of ['layer','acquisition']){
 scope.selected={axis,event:{box:'[300,400,340,440]'},crop:[192,292,448,548],geometry:{width:1280,height:1024},peak_layer:34,step:1,
 frames:[33,34,35].map(id=>({id,layer:id,phase:axis==='acquisition'?'acquisition':'fusion',comparable:true,name:'photo'+id}))};
 scope.$('overlay').checked=true;scope.renderInspection();
 const svg=nodes.overview.children.find(e=>e.tag==='svg');
 assert.ok(svg.children.some(e=>e.tag==='rect'&&e.attrs.stroke==='#087dab'&&e.attrs['stroke-dasharray']==='5 4'),axis+' : cadre bleu de contexte');
 assert.ok(svg.children.some(e=>e.tag==='rect'&&e.attrs.stroke==='#ef3535'),axis+' : cadre rouge de détection');
 assert.equal(svg.children.filter(e=>e.tag==='rect').at(-1).attrs.stroke,'#087dab','Le contexte bleu doit rester visible même quand il coïncide avec le cadre rouge.');
 assert.equal(nodes['image-grid'].children.length,3);
 const crops=nodes['image-grid'].children.map(f=>f.children.find(e=>e.className==='photo').children.find(e=>e.tag==='svg').attrs.viewBox);
 assert.deepEqual(crops,['192 292 256 256','192 292 256 256','192 292 256 256']);
}
console.log('Revue commune NIST/Aalto : cadre bleu pointillé, cadre rouge et trois cadrages identiques vérifiés.');
