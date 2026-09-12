"""Cadrage commun des comparaisons, exprimé dans les pixels d'origine."""
import math

CONTEXTS = {'tight': (128, .4), 'standard': (256, .8), 'wide': (512, 1.5)}


def context_box(box, width, height, mode='standard'):
    """Entoure une indication de contexte sans sortir de l'image.

    Le même rectangle doit être réutilisé pour N−1, N et N+1.
    Aucun recalage ou ajustement de luminosité n'est réalisé ici.
    """
    if mode not in CONTEXTS:
        raise ValueError('Cadrage inconnu.')
    if (len(box)!=4 or not all(math.isfinite(v) for v in box)
            or not 0 <= box[0] < box[2] <= width
            or not 0 <= box[1] < box[3] <= height):
        raise ValueError('Zone en dehors de l’image.')
    minimum, padding = CONTEXTS[mode]
    span = max(box[2]-box[0], box[3]-box[1])
    side = max(minimum, math.ceil(span*(1+2*padding)))
    crop_width, crop_height = min(width,side), min(height,side)
    left = max(0,min(width-crop_width, math.floor((box[0]+box[2]-crop_width)/2)))
    top = max(0,min(height-crop_height, math.floor((box[1]+box[3]-crop_height)/2)))
    return [left,top,left+crop_width,top+crop_height]
