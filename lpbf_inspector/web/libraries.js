window.createLibraryUI=function({getState,api,refresh,reportError}) {
  const el=id=>document.getElementById(id);let catalogKey='';
  const patterns={
    standard:{regex:'(?P<camera>cam[0-9]+)_layer(?P<layer>[0-9]+)_(?P<phase>spread|fused)\\.(?:jpe?g|png)',aliases:{spread:'etalement',fused:'fusion'}},
    french:{regex:'(?P<camera>cam[0-9]+)_layer(?P<layer>[0-9]+)_(?P<phase>etalement|fusion)\\.(?:jpe?g|png)',aliases:{etalement:'etalement',fusion:'fusion'}},
    nist:{regex:'(?P<phase>A|B)(?P<layer>[0-9]{4})(?P<camera>[abc])\\.PNG',aliases:{A:'etalement',B:'fusion'}}
  };
  function setPattern(){const p=patterns[el('import-pattern').value];if(p){el('import-regex').value=p.regex;el('import-aliases').value=JSON.stringify(p.aliases,null,2);}else el('import-advanced').open=true;}
  setPattern();el('import-pattern').onchange=setPattern;
  el('import-thickness').oninput=el('import-first').oninput=()=>{el('import-z').value=Number(el('import-first').value)*Number(el('import-thickness').value)/1000;};
  el('import-library').onclick=()=>{el('import-error').textContent='';el('import-dialog').showModal();};
  el('close-import').onclick=()=>el('import-dialog').close();
  el('browse-folder').onclick=async()=>{const button=el('browse-folder');button.disabled=true;el('import-error').textContent='';try{const result=await api('/api/libraries/browse',{});if(result.path)el('import-path').value=result.path;}catch(error){el('import-error').textContent='The folder picker is unavailable. Paste the folder path above.';}finally{button.disabled=false;}};
  el('library-select').onchange=async()=>{try{await api('/api/libraries/select',{id:el('library-select').value});await refresh();}catch(error){reportError(error);el('library-select').value=getState().dataset.id;}};
  el('import-form').onsubmit=async event=>{event.preventDefault();el('import-error').textContent='';try{
    const config={filename_regex:el('import-regex').value,phase_aliases:JSON.parse(el('import-aliases').value),layer_thickness_um:Number(el('import-thickness').value),first_layer:Number(el('import-first').value),first_layer_z_mm:Number(el('import-z').value),intensity_white_level:Number(el('import-white').value)};
    await api('/api/libraries/import',{path:el('import-path').value,name:el('import-name').value,config});
    el('import-dialog').close();await refresh();
  }catch(error){el('import-error').textContent=error.message;}};
  return {setState(state){
    const signature=JSON.stringify(state.libraries.map(l=>[l.id,l.name]));if(signature!==catalogKey){catalogKey=signature;el('library-select').replaceChildren(...state.libraries.map(l=>{const option=document.createElement('option');option.value=l.id;option.textContent=l.name;return option;}));}
    el('library-select').value=state.dataset.id;el('library-select').disabled=state.running;el('import-library').disabled=state.running;
    el('library-note').textContent=state.dataset.note||'';
    const source=el('source-note');source.replaceChildren();
    if(state.dataset.source_url){const a=document.createElement('a');a.href=state.dataset.source_url;a.target='_blank';a.rel='noopener';a.textContent='Image source · '+state.dataset.license+' ↗';source.append(a);}
    else source.textContent='Local folder: '+state.dataset.source;
    if(state.dataset.unmatched)source.append(document.createTextNode(' · '+state.dataset.unmatched+' image(s) not recognized by the filename pattern.'));
  }};
};
