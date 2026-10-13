const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
class Element{constructor(){this.children=[];this.textContent=''}append(e){this.children.push(e)}replaceChildren(){this.children=[]}}
const nodes={'score-formula':new Element(),'score-factors':new Element(),'score-evidence':new Element()};
const scope={document:{getElementById:id=>nodes[id],createElement:()=>new Element()},URLSearchParams};vm.createContext(scope);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/score-details.js'),'utf8'),scope);
(async()=>{
 let current,rendered=0;const evidence={available:true,channel:'Texture',reference_type:'Rolling median',current:24,reference:0,delta:24,threshold:8,recomputed_ratio:3,ratio_verified:true,note:'Not material severity',envelope_tiles:4,above_threshold_tiles:1};
 const detail={event:{id:7,priority_score:50,score_breakdown:{intensity:{component:50,weight:.35,points:17.5}}}};current=detail;
 const show=scope.createScoreDetails({api:async()=>evidence,isCurrent:d=>current===d,onEvidence:()=>rendered++});await show(detail,'job');
 assert.match(nodes['score-formula'].textContent,/17.50/);assert.match(nodes['score-evidence'].textContent,/24.00 ÷ 8.00 = × 3.000/);assert.match(nodes['score-evidence'].textContent,/stored ratio verified/);assert.equal(rendered,1);
 let resolve;const stale=scope.createScoreDetails({api:()=>new Promise(r=>resolve=r),isCurrent:d=>current===d,onEvidence:()=>rendered++});const work=stale(detail,'job');current=null;resolve(evidence);await work;assert.equal(rendered,1);
 console.log('Score details: exact contributions, trigger calculation, and stale responses verified.');
})().catch(error=>{console.error(error);process.exitCode=1});
