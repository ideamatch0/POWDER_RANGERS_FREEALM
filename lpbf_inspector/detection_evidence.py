"""Reproduce a detection from cached measurements, without decoding source photos."""
import json
import math
import numpy as np
from inspector import Detector, unpack, metadata

CHANNELS = ['Tile mean minus image mean', 'Tile texture (standard deviation)',
            'Tile brightest pixel minus image mean', 'Tile darkest pixel minus image mean']


def explain_trace(detector,event,geometry):
    trace=detector.trace
    if not trace:return {'available':False,'reason':'Insufficient comparable measurement history.'}
    kind=event['kind'];expected=float(event['score']);box=json.loads(event['box']) if isinstance(event['box'],str) else event['box']
    result={'available':True,'reference_count':trace['history_count'],'stored_ratio':expected,
            'note':'The detection reference is the preceding measurement history, not necessarily the previous photo. Priority is not material severity.'}
    if kind in {'changement_local','derive_locale'}:
        current,reference,threshold=trace['local' if kind=='changement_local' else 'drift']
        if current.ndim==2:current=current[None];reference=reference[None];threshold=threshold[None]
        thresholds=np.broadcast_to(threshold,current.shape)
        ratios=np.abs(current-reference)/thresholds
        roi=geometry['roi'];tile=geometry['tile']
        r0=max(0,int((box[1]-roi[1])//tile));c0=max(0,int((box[0]-roi[0])//tile))
        r1=min(current.shape[1],math.ceil((box[3]-roi[1])/tile));c1=min(current.shape[2],math.ceil((box[2]-roi[0])/tile))
        subset=ratios[:,r0:r1,c0:c1]
        if not subset.size:return {'available':False,'reason':'Indication outside the cached measurement grid.'}
        # Components can enclose unrelated cells; locate the stored component peak,
        # rather than silently substitute the largest ratio in its bounding box.
        channel,r,c=np.unravel_index(np.argmin(np.abs(subset-expected)),subset.shape);r+=r0;c+=c0
        value=float(current[channel,r,c]);baseline=float(reference[channel,r,c]);limit=float(thresholds[channel,r,c])
        result.update(channel=CHANNELS[channel] if kind=='changement_local' else 'Smoothed relative tile mean',
                      reference_type='Rolling median' if kind=='changement_local' else 'Fixed initial baseline versus smoothed current value',
                      peak_tile=[int(v) for v in (roi[0]+c*tile,roi[1]+r*tile,min(roi[2],roi[0]+(c+1)*tile),min(roi[3],roi[1]+(r+1)*tile))])
        result['envelope_tiles']=int(subset.shape[1]*subset.shape[2])
        result['above_threshold_tiles']=int(np.any(subset>=1,axis=0).sum())
    else:
        field={'luminosite_globale':'light','derive_globale':'light_drift','niveau_gris':'initial'}.get(kind)
        if not field or trace[field] is None:return {'available':False,'reason':'This detection type has no available cached reference.'}
        value,baseline,limit=map(float,trace[field]);result.update(channel='Analyzed image mean',reference_type={'light':'Rolling median','light_drift':'Fixed initial baseline versus smoothed current value','initial':'Initial job gray calibration'}[field])
    delta=abs(value-baseline);ratio=delta/limit
    result.update(current=value,reference=baseline,delta=delta,threshold=limit,recomputed_ratio=ratio,
                  ratio_verified=math.isclose(ratio,expected,rel_tol=.001,abs_tol=.001))
    return result


def explain_event(db,event,config):
    peak=db.execute('SELECT * FROM frames WHERE id=?',(event['peak_frame'],)).fetchone()
    if not peak or peak['features'] is None:return {'available':False,'reason':'Peak measurements unavailable.'}
    calibration=metadata(db,'gray_calibration',{}).get('channels',{}).get(event['camera']+'/'+event['phase'])
    detector=Detector(config,calibration)
    start=peak['layer']-config.history if event['kind']=='changement_local' else -2**63
    records=db.execute('SELECT * FROM frames WHERE camera=? AND phase=? AND layer>=? AND layer<=? ORDER BY layer',
                       (event['camera'],event['phase'],start,peak['layer']))
    for row in records:
        if row['features'] is None or row['error']:
            detector=Detector(config,calibration);continue
        detector.process(row['layer'],unpack(row['features']),row['luminance'],json.loads(row['geometry']),collect_events=False)
    return explain_trace(detector,event,json.loads(peak['geometry']))
