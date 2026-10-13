function createScoreDetails({api,isCurrent,onEvidence}){
 const factors={intensity:'Detection strength',persistence:'Persistence',area:'Bounding-box area',part:'Estimated part overlap',stage:'Process stage'};
 const formula=document.getElementById('score-formula'),body=document.getElementById('score-factors'),evidence=document.getElementById('score-evidence');
 return async function show(detail,run){
  const e=detail.event;body.replaceChildren();
  const parts=[];
  for(const [key,value] of Object.entries(e.score_breakdown||{})){
   const row=document.createElement('tr');
   for(const text of [factors[key]||key,value.component.toFixed(1)+' / 100',(value.weight*100).toFixed(1)+'%',value.points.toFixed(2)+' points']){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}
   body.append(row);parts.push(value.points.toFixed(2));
  }
  formula.textContent=parts.length?parts.join(' + ')+' = '+e.priority_score.toFixed(1)+' / 100 (final rounding)':'';
  evidence.textContent='Checking the trigger against cached measurements…';
  try{
   const data=await api('/api/evidence?'+new URLSearchParams({run,id:e.id}));
   if(!isCurrent(detail,run))return;
   if(!data.available){evidence.textContent=data.reason||'Trigger measurements unavailable.';return;}
   const ratio=data.recomputed_ratio.toFixed(3);
   evidence.textContent=data.channel+' · '+data.reference_type+'\nCurrent '+data.current.toFixed(2)+' · reference '+data.reference.toFixed(2)+' · absolute change '+data.delta.toFixed(2)+' / 255\nTrigger: '+data.delta.toFixed(2)+' ÷ '+data.threshold.toFixed(2)+' = × '+ratio+' · '+(data.ratio_verified?'stored ratio verified':'stored ratio differs — review this result')+'\n'+data.note;
   if(data.envelope_tiles)evidence.textContent+='\n'+data.above_threshold_tiles+' of '+data.envelope_tiles+' tiles in the red bounding box exceed a threshold. Its full area is used for the area factor.';
   detail.detection_evidence=data;onEvidence(detail);
  }catch(error){if(isCurrent(detail,run))evidence.textContent='Trigger verification unavailable: '+error.message;}
 };
}
