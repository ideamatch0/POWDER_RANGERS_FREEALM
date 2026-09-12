const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
class Element{
 constructor(){this.children=[];this.value='';this.hidden=false;this.disabled=false;this.checked=false;this.textContent='';}
 append(...children){this.children.push(...children)}replaceChildren(...children){this.children=children}
 setAttribute(){}removeAttribute(key){delete this[key]}showModal(){this.open=true}close(){this.open=false}scrollIntoView(){}reportValidity(){return true}
 querySelector(query){if(query==='input:checked')return this.children.flatMap(x=>x.children).find(x=>x.checked);return this.option||(this.option=new Element())}
}
const nodes={};const el=id=>nodes[id]||(nodes[id]=new Element());let printed=0;
el('report-preview').contentWindow={focus(){},print(){printed++}};
el('review-sort').value='priority';el('shape-contrast').value='4';el('stack-region').value='parts';
const storage=new Map(),calls=[],errors=[];let retained=2,revision=5,reply='ready',taskStarted;
const context={library_id:'job-a',library_name:'Job A',run:'run-a',min_consecutive:3,before_persistence:4,has_roi:true,
 defaults:{job_name:'Job A',reference:'',author:'',machine:'',material:'',date:'2026-09-09',conclusion:'',template:'detailed',planes:64,include_3d:true},
 templates:{summary:{name:'Summary',description:'Summary description'},detailed:{name:'Detailed',description:'Detail description'},presentation:{name:'Presentation',description:'Presentation description'}}};
const scope={window:{},document:{getElementById:el,createElement:()=>new Element()},URLSearchParams,Number,Error,
 localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},setTimeout:resolve=>Promise.resolve().then(resolve)};
vm.createContext(scope);vm.runInContext(fs.readFileSync('web/reports.js','utf8'),scope);
const api=async(path,body)=>{
 calls.push({path,body});
 if(path.startsWith('/api/reports/context'))return {...context,retained,revision};
 if(path==='/api/reports/start'){taskStarted?.();return {id:'report-1',status:'running',progress:20,message:'Rendering views',eta:2}}
 if(path.startsWith('/api/reports/status'))return {id:'report-1',status:reply,progress:100,job_name:'My build',filename:'my-build.html',error:reply==='error'?'Review changed':null};
 if(path==='/api/reports/cancel'){reply='cancelled';return {status:'running'}}
 throw Error(path)
};
const ui=scope.window.createReportUI({api,getState:()=>({run:'run-a'}),reportError:e=>errors.push(e.message)});
const submit=()=>el('report-form').onsubmit({preventDefault(){}});
(async()=>{
 await ui.open();assert.equal(el('report-job-name').value,'Job A');assert.equal(el('report-order').value,'priority');
 assert.equal(el('report-region').value,'parts');assert.equal(el('report-contrast').value,4);assert.equal(el('report-templates').children.length,3);
 el('report-job-name').value='My build';await submit();
 const start=calls.find(c=>c.path==='/api/reports/start').body;
 assert.equal(start.revision,5);assert.equal(start.options.job_name,'My build');assert.equal(start.options.include_3d,true);assert.equal(start.options.planes,64);
 assert.equal(el('report-preview').src,'/api/reports/file?id=report-1');assert.equal(el('report-download').hidden,false);
 assert.equal(el('report-print').disabled,true);el('report-preview').onload();assert.equal(el('report-print').disabled,false);
 el('report-print').onclick();assert.equal(printed,1);
 el('report-form').oninput();assert.equal(el('report-download').hidden,true);assert.equal(el('report-print').hidden,true);
 el('report-print').onclick();assert.equal(printed,1,'Changed settings must not print an obsolete report');
 await ui.open();assert.equal(el('report-job-name').value,'My build','Saved report fields persist for this library');
 reply='error';await submit();assert.equal(el('report-error').textContent,'Review changed');assert.equal(el('report-fields').disabled,false);
 retained=0;await ui.open();assert.equal(el('report-build').disabled,true);assert.match(el('report-error').textContent,/Keep at least one/);
 retained=2;reply='cancelled';await ui.open();await submit();assert.match(el('report-error').textContent,/cancelled/);assert.equal(el('report-download').hidden,true);
 assert.deepEqual(errors,['Review changed']);console.log('Report UI: templates, saved fields, immutable revision, progress, preview, print, stale settings, errors and cancellation passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
