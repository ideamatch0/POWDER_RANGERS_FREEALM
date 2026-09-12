"""Prototype LPBF, local et sans apprentissage. Python 3.10+.

Une série = une caméra + un état du procédé. Aucun tri chronologique
implicite ni déduction du numéro de couche à partir de la seule épaisseur.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass, field
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import zlib

import numpy as np
from PIL import Image

VERSION = "0.2.0"
PHASES = {"etalement", "fusion"}


@dataclass
class Config:
    filename_regex: str = r"(?P<camera>cam[0-9]+)_layer(?P<layer>[0-9]+)_(?P<phase>spread|fused)\.jpe?g"
    phase_aliases: dict = field(default_factory=lambda: {"spread": "etalement", "fused": "fusion"})
    layer_thickness_um: float = 60.0
    first_layer: int = 1
    first_layer_z_mm: float = 0.06
    tile_px: int = 16
    history: int = 9
    warmup: int = 5
    sigma: float = 6.0
    min_change_gray: float = 12.0
    min_texture_change: float = 8.0
    global_jump_gray: float = 12.0
    drift_gray: float = 20.0
    drift_alpha: float = 0.2
    roi_by_camera: dict = field(default_factory=dict)
    intensity_white_level: float = 255.0
    analysis_phases: list = field(default_factory=lambda: ['etalement','fusion'])

    def validate(self):
        if not isinstance(self.filename_regex,str) or len(self.filename_regex)>4000:
            raise ValueError('Filename pattern must be text with at most 4,000 characters.')
        if not isinstance(self.phase_aliases,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in self.phase_aliases.items()):
            raise ValueError('Stage aliases must map text names to stage identifiers.')
        if not isinstance(self.roi_by_camera,dict):
            raise ValueError('Camera regions must be a mapping.')
        if type(self.first_layer_z_mm) not in (int,float):
            raise ValueError('Origin height must be a finite number.')
        try:expression = re.compile(self.filename_regex, re.I)
        except re.error as error:raise ValueError('Invalid filename pattern: '+str(error)) from error
        if not {"camera", "layer", "phase"} <= expression.groupindex.keys():
            raise ValueError("The pattern must include camera, layer and phase as named groups.")
        for name in ("tile_px", "history", "warmup", "first_layer"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer.")
        if self.tile_px < 2 or not 3 <= self.warmup <= self.history <= 101:
            raise ValueError("Required: tile_px >= 2 and 3 <= warmup <= history <= 101.")
        for name in ("layer_thickness_um", "sigma", "min_change_gray", "min_texture_change",
                     "global_jump_gray", "drift_gray", "drift_alpha", "intensity_white_level"):
            value = getattr(self, name)
            if not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite.")
        if self.drift_alpha > 1 or not math.isfinite(self.first_layer_z_mm):
            raise ValueError("Required: drift_alpha <= 1 and a finite origin height.")
        if not self.phase_aliases or not set(self.phase_aliases.values()) <= PHASES:
            raise ValueError("Target stage identifiers are etalement and fusion.")
        if (not isinstance(self.analysis_phases,list) or not self.analysis_phases
                or not set(self.analysis_phases) <= PHASES
                or len(self.analysis_phases)!=len(set(self.analysis_phases))):
            raise ValueError('Select etalement, fusion or both for analysis.')
        if len({str(k).casefold() for k in self.phase_aliases}) != len(self.phase_aliases):
            raise ValueError("Ambiguous stage aliases.")
        for camera, roi in self.roi_by_camera.items():
            if (not isinstance(camera, str) or not isinstance(roi,(list,tuple)) or len(roi) != 4
                    or any(type(v) is not int for v in roi)
                    or not (0 <= roi[0] < roi[2] and 0 <= roi[1] < roi[3])):
                raise ValueError("Each ROI must contain integer pixel coordinates [x0,y0,x1,y1].")
        return self

    def z(self, layer):
        return self.first_layer_z_mm + (layer - self.first_layer) * self.layer_thickness_um / 1000


def connect(project):
    path = Path(project)
    path.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path / "project.sqlite", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      PRAGMA journal_mode=WAL;
      PRAGMA foreign_keys=ON;
      PRAGMA cache_size=-32768;
      PRAGMA temp_store=FILE;
      CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS frames(
        id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL,
        camera TEXT NOT NULL, phase TEXT NOT NULL, layer INTEGER NOT NULL,
        size INTEGER NOT NULL, mtime INTEGER NOT NULL,
        features BLOB, geometry TEXT, luminance REAL, error TEXT,
        UNIQUE(camera,phase,layer));
      CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY, camera TEXT NOT NULL, phase TEXT NOT NULL,
        kind TEXT NOT NULL, start_layer INTEGER NOT NULL, end_layer INTEGER NOT NULL,
        peak_frame INTEGER NOT NULL REFERENCES frames(id), box TEXT NOT NULL,
        score REAL NOT NULL, status TEXT NOT NULL DEFAULT 'a_examiner',
        comment TEXT NOT NULL DEFAULT '');
      CREATE INDEX IF NOT EXISTS event_active ON events(camera,phase,kind,end_layer);
      CREATE TABLE IF NOT EXISTS issues(
        code TEXT NOT NULL, path TEXT NOT NULL, detail TEXT NOT NULL,
        PRIMARY KEY(code,path));
      CREATE TABLE IF NOT EXISTS decisions(
        id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id),
        timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL, comment TEXT NOT NULL);
    """)
    return db


