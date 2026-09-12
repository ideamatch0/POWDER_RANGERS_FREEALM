"""Vues 3D fixes pour un rapport autonome, sans navigateur ni GPU.

La projection orthographique et la palette correspondent à la vue WebGL.
La géométrie cyan est extraite par le même algorithme photographique.
"""
import io
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shape_reconstruction import shape_preview
from previews import preview

PALETTE = [(255,223,98),(255,181,71),(255,139,62),(255,96,57),(255,48,71)]


def score_color(score):
    return PALETTE[min(4,max(0,int(float(score)//20)))]


def sampled_frames(frames, limit):
    return [frames[i] for i in sorted(set(np.linspace(0,len(frames)-1,min(len(frames),limit)).round().astype(int)))]


class Projection:
    def __init__(self, scene, top=False, size=(1200,850)):
        self.scene=scene;self.size=size;self.yaw=0 if top else -.35;self.pitch=math.pi/2 if top else .55
        self.first=scene['frames'][0]['position'];self.last=scene['frames'][-1]['position']
        points=np.array([self.raw(u,v,z) for z in (self.first,self.last) for u,v in ((0,0),(1,0),(1,1),(0,1))])
        low,high=points.min(axis=0),points.max(axis=0)
        self.scale=min((size[0]-170)/max(high[0]-low[0],.01),(size[1]-155)/max(high[1]-low[1],.01))
        self.center=(low+high)/2

    def raw(self,u,v,z):
        s=self.scene;maximum=max(s['width'],s['height'])
        x=(u-.5)*2*s['width']/maximum;y=(.5-v)*2*s['height']/maximum
        height=(z-self.first)/(self.last-self.first)*1.4-.7 if self.last!=self.first else 0
        return np.array([math.cos(self.yaw)*x-math.sin(self.yaw)*y,
                         -(math.sin(self.pitch)*(math.sin(self.yaw)*x+math.cos(self.yaw)*y)+math.cos(self.pitch)*height)])

    def point(self,u,v,z):
        p=(self.raw(u,v,z)-self.center)*self.scale+np.array(self.size)/2
        return tuple(float(x) for x in p)

    def box(self,box,z):
        s=self.scene;c=s['crop']
        u0,u1=(box[0]-c[0])/s['width'],(box[2]-c[0])/s['width']
        v0,v1=(box[1]-c[1])/s['height'],(box[3]-c[1])/s['height']
        return [self.point(u,v,z) for u,v in ((u0,v0),(u1,v0),(u1,v1),(u0,v1))]

    def plane(self,canvas,texture,z,opacity):
        origin=np.array(self.point(0,0,z));u=np.array(self.point(1,0,z))-origin;v=np.array(self.point(0,1,z))-origin
        corners=np.array([origin,origin+u,origin+v,origin+u+v])
        lo=np.maximum(np.floor(corners.min(axis=0)).astype(int),0)
        hi=np.minimum(np.ceil(corners.max(axis=0)).astype(int),np.array(canvas.size))
        if np.any(hi<=lo):return
        matrix=np.diag(texture.size)@np.linalg.inv(np.column_stack((u,v)))
        translation=matrix@(lo-origin)
        coefficients=(matrix[0,0],matrix[0,1],translation[0],matrix[1,0],matrix[1,1],translation[1])
        texture=texture.copy()
        texture.putalpha(texture.getchannel('A').point(lambda a:round(a*opacity)))
        tile=texture.transform(tuple(hi-lo),Image.Transform.AFFINE,coefficients,Image.Resampling.BILINEAR)
        canvas.alpha_composite(tile,tuple(lo))


def render_volume(scene,white,contrast=3,planes=64,progress=lambda text:None):
    """Retourne une vue oblique + dessus et une liste de limites de couverture."""
    projections=[Projection(scene),Projection(scene,top=True)]
    canvases=[Image.new('RGBA',p.size,(10,17,25,255)) for p in projections]
    sample=sampled_frames(scene['frames'],planes);warnings=[];loaded=0;nonempty=0
    for index,frame in enumerate(sample):
        try:
            if scene['cyan']:
                data,stats=shape_preview(frame['path'],white,tuple(scene['crop']),contrast)
                nonempty+=stats['coverage_percent']>0
                if stats['coverage_percent']>65:warnings.append('Very extensive extraction on layer '+str(frame['layer'])+'.')
            else:
                data=preview(frame['path'],white,tuple(scene['crop']),384)
            with Image.open(io.BytesIO(data)) as image:texture=image.convert('RGBA')
            for p,canvas in zip(projections,canvases):
                p.plane(canvas,texture,frame['position'],(.45 if scene['cyan'] else .07) if index<len(sample)-1 else 1)
            loaded+=1
        except (ValueError,OSError) as error:
            warnings.append('Plane '+str(frame['layer'])+' unavailable: '+str(error))
        progress('3D view · '+str(index+1)+' / '+str(len(sample))+' planes · '+scene['label'])
    if scene['cyan'] and not nonempty:warnings.append('No usable cyan section: the reconstruction is empty. Check the photographs and minimum contrast.')
    font=ImageFont.load_default(size=19)
    for p,canvas in zip(projections,canvases):
        draw=ImageDraw.Draw(canvas)
        labels=[]
        for z in (p.first,p.last):
            box=[p.point(u,v,z) for u,v in ((0,0),(1,0),(1,1),(0,1))]
            draw.line(box+[box[0]],fill=(78,116,138),width=2)
        for u,v in ((0,0),(1,0),(1,1),(0,1)):
            draw.line([p.point(u,v,p.first),p.point(u,v,p.last)],fill=(45,71,87),width=1)
        # Les scores les plus élevés sont dessinés en dernier, après la forme.
        for event in sorted(scene['events'],key=lambda e:e['priority_score']):
            box=p.box(event['box'],event['position']);color=score_color(event['priority_score'])
            draw.line(box+[box[0]],fill=color,width=3)
            center=((box[0][0]+box[2][0])/2,(box[0][1]+box[2][1])/2)
            draw.ellipse((center[0]-5,center[1]-5,center[0]+5,center[1]+5),fill=color,outline='white',width=1)
            if len(scene['events'])<=20:
                labels.append((center,event['report_label'],color))
        occupied=[]
        for center,label,color in reversed(labels):
            for distance in range(18,420,24):
                placed=False
                for dx,dy in ((1,-1),(1,1),(-1,-1),(-1,1),(0,-1),(0,1),(1,0),(-1,0)):
                    text_width=draw.textlength(label,font=font)
                    xy=(center[0]+dx*distance-(text_width if dx<0 else text_width/2 if dx==0 else 0),center[1]+dy*distance-10)
                    bounds=draw.textbbox(xy,label,font=font);rect=(bounds[0]-4,bounds[1]-3,bounds[2]+4,bounds[3]+3)
                    if rect[0]<10 or rect[1]<10 or rect[2]>canvas.width-10 or rect[3]>canvas.height-10:continue
                    if any(rect[0]<b[2]+5 and rect[2]>b[0]-5 and rect[1]<b[3]+5 and rect[3]>b[1]-5 for b in occupied):continue
                    anchor=(min(max(center[0],rect[0]),rect[2]),min(max(center[1],rect[1]),rect[3]))
                    draw.line([center,anchor],fill=color,width=1)
                    draw.rectangle(rect,fill=(10,17,25));draw.text(xy,label,font=font,fill=color)
                    occupied.append(rect);placed=True;break
                if placed:break
    output=[]
    for canvas in canvases:
        stream=io.BytesIO();canvas.convert('RGB').save(stream,format='PNG');output.append(stream.getvalue())
    return {'oblique':output[0],'top':output[1],'loaded':loaded,'sampled':len(sample),
            'total':len(scene['frames']),'warnings':warnings,'markers':len(scene['events'])}
