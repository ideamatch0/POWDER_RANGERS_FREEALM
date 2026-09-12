/* Animation décorative de l'accueil ; aucun appel au moteur d'analyse. */
(() => {
  const button=document.getElementById('motion-toggle');
  const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
  let paused=preference.matches,manualChoice=false;
  function renderMotion(){
    document.body.classList.toggle('motion-paused',paused);
    document.documentElement.classList.toggle('motion-enabled',!paused);
    document.getElementById('motion-label').textContent=paused?'Resume':'Pause';
    document.getElementById('motion-glyph').textContent=paused?'▷':'Ⅱ';
    button.setAttribute('aria-label',paused?'Resume animation':'Pause animation');
  }
  button.hidden=false;
  button.addEventListener('click',()=>{manualChoice=true;paused=!paused;renderMotion();});
  preference.addEventListener('change',event=>{if(!manualChoice){paused=event.matches;renderMotion();}});
  const visibility=()=>document.body.classList.toggle('tab-hidden',document.hidden);
  document.addEventListener('visibilitychange',visibility);
  window.addEventListener('pageshow',visibility);
  renderMotion();visibility();
})();