def metadata(db, key, default=None):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def setmeta(db, key, value):
    db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))


def jpeg_paths(root):
    """Parcours sans liste de tous les fichiers et sans suivre les liens."""
    stack = [Path(root)]
    while stack:
        with os.scandir(stack.pop()) as entries:
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file() and Path(entry.name).suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    yield Path(entry.path)


def index_images(db, source, config, progress=lambda **kw: None):
    source = Path(source).resolve()
    if not source.is_dir():
        raise ValueError("Source folder not found.")
    frozen = {"source": str(source), "config": asdict(config), "version": VERSION}
    previous = metadata(db, "definition")
    if previous is not None:
        # Compatibilité des projets créés avant la sélection des étapes.
        previous = {**previous, 'config':asdict(Config(**previous['config']))}
    if previous is not None and previous != frozen:
        raise ValueError("Settings are fixed in this project. Choose a new output folder to change them.")
    with db:
        setmeta(db, "definition", frozen)
        setmeta(db, "complete", False)
        db.execute("DELETE FROM issues WHERE code IN ('nom_non_reconnu','doublon','couche_avant_origine','fichier_modifie','fichier_absent','etape_exclue')")
    # Temporaire sur disque : le nombre de fichiers ne dimensionne pas la RAM.
    db.execute("CREATE TEMP TABLE seen(path TEXT PRIMARY KEY)")
    regex = re.compile(config.filename_regex, re.I)
    aliases = {k.casefold(): v for k, v in config.phase_aliases.items()}
    count = 0
    fatal = 0
    for path in jpeg_paths(source):
        count += 1
        rel = path.relative_to(source).as_posix()
        match = regex.fullmatch(rel)
        if match is None or match['phase'].casefold() not in aliases:
            db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ("nom_non_reconnu", str(path), "Image non indexée : vérifier le motif et les alias."))
        else:
            camera, phase, layer = match['camera'].casefold(), aliases[match['phase'].casefold()], int(match['layer'])
            if phase not in config.analysis_phases:
                db.execute('INSERT OR REPLACE INTO issues VALUES(?,?,?)',
                           ('etape_exclue',str(path),'Étape non sélectionnée pour cette analyse : '+phase))
                continue
            if layer < config.first_layer:
                fatal += 1
                db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ("couche_avant_origine", str(path), str(layer)))
                continue
            stat = path.stat()
            existing = db.execute("SELECT * FROM frames WHERE camera=? AND phase=? AND layer=?", (camera, phase, layer)).fetchone()
            if existing and existing['path'] != str(path):
                fatal += 1
                db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ("doublon", str(path), existing['path']))
            elif existing and (existing['size'], existing['mtime']) != (stat.st_size, stat.st_mtime_ns):
                fatal += 1
                db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ("fichier_modifie", str(path), "Créer un nouveau projet pour cette source modifiée."))
            else:
                db.execute("INSERT OR IGNORE INTO frames(path,camera,phase,layer,size,mtime) VALUES(?,?,?,?,?,?)",
                           (str(path), camera, phase, layer, stat.st_size, stat.st_mtime_ns))
            db.execute("INSERT OR IGNORE INTO seen VALUES(?)", (str(path),))
        if count % 250 == 0:
            db.commit()
            progress(stage="indexation", done=count, total=None)
    missing = db.execute("SELECT path FROM frames WHERE path NOT IN (SELECT path FROM seen)")
    for row in missing:
        fatal += 1
        db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ("fichier_absent", row['path'], "Fichier précédemment indexé absent."))
    db.execute("DROP TABLE seen")
    total = db.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
    db.commit()
    progress(stage="indexation", done=count, total=count)
    if fatal:
        raise ValueError(f"Ambiguous or changed import: {fatal} issue(s). See the status command for details.")
    if not total:
        raise ValueError("No recognized images. Adapt filename_regex to the actual relative paths.")
    return total


