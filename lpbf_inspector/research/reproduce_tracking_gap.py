"""Non-mutating demonstration of the remaining peak-box association limitation."""
from pathlib import Path
import sys,tempfile,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspector import connect,add_event
with tempfile.TemporaryDirectory() as folder:
    db=connect(folder)
    for layer,box,score in [(1,[0,0,10,10],5),(2,[5,0,15,10],3),(3,[10,0,20,10],2)]:
        db.execute('INSERT INTO frames(id,path,camera,phase,layer,size,mtime) VALUES(?,?,?,?,?,?,?)',
                   (layer,str(layer),'cam1','etalement',layer,0,0))
        add_event(db,{'id':layer,'camera':'cam1','phase':'etalement','layer':layer},'changement_local',box,score)
    events=[dict(r) for r in db.execute('SELECT start_layer,end_layer,box,score FROM events ORDER BY id')]
    result={'expected_adjacent_overlap_tracks':1,'actual_peak_box_tracks':len(events),'events':events,
            'conclusion':'Confirmed: the peak box prevents association of a drifting region that overlaps on every adjacent layer.'}
    assert len(events)==2,'Review the finding: behavior has changed'
    db.close()
    print(json.dumps(result,indent=2))
