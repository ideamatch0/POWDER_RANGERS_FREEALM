"""Détecteur spatial classique. L'inférence ne reçoit jamais d'annotations."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image

VERSION = 'aalto-spatial-2'
FEATURE_VERSION = 'aalto-spatial-1'
THRESHOLDS = (4, 7, 11, 17, 25)
LINE_THRESHOLDS = (.6, 1., 1.5, 2.5)


def percentile90(values):
    """Quantile linéaire équivalent à percentile(..., 90), sans préparation générique."""
    position=(len(values)-1)*.9
    lower=int(position);upper=min(lower+1,len(values)-1)
    ordered=np.partition(values,(lower,upper))
    a,b=float(ordered[lower]),float(ordered[upper])
    return a+(b-a)*(position-lower)


def opencv():
    try:
        import cv2
    except ImportError:
        local = Path(__file__).resolve().parent / '.deps'
        if local.is_dir():
            sys.path.insert(0, str(local))
        try:
            import cv2
        except ImportError as error:
            raise ValueError('Installer requirements-aalto.txt pour la détection Aalto.') from error
    cv2.setNumThreads(1)
    return cv2


def candidate_regions(path):
    """Retourne des candidats à partir des seuls pixels, sans accès aux XML.

    Le polygone retire le châssis de cette caméra EOS, indépendamment des
    rectangles des chercheurs. Il devra être adapté sur une autre caméra.
    """
    cv = opencv()
    with Image.open(path) as image:
        width, height = image.size
        small = np.asarray(image.convert('L').resize((640, 512), Image.Resampling.BOX)).copy()
    smooth = cv.GaussianBlur(small.astype(np.float32), (0, 0), .7)
    background = cv.GaussianBlur(smooth, (0, 0), 6)
    residual = smooth - background
    roi = np.zeros(small.shape, np.uint8)
    cv.fillPoly(roi, [np.array([[116, 82], [639, 82], [639, 447], [84, 447]], np.int32)], 1)
    # Stries horizontales : lisser le long de la strie, comparer au voisinage vertical.
    along = cv.blur(smooth, (17, 1))
    band = np.abs(along - cv.GaussianBlur(along, (1, 0), 0, sigmaY=4))
    groups = []
    for threshold in THRESHOLDS:
        candidates = []
        for kind, response in [('sombre', -residual), ('clair', residual), ('strie', band)]:
            mask = ((response >= threshold) & (roi != 0)).astype(np.uint8)
            kernel = np.ones((2, 9) if kind == 'strie' else (3, 3), np.uint8)
            mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel)
            mask *= roi
            count, labels, stats, _ = cv.connectedComponentsWithStats(mask, 8)
            for index in range(1, count):
                x, y, w, h, area = map(int, stats[index])
                if area < 6 or w < 2 or h < 2 or w*h > 35000:
                    continue
                aspect = max(w/h, h/w)
                if kind == 'strie' and (w < 35 or w/h < 4):
                    continue
                if kind == 'clair' and aspect < 2:
                    continue
                values = response[y:y+h, x:x+w][labels[y:y+h, x:x+w] == index]
                box = [max(0, int((x-1)*width/640)), max(0, int((y-1)*height/512)),
                       min(width, int((x+w+1)*width/640)), min(height, int((y+h+1)*height/512))]
                candidates.append({'box': box, 'score': round(percentile90(values), 3),
                                   'kind': kind, 'area': area, 'aspect': round(aspect, 3)})
        groups.append(candidates)
    return {'width': width, 'height': height, 'groups': groups, 'lines': line_candidates(path)}


def line_candidates(path):
    """Contrastes faibles, intégrés horizontalement, pour les stries de quelques pixels."""
    cv=opencv()
    with Image.open(path) as image:
        width,height=image.size
        pixels=np.asarray(image.convert('L').resize((640,512),Image.Resampling.BOX)).astype(np.float32)
    along=cv.blur(pixels,(41,1))
    response=np.abs(along-cv.GaussianBlur(along,(1,0),0,sigmaY=2))
    roi=np.zeros(pixels.shape,np.uint8)
    cv.fillPoly(roi,[np.array([[116,82],[639,82],[639,447],[84,447]],np.int32)],1)
    groups=[]
    for threshold in LINE_THRESHOLDS:
        mask=((response>=threshold)&(roi!=0)).astype(np.uint8)
        mask=cv.morphologyEx(mask,cv.MORPH_CLOSE,np.ones((1,15),np.uint8))*roi
        count,labels,stats,_=cv.connectedComponentsWithStats(mask,8)
        rows=[]
        candidates=np.flatnonzero((stats[:,2]>=40)&(stats[:,3]<=18)&(stats[:,2]>=8*stats[:,3]))
        for index in candidates:
            if index==0:continue
            x,y,w,h,area=map(int,stats[index])
            values=response[y:y+h,x:x+w][labels[y:y+h,x:x+w]==index]
            rows.append({'box':[max(0,int(x*width/640)),max(0,int((y-1)*height/512)),
                                min(width,int((x+w)*width/640)),min(height,int((y+h+1)*height/512))],
                         'score':round(percentile90(values),3),'kind':'strie','area':area,'aspect':w/h})
        groups.append(rows)
    return groups


def iou(a, b):
    overlap = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - overlap
    return overlap / union if union > 0 else 0.


def iou_matrix(a,b):
    if not len(a) or not len(b):return np.zeros((len(a),len(b)),np.float32)
    a=np.asarray(a,np.float32);b=np.asarray(b,np.float32)
    low=np.maximum(a[:,None,:2],b[None,:,:2]);high=np.minimum(a[:,None,2:],b[None,:,2:])
    overlap=np.maximum(0,high-low).prod(axis=2)
    area_a=(a[:,2:]-a[:,:2]).prod(axis=1);area_b=(b[:,2:]-b[:,:2]).prod(axis=1)
    union=area_a[:,None]+area_b[None,:]-overlap
    return np.divide(overlap,union,out=np.zeros_like(overlap),where=union>0)


def select_regions(candidates, config):
    rows=[]
    if config['threshold'] is not None:
        index=THRESHOLDS.index(config['threshold'])
        rows=[r for r in candidates['groups'][index] if r['area']>=config['min_area'] and r['kind']=='sombre']
    if config.get('line_threshold') is not None:
        rows+=candidates['lines'][LINE_THRESHOLDS.index(config['line_threshold'])]
    kept=[]
    ordered=sorted(rows,key=lambda r:(-r['score'],r['box']))
    boxes=[r['box'] for r in ordered]
    overlaps=iou_matrix(boxes,boxes) if len(boxes)<1000 else None
    blocked=np.zeros(len(boxes),bool)
    for index,row in enumerate(ordered):
        if blocked[index]:continue
        kept.append({k:row[k] for k in ('box','score','kind')})
        blocked|=(overlaps[index] if overlaps is not None else iou_matrix([row['box']],boxes)[0])>=.35
    return kept


def detect_image(path, profile):
    """API d'inférence réutilisable : une photo + des seuils, aucun label."""
    if profile.get('version') != VERSION:
        raise ValueError('Version de profil incompatible.')
    return select_regions(candidate_regions(path), profile['config'])


if __name__ == '__main__':
    import argparse
    import json
    parser=argparse.ArgumentParser(description='Détecter des indications dans une photo brute, sans annotations.')
    parser.add_argument('image',type=Path)
    parser.add_argument('--profile',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    profile=json.loads(args.profile.read_text(encoding='utf-8'))
    data={'image':str(args.image),'version':VERSION,'predictions':detect_image(args.image,profile)}
    text=json.dumps(data,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(text,encoding='utf-8')
    else:print(text)