def pack(array):
    buf = io.BytesIO()
    np.save(buf, array, allow_pickle=False)
    return zlib.compress(buf.getvalue(), level=1)


def unpack(blob):
    return np.load(io.BytesIO(zlib.decompress(blob)), allow_pickle=False)


def gray_pixels(image, config):
    if image.mode in {"L", "RGB", "RGBA"}:
        if config.intensity_white_level != 255:
            raise ValueError("An 8-bit image requires intensity_white_level=255.")
        return np.asarray(image.convert('L'), dtype=np.float32)
    if image.mode in {"I;16", "I;16L", "I;16B", "I"}:
        if config.intensity_white_level <= 255:
            raise ValueError("16-bit image: set a fixed intensity_white_level (e.g. 65535).")
        raw = np.asarray(image, dtype=np.float32)
        if np.any(raw < 0) or np.any(raw > config.intensity_white_level):
            raise ValueError("Image intensities exceed the configured fixed scale.")
        return raw * (255.0/config.intensity_white_level)
    raise ValueError(f"Unsupported image mode: {image.mode}.")


def extract(path, config, camera):
    with Image.open(path) as image:
        width, height = image.size
        box = config.roi_by_camera.get(camera, [0, 0, width, height])
        if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
            raise ValueError("The ROI is outside the image dimensions.")
        # Pas de sous-échantillonnage : les statistiques utilisent tous les pixels de la ROI.
        pixels = gray_pixels(image.crop(tuple(box)), config)
    h, w = pixels.shape
    b = config.tile_px
    rows, cols = math.ceil(h/b), math.ceil(w/b)
    padded = np.pad(pixels, ((0, rows*b-h), (0, cols*b-w)), mode="edge")
    blocks = padded.reshape(rows, b, cols, b)
    mean = blocks.mean(axis=(1, 3), dtype=np.float32)
    std = blocks.std(axis=(1, 3), dtype=np.float32)
    high = blocks.max(axis=(1, 3)).astype(np.float32)
    low = blocks.min(axis=(1, 3)).astype(np.float32)
    light = float(pixels.mean(dtype=np.float64))
    features = np.stack((mean-light, std, high-light, low-light)).astype(np.float32)
    geometry = {"width": width, "height": height, "roi": list(box), "tile": b}
    return features, light, geometry


