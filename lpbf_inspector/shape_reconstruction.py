"""Sections photographiques approximatives, sans géométrie CAO ni annotations.

Contraste local à résolution bornée, fermeture de petits interstices, suppression
des îlots minuscules. Les petites zones entièrement entourées sont comblées.
Le réglage dépend seulement de la photo courante ; il ne modifie pas la détection.
"""
from functools import lru_cache
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from inspector import Config, gray_pixels

MAX_EDGE = 512
SHAPE_VERSION = 'texture-sections-1'


def contrast_value(value):
    value = float(value)
    if not math.isfinite(value) or not 1 <= value <= 8:
        raise ValueError('Reconstruction contrast must be between 1 and 8.')
    return value


def components(mask):
    """Composantes 4-connexes par segments de lignes, sans dépendance SciPy."""
    runs, parents, previous = [], [], []
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for y, row in enumerate(mask):
        edges = np.flatnonzero(np.diff(np.pad(row.astype(np.int8), (1, 1))))
        current, j = [], 0
        for x0, x1 in zip(edges[::2], edges[1::2]):
            i = len(runs)
            runs.append((y, int(x0), int(x1))); parents.append(i); current.append(i)
            while j < len(previous) and runs[previous[j]][2] <= x0: j += 1
            k = j
            while k < len(previous) and runs[previous[k]][1] < x1:
                parents[root(previous[k])] = root(i)
                k += 1
        previous = current
    sizes, border, labels = {}, set(), []
    h, w = mask.shape
    for i, (y, x0, x1) in enumerate(runs):
        label = root(i); labels.append(label)
        sizes[label] = sizes.get(label, 0) + x1 - x0
        if y in (0, h-1) or x0 == 0 or x1 == w: border.add(label)
    return runs, labels, sizes, border


def section_mask(image, contrast=3):
    """Retourne un masque L et ses mesures à la résolution d'aperçu."""
    contrast = contrast_value(contrast)
    im = image.convert('L').copy(); im.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    a = np.asarray(im, dtype=np.float32)
    high = np.abs(a - np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32))
    energy = np.asarray(Image.fromarray(np.uint8(np.rint(high))).filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32)
    base = float(np.median(energy)); mad = float(1.4826*np.median(np.abs(energy-base)))
    threshold = max(2., base + contrast * max(mad, .5))
    binary = Image.fromarray(np.uint8(energy > threshold)*255)
    mask = np.array(binary.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MedianFilter(3))) > 0
    runs, labels, sizes, _ = components(mask)
    minimum = max(6, int(mask.size * .000045))
    for (y, x0, x1), label in zip(runs, labels):
        if sizes[label] < minimum: mask[y, x0:x1] = False
    # Petits trous de reflet : pas de remplissage de grandes cavités visibles.
    runs, labels, sizes, border = components(~mask)
    for (y, x0, x1), label in zip(runs, labels):
        if label not in border and sizes[label] <= max(16, int(mask.size*.0008)):
            mask[y, x0:x1] = True
    return Image.fromarray(np.uint8(mask)*255), {'threshold': round(threshold, 2), 'coverage_percent': round(float(mask.mean()*100), 2)}


def shape_preview(path, white, crop, contrast=3):
    p = Path(path); stat = p.stat()
    return _cached_preview(str(p), stat.st_mtime_ns, stat.st_size, white, tuple(crop), contrast_value(contrast), SHAPE_VERSION)


def part_overlap(path, white, box, contrast=3):
    """Fraction of an event box covered by the extracted post-melting section."""
    p = Path(path); stat = p.stat()
    mask_bytes, width, height = _cached_mask(str(p), stat.st_mtime_ns, stat.st_size, white, contrast_value(contrast), SHAPE_VERSION)
    mask = np.frombuffer(mask_bytes, dtype=np.bool_).reshape((height, width))
    with Image.open(path) as original:
        scale_x, scale_y = width / original.width, height / original.height
    x0 = max(0, min(width, math.floor(float(box[0]) * scale_x)))
    y0 = max(0, min(height, math.floor(float(box[1]) * scale_y)))
    x1 = max(0, min(width, math.ceil(float(box[2]) * scale_x)))
    y1 = max(0, min(height, math.ceil(float(box[3]) * scale_y)))
    if x0 >= x1 or y0 >= y1:
        return 0.0
    return round(float(mask[y0:y1, x0:x1].mean()), 3)


@lru_cache(maxsize=160)
def _cached_mask(path, mtime, size, white, contrast, version):
    with Image.open(path) as original:
        im = Image.fromarray(np.uint8(np.rint(gray_pixels(original, Config(intensity_white_level=white)))))
    mask, _ = section_mask(im, contrast)
    array = np.asarray(mask) > 0
    return array.tobytes(), mask.width, mask.height


@lru_cache(maxsize=160)
def _cached_preview(path, mtime, size, white, crop, contrast, version):
    with Image.open(path) as original:
        if not 0 <= crop[0] < crop[2] <= original.width or not 0 <= crop[1] < crop[3] <= original.height:
            raise ValueError('Invalid reconstruction crop.')
        # Même normalisation 8/16 bits que l'analyse, puis travail sur l'image
        # entière pour ne pas changer le seuil lorsque l'utilisateur recadre.
        im = Image.fromarray(np.uint8(np.rint(gray_pixels(original, Config(intensity_white_level=white)))))
        width, height = im.size
    mask, stats = section_mask(im, contrast)
    coords = (round(crop[0]*mask.width/width), round(crop[1]*mask.height/height),
              round(crop[2]*mask.width/width), round(crop[3]*mask.height/height))
    if coords[0] >= coords[2] or coords[1] >= coords[3]:
        raise ValueError('Crop too small for the reconstruction preview.')
    mask = mask.crop(coords)
    rgba = Image.new('RGBA', mask.size, (36, 217, 205, 0)); rgba.putalpha(mask)
    output = io.BytesIO(); rgba.save(output, format='PNG')
    stats = dict(stats, coverage_percent=round(float((np.asarray(mask)>0).mean()*100), 2), width=mask.width, height=mask.height)
    return output.getvalue(), stats
