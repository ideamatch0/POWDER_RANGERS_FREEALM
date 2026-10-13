"""User-defined normalized plate outlines; no CAD or machine-specific model."""
from functools import lru_cache
import math
import numpy as np
from PIL import Image,ImageDraw


def validate_outlines(outlines):
    if not isinstance(outlines,dict) or len(outlines)>32:
        raise ValueError('Build plate outlines must map camera names to polygons.')
    normalized={}
    for camera,points in outlines.items():
        if not isinstance(camera,str) or not camera or len(camera)>120 or camera.casefold() in normalized:
            raise ValueError('Each build plate outline needs a unique camera name.')
        if not isinstance(points,(list,tuple)) or not 3<=len(points)<=64:
            raise ValueError('Click between 3 and 64 points around the build plate.')
        for point in points:
            if not isinstance(point,(list,tuple)) or len(point)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in point):
                raise ValueError('Build plate points must be normalized coordinates between 0 and 1.')
        if len(set(map(tuple,points)))!=len(points):
            raise ValueError('Build plate points must be distinct.')
        area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2
        if area<1e-6:raise ValueError('The build plate outline has no usable area.')
        def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        def intersects(a,b,c,d):
            values=(orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b))
            if values[0]*values[1]<0 and values[2]*values[3]<0:return True
            for value,p,q,r in ((values[0],a,b,c),(values[1],a,b,d),(values[2],c,d,a),(values[3],c,d,b)):
                if abs(value)<1e-12 and min(p[0],q[0])<=r[0]<=max(p[0],q[0]) and min(p[1],q[1])<=r[1]<=max(p[1],q[1]):return True
            return False
        for i in range(len(points)):
            for j in range(i+1,len(points)):
                if j==i+1 or (i==0 and j==len(points)-1):continue
                if intersects(points[i],points[(i+1)%len(points)],points[j],points[(j+1)%len(points)]):
                    raise ValueError('The build plate outline crosses itself. Click points in contour order.')
        normalized[camera.casefold()]=[list(p) for p in points]
    return normalized


@lru_cache(maxsize=16)
def plate_mask(width,height,points):
    image=Image.new('1',(width,height))
    ImageDraw.Draw(image).polygon([(x*width,y*height) for x,y in points],fill=1)
    mask=np.asarray(image,dtype=bool);mask.setflags(write=False)
    return mask


def plate_bounds(width,height,points):
    return [max(0,math.floor(min(p[0] for p in points)*width)),
            max(0,math.floor(min(p[1] for p in points)*height)),
            min(width,math.ceil(max(p[0] for p in points)*width)+1),
            min(height,math.ceil(max(p[1] for p in points)*height)+1)]