def calibrate_index(db, config, progress=lambda **kw: None, stop=lambda: False):
    """20 premières photos par caméra/étape de ce job uniquement, sans labels."""
    existing = metadata(db, 'gray_calibration')
    if existing is not None:
        return existing
    channels = {}; done = 0; started = time.monotonic()
    series = db.execute('SELECT camera,phase,COUNT(*) n FROM frames GROUP BY camera,phase').fetchall()
    total = sum(min(20, r['n']) for r in series)
    for series_row in series:
        camera, phase = series_row['camera'], series_row['phase']
        lights, ids, positions = [], [], []
        for frame in db.execute('SELECT * FROM frames WHERE camera=? AND phase=? ORDER BY layer LIMIT 20', (camera, phase)):
            if stop():
                raise InterruptedError('Calibration interrompue.')
            try:
                if frame['features'] is not None:
                    level = frame['luminance']
                else:
                    with Image.open(frame['path']) as photo:
                        roi=config.roi_by_camera.get(camera,[0,0,photo.width,photo.height])
                        if not (0<=roi[0]<roi[2]<=photo.width and 0<=roi[1]<roi[3]<=photo.height):
                            raise ValueError('Invalid crop.')
                        level=float(gray_pixels(photo.crop(tuple(roi)),config).mean(dtype=np.float64))
                lights.append(level); ids.append(frame['id']); positions.append(frame['layer'])
            except (OSError, ValueError, Image.DecompressionBombError):
                pass  # L'analyse consignera l'image illisible dans sa couverture.
            done += 1
            progress(stage='gris', done=done, total=total, eta=(time.monotonic()-started)/done*(total-done))
        channels[camera+'/'+phase] = {'mean_gray':float(np.mean(lights)) if lights else None,
                                    'std_gray':float(np.std(lights)) if lights else 0, 'sample_ids':ids,
                                    'last_position':max(positions) if positions else 0}
    n = sum(len(v['sample_ids']) for v in channels.values())
    result = {'channels':channels, 'sample_images':n,
              'mean_gray':sum(v['mean_gray']*len(v['sample_ids']) for v in channels.values() if v['sample_ids'])/n if n else None,
              'note':'Gray level from the first 20 images per camera and stage of this job. These images are not assumed to be defect-free.'}
    with db:
        setmeta(db, 'gray_calibration', result)
    return result


def components(mask, scores, geometry):
    """Regroupement 8-connexe sur la grille, jamais sur tous les pixels."""
    cells = set((int(r), int(c)) for r, c in zip(*np.nonzero(mask)))
    tile = geometry['tile']
    x0, y0, x1, y1 = geometry['roi']
    while cells:
        first = min(cells)
        cells.remove(first)
        todo = [first]
        rmin = rmax = first[0]
        cmin = cmax = first[1]
        score = 0.0
        while todo:
            r, c = todo.pop()
            rmin, rmax, cmin, cmax = min(rmin, r), max(rmax, r), min(cmin, c), max(cmax, c)
            score = max(score, float(scores[r, c]))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    neighbor = (r+dr, c+dc)
                    if neighbor in cells:
                        cells.remove(neighbor)
                        todo.append(neighbor)
        yield [x0+cmin*tile, y0+rmin*tile, min(x1, x0+(cmax+1)*tile), min(y1, y0+(rmax+1)*tile)], score


