const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
const source=html.slice(html.indexOf('async function decide('),html.indexOf('async function applyPersistence('));
function scenario(next_id){
 const nodes={};const calls=[];const current={event:{id:'125:0',snapshot:'snap',status:'a_examiner',comment:''}};
 const scope={state:{run:'job-A'},selected:current,savingDecision:false,reviewFinished:false,requestSerial:0,statusName:{retenue:'Retenue',ecartee:'Écartée',a_examiner:'À examiner'},
  $:id=>nodes[id]||(nodes[id]={value:'Mon observation',textContent:'',querySelector(){return this}}),
  message:error=>{if(error)calls.push(['error',String(error)])},renderState(){},
  api:async(route,body)=>{calls.push(['saved',body]);return {saved:true}},
  loadList:async options=>{calls.push(['list',options]);return {next_id}},
  choose:async id=>{calls.push(['choose',id]);scope.selected={event:{id}}},refreshState:async()=>{}};
 vm.createContext(scope);vm.runInContext(source,scope);return {scope,calls,current,nodes};
}
(async()=>{
 for(const status of ['retenue','ecartee']){
  const {scope,calls}=scenario('126:0');await scope.decide(status);
  assert.equal(calls[0][0],'saved');assert.equal(calls[0][1].comment,'Mon observation');
  assert.equal(calls[1][1].after,'125:0');assert.equal(calls[1][1].autoSelect,false);
  assert.equal(calls[2][1],'126:0');assert.equal(scope.savingDecision,false);
 }
 const pending=scenario('126:0');await pending.scope.decide('a_examiner');assert.equal(pending.scope.selected,pending.current);assert.ok(!pending.calls.some(c=>c[0]==='choose'));
 const end=scenario(null);await end.scope.decide('retenue');assert.equal(end.scope.selected,null);assert.equal(end.scope.reviewFinished,true);assert.match(end.nodes.empty.textContent,/End of list/);
 const failed=scenario('126:0');failed.scope.api=async()=>{throw Error('Enregistrement refusé')};await failed.scope.decide('ecartee');assert.equal(failed.scope.selected,failed.current);assert.equal(failed.current.event.status,'a_examiner');assert.ok(!failed.calls.some(c=>c[0]==='choose'));
 const doubled=scenario('126:0');let finish;doubled.scope.api=async(_,body)=>{doubled.calls.push(['saved',body]);await new Promise(resolve=>finish=resolve)};
 const first=doubled.scope.decide('retenue');await doubled.scope.decide('ecartee');finish();await first;assert.equal(doubled.calls.filter(c=>c[0]==='saved').length,1);
 const changed=scenario('126:0');changed.scope.api=async()=>{changed.scope.state={run:'job-B'}};await changed.scope.decide('retenue');assert.ok(!changed.calls.some(c=>c[0]==='choose'));
 console.log('Revue : passage après sauvegarde, maintien À examiner, fin de liste, erreur, double clic et changement de job vérifiés.');
})().catch(error=>{console.error(error);process.exitCode=1});
