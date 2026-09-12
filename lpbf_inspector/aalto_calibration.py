"""Calibration des seuils, puis évaluation par fabrication laissée de côté."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time

import numpy as np

from aalto_detector import VERSION, FEATURE_VERSION, THRESHOLDS, LINE_THRESHOLDS, candidate_regions, line_candidates, select_regions, iou_matrix

CONFIGS = [{'threshold': threshold, 'min_area': area, 'line_threshold': line}
           for threshold in THRESHOLDS for area in (16, 40) for line in (None, *LINE_THRESHOLDS)]
CONFIGS += [{'threshold':None,'min_area':16,'line_threshold':line} for line in LINE_THRESHOLDS]


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(path)


def match_boxes(predictions, annotations, threshold=.3):
    """Appariement un à un, par score décroissant, à un seuil IoU explicite."""
    ordered=sorted(predictions,key=lambda r:-r['score'])
    overlaps=iou_matrix([r['box'] for r in ordered],[r['box'] for r in annotations])
    matched=0
    for row in overlaps:
        if not len(row):break
        # Comme l'implémentation scalaire, choisir le dernier indice à IoU égal.
        index=len(row)-1-int(np.argmax(row[::-1]))
        if row[index]>=threshold:
            matched+=1;overlaps[:,index]=-1
    return matched,len(predictions)-matched,len(annotations)-matched


def metrics(tp, unmatched, missed):
    precision = tp/(tp+unmatched) if tp+unmatched else 0.
    recall = tp/(tp+missed) if tp+missed else 0.
    return {'matched': int(tp), 'unmatched': int(unmatched), 'missed': int(missed),
            'precision': precision, 'recall': recall,
            'f1': 2*precision*recall/(precision+recall) if precision+recall else 0.}


def choose_config(counts, calibration_indices):
    """Cette fonction ne voit que les compteurs des jobs de calibration."""
    totals = counts[calibration_indices].sum(axis=0)
    scores = [metrics(*row)['f1'] for row in totals]
    # À F1 égal, minimiser les alertes sans correspondance, puis préférer le seuil élevé.
    index = max(range(len(CONFIGS)), key=lambda i: (scores[i], -int(totals[i, 1]), CONFIGS[i]['threshold'] or 1000))
    return index, metrics(*totals[index])


def run_calibration(source, output, progress=lambda **values: None, stop=lambda: False):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    provenance_bytes = (source/'provenance.json').read_bytes()
    provenance = json.loads(provenance_bytes)
    records = provenance['records']
    jobs = sorted({r['job'] for r in records})
    if len(jobs) < 3:
        raise ValueError('La calibration exige trois fabrications séparées.')
    signature = hashlib.sha256(VERSION.encode()+provenance_bytes).hexdigest()
    started = time.monotonic()
    cache = sqlite3.connect(output/'candidates.sqlite')
    cache.execute('CREATE TABLE IF NOT EXISTS candidates (name TEXT PRIMARY KEY, signature TEXT, payload TEXT)')
    cache.commit()
    features = {}
    errors = []

    def extract(record,previous=None):
        if stop():
            raise InterruptedError('Calibration interrompue.')
        path = (source/record['name']).resolve()
        if source.resolve() not in path.parents:
            raise ValueError('Image hors bibliothèque.')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record['sha256']:
            raise ValueError('Image modifiée depuis la provenance : '+record['name'])
        if previous is not None:
            previous['lines']=line_candidates(path)
            return record,previous
        return record,candidate_regions(path)

    try:
        pending = []
        for r in records:
            path = source/r['name']
            stat = path.stat()
            stamp = f"{FEATURE_VERSION}:{r['sha256']}:{stat.st_size}:{stat.st_mtime_ns}"
            row = cache.execute('SELECT payload FROM candidates WHERE name=? AND signature=?', (r['name'], stamp)).fetchone()
            previous=json.loads(row[0]) if row else None
            if previous and 'lines' in previous:features[r['id']]=previous
            else:pending.append((r,stamp,previous))
        done = len(features)
        progress(stage='extraction', done=done, total=len(records), eta=None)
        # Deux images simultanées maximum : mémoire indépendante du volume source.
        with ThreadPoolExecutor(max_workers=2) as pool:
            for start in range(0, len(pending), 2):
                batch = pending[start:start+2]
                futures = [(r, stamp, pool.submit(extract, r, previous)) for r, stamp, previous in batch]
                for r, stamp, future in futures:
                    if stop():
                        raise InterruptedError('Calibration interrompue.')
                    try:
                        _, result = future.result()
                    except InterruptedError:
                        raise
                    except Exception as error:
                        errors.append({'id': r['id'], 'name': r['name'], 'error': str(error)})
                        continue
                    features[r['id']] = result
                    cache.execute('INSERT OR REPLACE INTO candidates VALUES(?,?,?)', (r['name'], stamp, json.dumps(result)))
                    cache.commit()
                    done += 1
                processed = start+len(batch)
                eta = (time.monotonic()-started)/max(1, processed)*(len(pending)-processed)
                progress(stage='extraction', done=done, total=len(records), eta=eta)
        if errors:
            atomic_json(output/'errors.json', errors)
            raise ValueError(f'{len(errors)} image(s) illisible(s) ou modifiée(s). Voir aalto_runs/errors.json. Aucun nouveau résultat publié.')
        counts = np.zeros((len(jobs), len(CONFIGS), 3), np.int64)
        calibration_started=time.monotonic()
        for index, r in enumerate(records):
            if stop():
                raise InterruptedError('Calibration interrompue.')
            if r['annotations']:
                for ci, config in enumerate(CONFIGS):
                    predictions = select_regions(features[r['id']], config)
                    counts[jobs.index(r['job']), ci] += match_boxes(predictions, r['annotations'], .3)
            if index % 20 == 0:
                eta=(time.monotonic()-calibration_started)/max(1,index)*(len(records)-index) if index else None
                progress(stage='calibration', done=index, total=len(records), eta=eta)
        all_results = {}
        report = {'version': VERSION, 'signature': signature, 'created': datetime.now(timezone.utc).isoformat(),
                  'images': len(records), 'protocol': 'leave-one-job-out', 'selection_iou': .3,
                  'objective': 'F1 sur les rectangles annotés des deux autres jobs', 'configs_tested': len(CONFIGS),
                  'limitations': ["Évaluation interne rétrospective ; les seuils seuls sont choisis hors job.",
                    "Photos sans rectangle exploitable exclues des mesures de correspondance, mais toutes analysées.",
                    "Une alerte sans correspondance n'est pas nécessairement un faux défaut : les annotations peuvent être incomplètes.",
                    "Aucune sensibilité ou spécificité de contrôle industriel n'est établie.",
                    "Les compteurs ne sont pas assimilés aux couches ; aucune étape ou hauteur inventée."],
                  'jobs': {}}
        for job_index, job in enumerate(jobs):
            calibration_indices = [i for i in range(len(jobs)) if i != job_index]
            config_index, calibration_metrics = choose_config(counts, calibration_indices)
            config = CONFIGS[config_index]
            rows = [r for r in records if r['job'] == job]
            selected = {}
            strict = np.zeros(3, np.int64)
            for r in rows:
                predictions = select_regions(features[r['id']], config)
                selected[str(r['id'])] = {'id': r['id'], 'name': r['name'], 'job': job, 'predictions': predictions}
                if r['annotations']:
                    strict += match_boxes(predictions, r['annotations'], .5)
            profile = {'version': VERSION, 'config': config, 'excluded_job': job,
                       'calibration_jobs': [jobs[i] for i in calibration_indices], 'signature': signature}
            atomic_json(output/f'profile_{job}.json', profile)
            report['jobs'][job] = {'job': job, 'images': len(rows),
                'annotated_images': sum(bool(r['annotations']) for r in rows),
                'reference_boxes': sum(len(r['annotations']) for r in rows),
                'unknown_images': sum(not r['annotations'] for r in rows),
                'detections': sum(len(r['predictions']) for r in selected.values()),
                'flagged_images': sum(bool(r['predictions']) for r in selected.values()),
                'config': config, 'calibration_jobs': profile['calibration_jobs'],
                'calibration_metrics': calibration_metrics, 'iou30': metrics(*counts[job_index, config_index]),
                'iou50': metrics(*strict)}
            all_results.update(selected)
        report['seconds'] = round(time.monotonic()-started, 2)
        # Un fichier atomique associe métriques, profils et prédictions de la même exécution.
        result = {'report': report, 'images': all_results}
        atomic_json(output/'results.json', result)
        atomic_json(output/'errors.json', [])
        progress(stage='termine', done=len(records), total=len(records), eta=0)
        return result
    finally:
        cache.close()


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    last = [0.]
    def log(**values):
        now = time.monotonic()
        if now-last[0] > 5 or values['stage'] == 'termine':
            print(json.dumps(values), flush=True)
            last[0] = now
    result = run_calibration(root/'datasets'/'aalto_pb', root/'aalto_runs', log)
    print(json.dumps(result['report'], ensure_ascii=False, indent=2))