class Detector:
    def __init__(self, config, calibration=None):
        self.calibration = calibration
        self.c = Config(**asdict(config))
        if calibration:
            # La calibration initiale fixe le gris de départ, jamais un seuil
            # tiré d'images qui pourraient elles-mêmes contenir un incident.
            self.c.global_jump_gray = config.min_change_gray
            self.c.drift_gray = config.min_change_gray*1.5
        self.history = deque(maxlen=config.history)
        self.lights = deque(maxlen=config.history)
        self.previous_layer = None
        self.geometry = None
        self.baseline = None
        self.base_light = None
        self.ewma = None
        self.ewma_light = None

    def process(self, layer, values, light, geometry):
        c = self.c
        discontinuity = self.previous_layer is not None and (
            layer != self.previous_layer + 1 or geometry != self.geometry)
        if discontinuity:
            self.__init__(c, self.calibration)
        self.previous_layer, self.geometry = layer, geometry
        events = []
        ready = len(self.history) >= c.warmup
        if ready:
            history = np.stack(self.history)
            median = np.median(history, axis=0)
            mad = 1.4826 * np.median(np.abs(history-median), axis=0)
            floor = np.array([c.min_change_gray, c.min_texture_change,
                              2*c.min_change_gray, 2*c.min_change_gray], np.float32)[:, None, None]
            threshold = np.maximum(c.sigma*mad, floor)
            score = np.max(np.abs(values-median)/threshold, axis=0)
            for box, severity in components(score >= 1, score, geometry):
                events.append(("changement_local", box, severity))
            if self.baseline is None:
                # Référence interne de départ ; elle n'est pas déclarée saine.
                self.baseline = median[0].copy()
                self.base_light = float(np.median(self.lights))
                self.ewma = self.baseline.copy()
                self.ewma_light = self.base_light
                self.drift_threshold = np.maximum(c.drift_gray, c.sigma*mad[0])
            a = c.drift_alpha
            self.ewma = (1-a)*self.ewma + a*values[0]
            self.ewma_light = (1-a)*self.ewma_light + a*light
            drift = np.abs(self.ewma-self.baseline)/self.drift_threshold
            for box, severity in components((drift >= 1) & (score < 1), drift, geometry):
                events.append(("derive_locale", box, severity))
            jump = abs(light-float(np.median(self.lights)))/c.global_jump_gray
            global_drift = abs(self.ewma_light-self.base_light)/c.drift_gray
            if jump >= 1:
                events.append(("luminosite_globale", geometry['roi'], jump))
            elif global_drift >= 1:
                events.append(("derive_globale", geometry['roi'], global_drift))
            if self.calibration and self.calibration['mean_gray'] is not None and layer>self.calibration.get('last_position',-math.inf):
                deviation = abs(light-self.calibration['mean_gray'])/c.drift_gray
                if deviation >= 1 and jump < 1 and global_drift < 1:
                    events.append(('niveau_gris', geometry['roi'], deviation))
        self.history.append(values)
        self.lights.append(light)
        return events, ready, discontinuity


def overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def add_event(db, frame, kind, box, score):
    # Même caméra/étape/type, couches consécutives, recouvrement spatial.
    active = db.execute("SELECT * FROM events WHERE camera=? AND phase=? AND kind=? AND end_layer=? ORDER BY id",
                        (frame['camera'], frame['phase'], kind, frame['layer']-1)).fetchall()
    match = next((r for r in active if overlap(json.loads(r['box']), box)), None)
    if match:
        if match['status'] != 'a_examiner':
            db.execute("INSERT INTO decisions(event_id,status,comment) VALUES(?,?,?)",
                       (match['id'], 'a_examiner', 'Événement prolongé après reprise de l’analyse.'))
        peak_frame = frame['id'] if score > match['score'] else match['peak_frame']
        peak_box = json.dumps(box) if score > match['score'] else match['box']
        db.execute("UPDATE events SET end_layer=?,peak_frame=?,box=?,score=?,status='a_examiner' WHERE id=?",
                   (frame['layer'], peak_frame, peak_box, max(score, match['score']), match['id']))
    else:
        db.execute("INSERT INTO events(camera,phase,kind,start_layer,end_layer,peak_frame,box,score) VALUES(?,?,?,?,?,?,?,?)",
                   (frame['camera'], frame['phase'], kind, frame['layer'], frame['layer'], frame['id'], json.dumps(box), score))


