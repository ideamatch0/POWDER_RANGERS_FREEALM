from pathlib import Path
root=Path(__file__).resolve().parents[1]
mapping={'Retenez':'Keep between','Gros plans : même cadrage':'Close-ups: matching crop','Vue d’ensemble':'Overview','changé':'changed','limites':'limits',
'Persistance minimale : 3':'Minimum persistence: 3','Priorité {':'Priority {',"ValueError,'fusion'":"ValueError,'post-melting'",'couches comparées':'compared layers','partie de l’analyse':'included in the analysis','Doublon':'Duplicate','Dimensions différentes':'Different dimensions',
"ValueError, 'ambigu'":"ValueError, '[Aa]mbiguous'", "ValueError, 'figés'":"ValueError, 'fixed'", "ValueError, 'modifié'":"ValueError, 'changed'",'16 bits':'16-bit',"ValueError,'évolué'":"ValueError,'changed'", "ValueError,'ce job'":"ValueError,'this job'",'autre bibliothèque':'another library',"ValueError,'voisin'":"ValueError,'adjacent'",'Revue commune':'Build image review report',"ValueError,'persistance'":"ValueError,'persistence'",'/Fin de la liste/':'/End of list/','/Couche 1/':'/Layer 1/'}
for name in ['test_local_app.py','test_aalto.py','test_inspector.py','test_review_navigation.cjs','test_stack_controls.cjs']:
    p=root/'tests'/name;s=p.read_text(encoding='utf-8')
    for old,new in mapping.items():s=s.replace(old,new)
    p.write_text(s,encoding='utf-8')
