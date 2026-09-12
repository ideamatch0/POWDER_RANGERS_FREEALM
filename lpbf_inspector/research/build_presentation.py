"""27-second presentation using actual software outputs, not a UI recording."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import base64,io,json,math,re,subprocess,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from local_app import Application
from reporting import collect_report
from review import picture
from report_volume import render_volume

OUT=ROOT/'output/video';OUT.mkdir(parents=True,exist_ok=True)
FF=ROOT/'.deps/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
W,H,FPS,DURATION=1920,1080,24,27
BG=(8,14,22);CYAN=(122,222,255);MUTED=(156,176,194);WHITE=(242,247,250);RED=(255,79,100)
fonts={}
def font(size,bold=False):
    key=(size,bold)
    if key not in fonts:fonts[key]=ImageFont.truetype('C:/Windows/Fonts/arial'+('bd' if bold else '')+'.ttf',size)
    return fonts[key]
def text(im,xy,value,size=40,color=WHITE,bold=False):
    ImageDraw.Draw(im).text(xy,value,font=font(size,bold),fill=color)
def center(im,y,value,size=40,color=WHITE,bold=False):
    f=font(size,bold);text(im,((W-f.getlength(value))/2,y),value,size,color,bold)
def contain(im,asset,rect):
    x,y,w,h=rect;tile=ImageOps.contain(asset,(int(w),int(h)),Image.Resampling.LANCZOS)
    im.paste(tile,(int(x+(w-tile.width)/2),int(y+(h-tile.height)/2)))
def badge(size):
    scale=size/80;im=Image.new('RGBA',(size,size));d=ImageDraw.Draw(im)
    pts=lambda p:[(x*scale,y*scale) for x,y in p]
    d.polygon(pts([(16,4),(64,4),(76,16),(76,48),(40,76),(4,48),(4,16)]),fill='#111a24',outline='#304452',width=max(1,int(scale*1.5)))
    for y,c in [(51,'#46758e'),(41,'#70b1d0')]:d.line(pts([(14,y),(40,y+14),(66,y)]),fill=c,width=int(scale*3),joint='curve')
    poly=pts([(14,31),(40,17),(66,31),(40,45),(14,31)])
    d.polygon(poly,fill='#203a4c');d.line(poly,fill='#91dcff',width=int(scale*3),joint='curve')
    d.polygon(pts([(22,31),(40,24),(48,27),(40,30),(28,36)]),fill='#0b1119')
    for p in [[(43,22),(43,18),(48,18)],[(59,28),(64,28),(64,24)],[(43,36),(43,40),(48,40)],[(64,32),(64,40),(59,40)]]:d.line(pts(p),fill=RED,width=int(scale*2))
    d.ellipse((49*scale,25*scale,57*scale,33*scale),fill=RED)
    return im

def assets():
    app=Application();assert app.library['id']=='nist_scan','Use only the public NIST sample for marketing'
    snapshot=collect_report(app,app.key,{'job_name':'NIST public demonstration','planes':64,'order':'priority'})
    eligible=[d for d in snapshot['details'] if all(f and f['comparable'] for f in d['frames'])]
    detail=eligible[0];box=json.loads(detail['event']['box'])
    for j,f in enumerate(detail['frames']):
        html=picture(f,app.config,box,detail['crop'],reference=j!=1)
        raw=base64.b64decode(re.search(r'base64,([^\"]+)',html)[1]);(OUT/f'crop-{j}.jpg').write_bytes(raw)
    raw=base64.b64decode(re.search(r'base64,([^\"]+)',picture(detail['frames'][1],app.config,box))[1]);(OUT/'overview.jpg').write_bytes(raw)
    volume=render_volume(snapshot['scenes'][0],app.config.intensity_white_level,planes=64)
    (OUT/'volume.png').write_bytes(volume['oblique']);(OUT/'volume-top.png').write_bytes(volume['top'])
    metadata={'job':'NIST 3D Scan Strategies','source':'https://doi.org/10.18434/M32044','images':200,'layers':100,
        'stage':'After spreading','camera':detail['event']['camera'],'layer':detail['peak_layer'],'z_mm':detail['z_mm'],
        'score':detail['event']['priority_score'],'persistence':detail['event']['consecutive_count'],
        'retained':len(snapshot['details']),'render':{k:volume[k] for k in ('loaded','sampled','total','markers','warnings')},
        'frames':[{'name':f['name'],'layer':f['layer']} for f in detail['frames']],
        'register':[{'label':d['event']['report_label'],'layer':d['peak_layer'],'score':d['event']['priority_score']} for d in snapshot['details']]}
    (OUT/'demonstration.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');return metadata

def soundtrack():
    rate=48000;n=rate*DURATION;a=np.zeros(n,dtype=np.float64);rng=np.random.default_rng(821)
    # Original synthesized pulse: 120 BPM, kicks, hats, filtered bass and transition sweeps.
    for beat in np.arange(0,DURATION,.5):
        start=int(beat*rate);length=min(int(.42*rate),n-start);t=np.arange(length)/rate
        kick=np.sin(2*np.pi*(49*t+55*.045*(1-np.exp(-t/.045))))*np.exp(-t*13)*.42
        a[start:start+length]+=kick
        bass=np.sin(2*np.pi*([55,55,65.406,49][int(beat//2)%4])*t)*np.minimum(t/.02,1)*np.exp(-t*5)*.12
        a[start:start+length]+=bass
    for beat in np.arange(.25,DURATION,.5):
        start=int(beat*rate);length=min(int(.08*rate),n-start);t=np.arange(length)/rate
        noise=rng.standard_normal(length);noise=np.concatenate(([0],np.diff(noise)))
        a[start:start+length]+=noise*np.exp(-t*70)*.035
    for cut in (5,11,16,22,24):
        start=int((cut-.4)*rate);length=int(.7*rate);t=np.arange(length)/rate
        sweep=np.sin(2*np.pi*(180*t+1500*t*t))*.065*np.sin(np.pi*t/.7)**2
        a[start:start+length]+=sweep
    a*=np.minimum(np.arange(n)/rate/.5,1)*np.minimum((n-np.arange(n))/rate/1.2,1)
    a=np.tanh(a)*.85
    stereo=np.column_stack((a,a));pcm=(stereo*32767).astype('<i2')
    with wave.open(str(OUT/'original_soundtrack.wav'),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())
    return float(np.max(np.abs(a)))

def main():
    meta=assets();audio_peak=soundtrack();print(json.dumps(meta),flush=True)
    crops=[Image.open(OUT/f'crop-{j}.jpg').convert('RGB') for j in range(3)]
    overview=Image.open(OUT/'overview.jpg').convert('RGB');volume=Image.open(OUT/'volume.png').convert('RGB')
    logo=badge(480);small=badge(70)
    base=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(base)
    for x in range(-H,W,100):d.line((x,H,x+H,0),fill=(13,24,34),width=1)
    def board(t,kicker):
        im=base.copy();im.paste(small,(75,50),small);text(im,(166,70),'POWDER RANGER',25,WHITE,True)
        text(im,(W-515,75),'Every layer under watch.',23,MUTED)
        text(im,(90,178),kicker,24,CYAN,True)
        text(im,(90,1013),'PUBLIC NIST DATA  /  DATA-DRIVEN DEMONSTRATION',18,MUTED)
        ImageDraw.Draw(im).rectangle((90,1060,90+(W-180)*t/DURATION,1063),fill=CYAN)
        return im
    decoder=subprocess.Popen([str(FF),'-hide_banner','-loglevel','error','-i',str(OUT/'illustrative_lpbf_intro.mp4'),'-vf',f'scale={W}:{H},fps={FPS}','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    video=OUT/'Powder_Ranger_Presentation_27s_EN.mp4'
    log=open(OUT/'encoding.log','w')
    encoder=subprocess.Popen([str(FF),'-y','-hide_banner','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(OUT/'original_soundtrack.wav'),'-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',str(DURATION),'-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=log)
    contact=[];cuts=(0,5,11,16,22,24);old=None
    for i in range(FPS*DURATION):
        t=i/FPS
        if t<5:
            raw=decoder.stdout.read(W*H*3);assert len(raw)==W*H*3
            im=Image.frombytes('RGB',(W,H),raw)
            shade=Image.new('RGB',(W,H),BG);im=Image.blend(im,shade,.32)
            if t<2.5:
                text(im,(105,690),'THOUSANDS',110,WHITE,True);text(im,(105,805),'OF LAYERS.',110,WHITE,True)
            else:
                text(im,(105,690),'ONE CLEARER',110,WHITE,True);text(im,(105,805),'VIEW.',110,CYAN,True)
            text(im,(105,1004),'ILLUSTRATIVE LPBF FOOTAGE',18,MUTED)
        elif t<11:
            im=board(t,'01  /  FIND THE CHANGE');text(im,(90,225),'Same area. Before. After.',78,WHITE,True)
            for j,asset in enumerate(crops):
                x=90+j*586;rect=(x,405,562,430)
                ImageDraw.Draw(im).rounded_rectangle((x-6,399,x+568,841),radius=12,fill=(18,30,42),outline=RED if j==1 else (56,106,137),width=3)
                contain(im,asset,rect);text(im,(x,865),['BEFORE','FLAGGED IMAGE','AFTER'][j],26,RED if j==1 else CYAN,True)
                text(im,(x,910),'Layer '+str(meta['frames'][j]['layer']),27,MUTED)
            text(im,(90,334),'Matching crops make the difference easier to inspect.',32,MUTED)
        elif t<16:
            im=board(t,'02  /  PRIORITISE THE REVIEW');text(im,(90,230),'Intensity + persistence.',76,WHITE,True)
            contain(im,overview,(100,372,690,560))
            p=min(1,(t-11)/1.1);score=meta['score']*p
            text(im,(925,390),f'{score:.1f}',155,CYAN,True);text(im,(1275,508),'/ 100',48,MUTED)
            text(im,(935,590),'REVIEW PRIORITY',31,WHITE,True)
            d=ImageDraw.Draw(im);d.rounded_rectangle((935,655,1725,675),radius=10,fill=(34,51,65));d.rounded_rectangle((935,655,935+790*score/100,675),radius=10,fill=RED)
            text(im,(935,730),f"{meta['persistence']} consecutive layer(s)",40,WHITE,True)
            text(im,(935,801),'Sort by layer or by score.',30,MUTED)
            text(im,(935,879),'A review score, not defect probability.',24,MUTED)
        elif t<22:
            im=board(t,'03  /  EXPLORE IN 3D');text(im,(90,225),'See where it happened.',76,WHITE,True)
            contain(im,volume,(690,305,1150,670))
            text(im,(90,410),'CYAN',38,CYAN,True);text(im,(90,468),'Photographic part shape',30,WHITE)
            text(im,(90,568),'COLOUR BY PRIORITY',32,RED,True);text(im,(90,625),str(meta['render']['markers'])+' retained in this stage',31,WHITE)
            text(im,(90,773),'100 layers  /  200 images',30,MUTED)
            text(im,(90,827),'NIST 3D Scan Strategies',27,MUTED)
            text(im,(90,903),'Approximate shape; Z exaggerated.',23,MUTED)
        elif t<24:
            im=board(t,'04  /  KEEP THE EVIDENCE');text(im,(90,225),'Review. Retain. Report.',80,WHITE,True)
            d=ImageDraw.Draw(im);d.rounded_rectangle((100,381,1820,924),radius=18,fill=(19,31,43),outline=(57,77,94),width=2)
            contain(im,volume,(110,395,720,500));text(im,(890,421),'BUILD REVIEW REPORT',35,CYAN,True)
            text(im,(890,482),'Job name. Views. Observations.',30,WHITE)
            for j,r in enumerate(meta['register'][:4]):
                y=570+j*70;text(im,(895,y),r['label'],25,MUTED);text(im,(1060,y),'Layer '+str(r['layer']),27,WHITE);text(im,(1390,y),f"{r['score']:.1f} / 100",28,RED,True)
        else:
            im=base.copy();scale=1+.025*math.sin((t-24)*1.4);size=int(380*scale);b=logo.resize((size,size),Image.Resampling.LANCZOS);im.paste(b,((W-size)//2,130),b)
            center(im,555,'POWDER RANGER',96,WHITE,True);center(im,688,'Every layer under watch.',50,CYAN)
            center(im,850,'BRING A BUILD. SEE WHAT CHANGED.',32,WHITE,True)
            center(im,978,'Local image analysis  /  Human review  /  Explore a pilot',23,MUTED)
        # Brief wipe at each chapter; typography remains fully legible for most of every shot.
        elapsed=t-max(c for c in cuts if c<=t)
        if t>=5 and elapsed<.18:
            x=int(W*elapsed/.18);ImageDraw.Draw(im).rectangle((x,0,min(W,x+14),H),fill=CYAN)
        if t<.35:im=Image.blend(Image.new('RGB',(W,H),BG),im,t/.35)
        if t>26.7:im=Image.blend(im,Image.new('RGB',(W,H),BG),(t-26.7)/.3)
        if i in [24,96,180,312,444,552,612]:
            im.save(OUT/f'qa-frame-{i:03d}.jpg',quality=95);contact.append((t,im.resize((640,360))))
        if i==612:im.save(OUT/'presentation-poster.jpg',quality=95)
        encoder.stdin.write(im.tobytes())
        if i%120==0:print('Encoded',i,'/',FPS*DURATION,flush=True)
    encoder.stdin.close();assert encoder.wait()==0;decoder.stdout.close();assert decoder.wait()==0;log.close()
    sheet=Image.new('RGB',(1280,4*398),BG)
    for j,(t,frame) in enumerate(contact):
        x=(j%2)*640;y=(j//2)*398;sheet.paste(frame,(x,y));text(sheet,(x+15,y+364),f'{t:.1f} s',22,MUTED)
    sheet.save(OUT/'contact-sheet.jpg',quality=92)
    (OUT/'media-check.json').write_text(json.dumps({'frames':FPS*DURATION,'fps':FPS,'duration_seconds':DURATION,'resolution':[W,H],'audio_peak':audio_peak,'bytes':video.stat().st_size,'format':'H.264 yuv420p / AAC / MP4 faststart','data':meta},indent=2),encoding='utf-8')
    (OUT/'captions.srt').write_text('1\n00:00:00,000 --> 00:00:02,500\nThousands of layers.\n\n2\n00:00:02,500 --> 00:00:05,000\nOne clearer view.\n\n3\n00:00:05,000 --> 00:00:11,000\nSpot the change with matching before and after crops.\n\n4\n00:00:11,000 --> 00:00:16,000\nPrioritise review by intensity and persistence.\n\n5\n00:00:16,000 --> 00:00:22,000\nExplore retained indications in a photographic 3D stack.\n\n6\n00:00:22,000 --> 00:00:24,000\nReview. Retain. Report.\n\n7\n00:00:24,000 --> 00:00:27,000\nPowder Ranger. Every layer under watch.\n',encoding='utf-8')
    print('READY',video,flush=True)

if __name__=='__main__':main()
