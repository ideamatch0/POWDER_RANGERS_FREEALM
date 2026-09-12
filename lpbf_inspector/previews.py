"""Image previews shared by API and reporting, independent of application state."""
from functools import lru_cache
import io
from pathlib import Path
import numpy as np
from PIL import Image
from inspector import Config,gray_pixels
from source_integrity import file_stamp,verify_source


def preview(path,white,crop=None,edge=1400):
    path=str(Path(path).resolve());stamp=tuple(file_stamp(path))
    return _preview(path,white,tuple(crop) if crop is not None else None,edge,stamp)


@lru_cache(maxsize=220)
def _preview(path,white,crop,edge,stamp):
    with Image.open(path) as original:
        if crop:
            if not 0<=crop[0]<crop[2]<=original.width or not 0<=crop[1]<crop[3]<=original.height:
                raise ValueError('Image dimensions do not allow the matching crop.')
            original=original.crop(crop)
        pixels=gray_pixels(original,Config(intensity_white_level=white))
    image=Image.fromarray(np.rint(pixels).astype(np.uint8));image.thumbnail((edge,edge))
    output=io.BytesIO();image.save(output,format='JPEG',quality=90)
    verify_source(path,stamp)
    return output.getvalue()


preview.cache_clear=_preview.cache_clear
preview.cache_info=_preview.cache_info
