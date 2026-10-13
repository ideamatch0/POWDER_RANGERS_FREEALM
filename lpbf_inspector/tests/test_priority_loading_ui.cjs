const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
const nodes={phase:{value:''},status:{value:''},'review-sort':{value:'priority'},'part-only':{checked:false},list:{clears:0,replaceChildren(){this.clears++}},page:{}};
const scope={state:{run:'job'},offset:0,listSerial:0,priorityPending:false,pendingAdvance:null,URLSearchParams,$:id=>nodes[id]||(nodes[id]={}),message:value=>scope.feedback=value,
 document:{createElement:()=>({})},choose:async id=>scope.chosen=id,
 api:async()=>({pending:true,done:10,work_total:278,total:278})};
vm.createContext(scope);vm.runInContext(html.slice(html.indexOf('async function loadList'),html.indexOf('function svgElement')),scope);
(async()=>{await scope.loadList();assert.equal(scope.priorityPending,true);assert.equal(nodes.list.clears,0);assert.match(scope.feedback,/10 \/ 278/);assert.equal(nodes.page.textContent,'Preparing scores…');
 const current={event:{id:125}};scope.selected=current;scope.pendingAdvance={run:'job',id:125,current};nodes.list.append=()=>{};
 scope.api=async url=>{assert.match(url,/after=125/);return {items:[],total:0,next_id:126}};
 await scope.loadList();assert.equal(scope.chosen,126);assert.equal(scope.pendingAdvance,null);assert.equal(scope.priorityPending,false);
 console.log('Priority preparation preserves the current list, shows progress, and resumes saved-decision navigation.');})().catch(error=>{console.error(error);process.exitCode=1});