def analyze(source, project, config, progress=lambda **kw: None, stop=lambda: False, calibration_only=False):
    config.validate()
    source, project = Path(source).resolve(), Path(project).resolve()
    if source == project or source in project.parents:
        raise ValueError("Store results outside the source image folder.")
    db = connect(project)
    frames = None
    try:
        total = index_images(db, source, config, progress)
        try:
            calibration = calibrate_index(db, config, progress, stop)
        except InterruptedError:
            return summary(db)
        if calibration_only:
            return summary(db)
        started, done, cached = time.monotonic(), 0, 0
        evaluated = flagged = detections = warmup = gaps = 0
        stream, detector = None, None
        frames = db.execute("SELECT * FROM frames ORDER BY camera,phase,layer")
        for frame in frames:
            if stop():
                break
            key = (frame['camera'], frame['phase'])
            if key != stream:
                stream = key
                profile = calibration['channels'][key[0]+'/'+key[1]]
                detector = Detector(config, profile)
            if frame['error']:
                detector = Detector(config, profile)
                done += 1
                continue
            try:
                if frame['features'] is not None:
                    values, light, geometry = unpack(frame['features']), frame['luminance'], json.loads(frame['geometry'])
                    cached += 1
                else:
                    stat = Path(frame['path']).stat()
                    if (stat.st_size, stat.st_mtime_ns) != (frame['size'], frame['mtime']):
                        raise ValueError("File changed after indexing.")
                    values, light, geometry = extract(frame['path'], config, frame['camera'])
                events, ready, gap = detector.process(frame['layer'], values, light, geometry)
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                with db:
                    db.execute("UPDATE frames SET error=? WHERE id=?", (str(error), frame['id']))
                    db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ('image_non_analysee', frame['path'], str(error)))
                detector = Detector(config, profile)
            else:
                evaluated += int(ready); warmup += int(not ready); gaps += int(gap)
                flagged += int(bool(events)); detections += len(events)
                if frame['features'] is None:
                    # Cache, résultats et couverture sont validés dans une seule transaction.
                    with db:
                        db.execute("UPDATE frames SET features=?,geometry=?,luminance=? WHERE id=?",
                                   (pack(values), json.dumps(geometry), light, frame['id']))
                        for kind, box, severity in events:
                            add_event(db, frame, kind, box, severity)
                        if not ready:
                            db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ('initialisation', frame['path'], 'Historique insuffisant : pas de détection temporelle.'))
                        if gap:
                            db.execute("INSERT OR REPLACE INTO issues VALUES(?,?,?)", ('discontinuite', frame['path'], 'Couche manquante ou dimensions/ROI modifiées : historique réinitialisé.'))
            done += 1
            elapsed = time.monotonic()-started
            progress(stage="analyse", done=done, total=total, cached=cached,
                     elapsed=elapsed, eta=elapsed/done*(total-done), layer=frame['layer'],
                     camera=frame['camera'], phase=frame['phase'])
        else:
            with db:
                setmeta(db, "complete", True)
                setmeta(db, 'analysis_report', {'images':total, 'measured':db.execute('SELECT COUNT(*) FROM frames WHERE features IS NOT NULL').fetchone()[0],
                    'evaluated':evaluated, 'flagged_images':flagged, 'detections':detections, 'warmup_images':warmup, 'gaps':gaps,
                    'errors':[dict(r) for r in db.execute('SELECT id,error FROM frames WHERE error IS NOT NULL')],
                    'calibration_gray':calibration['mean_gray'], 'seconds':time.monotonic()-started,
                    'config':asdict(config), 'note':'Single-job analysis, per camera and stage. No annotations or other jobs used.'})
        return summary(db)
    finally:
        if frames is not None:
            frames.close()
        db.close()


def summary(db):
    counts = dict(db.execute("SELECT status,COUNT(*) FROM events GROUP BY status").fetchall())
    return {"parcours_termine": metadata(db, "complete", False),
            "images_indexees": db.execute("SELECT COUNT(*) FROM frames").fetchone()[0],
            "images_mesurees": db.execute("SELECT COUNT(*) FROM frames WHERE features IS NOT NULL").fetchone()[0],
            "images_en_erreur": db.execute("SELECT COUNT(*) FROM frames WHERE error IS NOT NULL").fetchone()[0],
            "indications": counts,
            "observations_import_couverture": dict(db.execute("SELECT code,COUNT(*) FROM issues GROUP BY code").fetchall()),
            "series": [dict(r) for r in db.execute("SELECT camera,phase,COUNT(*) images,MIN(layer) premiere,MAX(layer) derniere FROM frames GROUP BY camera,phase")]}


