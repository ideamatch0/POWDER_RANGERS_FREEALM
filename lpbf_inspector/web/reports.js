'use strict';
window.createReportUI=function({getState,api,reportError}){
 const el=id=>document.getElementById(id);let context=null,task=null,busy=false,serial=0,dirty=false;
 const fields={job_name:'job-name',reference:'reference',author:'author',machine:'machine',material:'material',date:'date',conclusion:'conclusion',order:'order',region:'region',planes:'planes',contrast:'contrast'};
 function selectedTemplate(){return el('report-templates').querySelector('input:checked')?.value||'detailed';}
 function options(){const result=Object.fromEntries(Object.entries(fields).map(([key,id])=>[key,el('report-'+id).value]));return {...result,template:selectedTemplate(),include_3d:el('report-include-3d').checked,planes:Number(result.planes),contrast:Number(result.contrast)};}
 function volumeControls(){el('report-volume-options').hidden=!el('report-include-3d').checked;}
 function setBusy(value){busy=value;el('report-fields').disabled=value;el('report-build').disabled=value||!context?.retained;el('report-progress-area').hidden=!value;el('report-cancel').disabled=false;}
 function markChanged(){dirty=true;el('report-download').hidden=true;el('report-print').hidden=true;el('report-preview-state').textContent='Settings changed · generate a new preview';}
 async function cancel(){if(task?.status==='running'){el('report-cancel').disabled=true;try{await api('/api/reports/cancel',{id:task.id});}catch(error){el('report-error').textContent=error.message;}}}
 function displayTemplates(selected){
  el('report-templates').replaceChildren(...Object.entries(context.templates).map(([key,template])=>{
   const label=document.createElement('label');label.className='report-template';const radio=document.createElement('input');radio.type='radio';radio.name='report-template';radio.value=key;radio.checked=key===selected;
   const mini=document.createElement('span');mini.className='template-mini mini-'+key;mini.setAttribute('aria-hidden','true');
   for(const cls of ['mini-title','mini-volume','mini-table','mini-detail']){const span=document.createElement('span');span.className=cls;mini.append(span);}
   const strong=document.createElement('strong');strong.textContent=template.name;label.append(radio,mini,strong);return label;
  }));
  const describe=()=>{el('report-template-description').textContent=context.templates[selectedTemplate()].description;};
  el('report-templates').onchange=describe;describe();
 }
 async function open(){
  if(busy){el('report-dialog').showModal();return;}
  const current=++serial;el('report-dialog').showModal();el('report-error').textContent='';el('report-build').disabled=true;el('report-scope').textContent='Reading retained indications…';
  try{
   const data=await api('/api/reports/context?'+new URLSearchParams({run:getState().run}));if(current!==serial)return;context=data;task=null;
   let saved={};try{saved=JSON.parse(localStorage.getItem('powder-ranger-report:'+data.library_id)||'{}');}catch{}
   const values={...data.defaults,...saved,date:data.defaults.date,order:el('review-sort').value};
   // Les paramètres 3D courants servent de point de départ ; aucune coupe n'est exportée implicitement.
   values.contrast=Number(el('shape-contrast').value)||3;values.region=data.has_roi?el('stack-region').value:'full';
   for(const [key,id] of Object.entries(fields))el('report-'+id).value=values[key];
   el('report-include-3d').checked=values.include_3d!==false;el('report-region').querySelector('[value="parts"]').disabled=!data.has_roi;
   displayTemplates(data.templates[values.template]?values.template:'detailed');volumeControls();
   el('report-scope').textContent=data.library_name+' · '+data.retained+' exportable retained indication(s) · minimum persistence '+data.min_consecutive+' · '+Math.max(0,data.before_persistence-data.retained)+' retained indication(s) hidden by this filter.';
   if(!data.retained)el('report-error').textContent='Keep at least one indication meeting the minimum persistence before generating a report.';
   if(data.retained>500){el('report-error').textContent='This export is limited to 500 retained indications. Adjust the review or persistence filter.';context.retained=0;}
   el('report-preview-area').hidden=true;el('report-preview').removeAttribute('src');el('report-download').hidden=true;el('report-print').hidden=true;dirty=false;setBusy(false);
  }catch(error){el('report-error').textContent=error.message;reportError(error);}
 }
 el('report-form').oninput=()=>{if(!busy)markChanged();};el('report-form').onchange=()=>{volumeControls();if(!busy)markChanged();};
 el('report-form').onsubmit=async event=>{
  event.preventDefault();if(busy||!context||!el('report-form').reportValidity())return;
  const current=++serial,values=options();setBusy(true);el('report-error').textContent='';el('report-download').hidden=true;el('report-print').hidden=true;
  el('report-progress').value=0;el('report-progress-label').textContent='Generating report…';
  try{
   try{localStorage.setItem('powder-ranger-report:'+context.library_id,JSON.stringify(values));}catch{}
   task=await api('/api/reports/start',{run:context.run,revision:context.revision,options:values});
   while(current===serial&&task.status==='running'){
    el('report-progress').value=task.progress;el('report-progress-label').textContent=task.message+(Number.isFinite(task.eta)?' · estimated remaining '+task.eta+' s':'');
    await new Promise(resolve=>setTimeout(resolve,600));if(current!==serial)return;
    task=await api('/api/reports/status?'+new URLSearchParams({id:task.id}));
   }
   if(current!==serial)return;
   if(task.status==='error')throw Error(task.error||'Export failed.');
   if(task.status==='cancelled'){el('report-error').textContent='Generation cancelled.';return;}
   if(task.status!=='ready')throw Error('Unexpected report status.');
   const url='/api/reports/file?'+new URLSearchParams({id:task.id});
   dirty=false;el('report-preview-title').textContent='Preview · '+task.job_name;el('report-preview-state').textContent='Decision snapshot · '+context.retained+' retained';
   el('report-preview').src=url;el('report-preview-area').hidden=false;
   el('report-download').href=url+'&download=1';el('report-download').download=task.filename;el('report-download').hidden=false;el('report-print').hidden=false;el('report-print').disabled=true;
   el('report-preview-area').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(error){el('report-error').textContent=error.message;reportError(error);}finally{if(current===serial)setBusy(false);}
 };
 el('report-preview').onload=()=>{el('report-print').disabled=dirty||task?.status!=='ready';};
 el('report-print').onclick=()=>{if(!dirty&&task?.status==='ready'){el('report-preview').contentWindow.focus();el('report-preview').contentWindow.print();}};
 el('report-cancel').onclick=cancel;
 el('report-close').onclick=()=>{if(!busy)serial++;el('report-dialog').close();};
 el('report-dialog').oncancel=()=>{if(!busy)serial++;};
 return {open};
};
