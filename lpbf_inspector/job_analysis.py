"""Calibration photométrique et analyse d'un seul job, sans labels ni job externe."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

import numpy as np
from PIL import Image
from inspector import Config, Detector, extract, pack, unpack
from storage import atomic_json

VERSION='single-job-2'
MEASUREMENT_VERSION='single-job-1'


def write_json(path,value):
    atomic_json(path,value)


def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def check_records(records):
    if not records or len({r['job'] for r in records})!=1:
        raise ValueError('An analysis must contain exactly one job.')
    if len({r['counter'] for r in records})!=len(records):
        raise ValueError('Duplicate acquisition counters in this job.')
    return sorted(records,key=lambda r:r['counter'])


def calibration_signature(fingerprint,config,step):
    return signature([MEASUREMENT_VERSION,fingerprint,config.roi_by_camera,step,config.intensity_white_level])


def analysis_signature(fingerprint,config,step):
    return signature([VERSION,calibration_signature(fingerprint,config,step),asdict(config),step])


def measure(path,config):
    return extract(path, config, 'aalto')


def source_path(source,record):
    source=Path(source).resolve();path=(source/record['name']).resolve()
    if source not in path.parents:raise ValueError('Image outside the library.')
    return path


def calibrate(source,records,config,step,fingerprint,progress=lambda **v:None,stop=lambda:False):
    records=check_records(records)
    if step not in (1,2):raise ValueError('Invalid acquisition interval.')
    selected={channel:[r for r in records if r['counter']%step==channel][:20] for channel in range(step)}
    values={};errors=[];started=time.monotonic();done=0;total=sum(map(len,selected.values()))
    for channel,rows in selected.items():
        lights=[];valid=[]
        for record in rows:
            if stop():raise InterruptedError('Calibration interrompue.')
            try:
                _,level,_=measure(source_path(source,record),config)
                lights.append(level);valid.append(record)
            except (OSError,ValueError,Image.DecompressionBombError) as error:
                errors.append({'id':record['id'],'error':str(error)})
            done+=1
            progress(stage='gris',done=done,total=total,eta=(time.monotonic()-started)/done*(total-done))
        if lights:
            values[str(channel)]={'mean_gray':float(np.mean(lights)),'std_gray':float(np.std(lights)),
                                  'sample_ids':[r['id'] for r in valid],
                                  'first_counter':rows[0]['counter'],'last_counter':rows[-1]['counter']}
        elif rows:raise ValueError('No readable calibration images in sequence '+str(channel)+'.')
    measured=sum(len(v['sample_ids']) for v in values.values())
    return {'version':VERSION,'job':records[0]['job'],'signature':calibration_signature(fingerprint,config,step),
            'fingerprint':fingerprint,'step':step,'sample_images':measured,'errors':errors,'channels':values,
            'mean_gray':sum(v['mean_gray']*len(v['sample_ids']) for v in values.values())/measured,
            'note':'Mean gray level from the first 20 acquisitions in each sequence. These images are not assumed to be defect-free.'}


def analyze_job(source,records,config,step,fingerprint,calibration,folder,progress=lambda **v:None,stop=lambda:False):
    records=check_records(records);job=records[0]['job'];folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    expected=calibration_signature(fingerprint,config,step)
    if calibration['job']!=job or calibration['signature']!=expected:
        raise ValueError('Calibration does not match this job and crop.')
    run_signature=analysis_signature(fingerprint,config,step)
    started=time.monotonic();results={};detectors={};warmup=0;gaps=0;cached=0;errors=[]
    db=sqlite3.connect(folder/'measurements.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS features(signature TEXT PRIMARY KEY,values_blob BLOB,level REAL,geometry TEXT)')
    try:
        for index,record in enumerate(records):
            if stop():raise InterruptedError('Analyse interrompue. Relancer réutilise les mesures déjà calculées.')
            channel=record['counter']%step
            cal=calibration['channels'][str(channel)]
            if channel not in detectors:
                detectors[channel]=Detector(config, {**cal,'last_position':cal['last_counter']//step})
            detector=detectors[channel]
            predictions=[];ready=False;level=None;geometry=None;gap=False
            try:
                path=source_path(source,record);stat=path.stat()
                stamp=signature([MEASUREMENT_VERSION,str(path),stat.st_size,stat.st_mtime_ns,config.tile_px,config.roi_by_camera,config.intensity_white_level])
                stored=db.execute('SELECT values_blob,level,geometry FROM features WHERE signature=?',(stamp,)).fetchone()
                if stored:
                    values,level,geometry=unpack(stored[0]),stored[1],json.loads(stored[2]);cached+=1
                else:
                    values,level,geometry=measure(path,config)
                    db.execute('INSERT INTO features VALUES(?,?,?,?)',(stamp,pack(values),level,json.dumps(geometry)))
                events,ready,gap=detector.process(record['counter']//step,values,level,geometry)
                predictions=[{'kind':kind,'box':box,'score':round(float(score),3)} for kind,box,score in events]
                if not ready:warmup+=1
                if gap:gaps+=1
            except (OSError,ValueError,Image.DecompressionBombError) as error:
                errors.append({'id':record['id'],'error':str(error)});detectors.pop(channel,None)
            results[str(record['id'])]={'id':record['id'],'job':job,'name':record['name'],'counter':record['counter'],
                'mean_gray':level,'calibration_gray':cal['mean_gray'],'analyzed':ready,'predictions':predictions,
                'geometry':geometry,'error':errors[-1]['error'] if errors and errors[-1]['id']==record['id'] else None}
            if (index+1)%20==0 or index+1==len(records):
                db.commit();progress(stage='analyse_job',done=index+1,total=len(records),eta=(time.monotonic()-started)/(index+1)*(len(records)-index-1))
        report={'job':job,'signature':run_signature,'version':VERSION,'mode':'single',
            'images':len(records),'measured':len(records)-len(errors),'evaluated':sum(r['analyzed'] for r in results.values()),
            'warmup_images':warmup,'gaps':gaps,'errors':errors,'cached':cached,'step':step,
            'detections':sum(len(r['predictions']) for r in results.values()),
            'flagged_images':sum(bool(r['predictions']) for r in results.values()),'calibration_gray':calibration['mean_gray'],
            'seconds':round(time.monotonic()-started,3),'config':asdict(config),
            'note':'Changes and drift within this job. Annotations and other jobs are not used. Physical stages are unidentified.'}
        result={'report':{'signature':run_signature,'jobs':{job:report}},'images':results}
        write_json(folder/f'analysis_{run_signature}.json',result)
        return result
    finally:db.commit();db.close()