def save_decisions(project, path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    db = connect(project)
    try:
        expected = hashlib.sha256(json.dumps(metadata(db, 'definition'), sort_keys=True).encode()).hexdigest()
        if payload.get('project_key') != expected:
            raise ValueError("Decisions belong to another project.")
        with db:
            for item in payload['decisions']:
                if item['status'] not in {'a_examiner', 'retenue', 'ecartee'}:
                    raise ValueError("Unknown review status.")
                if not isinstance(item.get('comment', ''), str):
                    raise ValueError("The comment must be text.")
                row = db.execute("SELECT * FROM events WHERE id=?", (item['id'],)).fetchone()
                if not row:
                    raise ValueError("Unknown indication.")
                if item.get('snapshot') != event_fingerprint(row):
                    raise ValueError("The indication has changed since this page was created. Regenerate the review.")
                db.execute("UPDATE events SET status=?,comment=? WHERE id=?", (item['status'], item.get('comment', ''), item['id']))
                db.execute("INSERT INTO decisions(event_id,status,comment) VALUES(?,?,?)", (item['id'], item['status'], item.get('comment', '')))
    finally:
        db.close()


def event_fingerprint(row):
    data = [row[k] for k in ('id', 'start_layer', 'end_layer', 'peak_frame', 'box', 'score')]
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("analyze", help="Indexer, analyser ou reprendre un projet")
    run.add_argument("source", type=Path)
    run.add_argument("project", type=Path)
    run.add_argument("--config", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("project", type=Path)
    report = commands.add_parser("review", help="Créer une page locale de revue des indications")
    report.add_argument("project", type=Path)
    report.add_argument("--offset", type=int, default=0)
    report.add_argument("--limit", type=int, default=100)
    report.add_argument("--retained-only", action="store_true")
    decisions = commands.add_parser("decisions", help="Enregistrer les décisions exportées par la page de revue")
    decisions.add_argument("project", type=Path)
    decisions.add_argument("json_file", type=Path)
    args = parser.parse_args()
    last = [0.0]

    def progress(**p):
        now = time.monotonic()
        if now-last[0] < .25 and p.get('done') != p.get('total'):
            return
        last[0] = now
        total = p.get('total')
        fraction = p['done']/max(total, 1) if total else 0
        bar = '#' * int(25*fraction) + '-' * (25-int(25*fraction))
        eta = f" | reste estimé {p['eta']/60:.1f} min" if 'eta' in p else ''
        print(f"\r{p['stage']} [{bar}] {p['done']}/{total or '?'}{eta}     ", end='', flush=True)

    try:
        if args.command == "analyze":
            config = Config(**json.loads(args.config.read_text(encoding="utf-8-sig")))
            result = analyze(args.source, args.project, config, progress)
            print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "status":
            db = connect(args.project)
            try:
                print(json.dumps(summary(db), ensure_ascii=False, indent=2))
                for row in db.execute("SELECT * FROM issues WHERE code!='initialisation' LIMIT 30"):
                    print(dict(row))
            finally:
                db.close()
        elif args.command == "decisions":
            save_decisions(args.project, args.json_file)
            print("Décisions enregistrées.")
        elif args.command == "review":
            from review import create_review
            print(create_review(args.project, args.offset, args.limit, args.retained_only))
    except KeyboardInterrupt:
        print("\nInterrompu. Relancer la même commande pour reprendre.")
        return 130
    except (ValueError, OSError, sqlite3.Error) as error:
        print(f"\nErreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
