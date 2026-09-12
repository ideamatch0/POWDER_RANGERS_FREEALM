"""Create a sourced, editable commercialisation report and layout diagnostics."""
from pathlib import Path
import json,re,sys,html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from strategy_content import pages,S,M
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf'),('Arial-Italic','ariali.ttf')]:pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
NAVY=colors.HexColor('#0a1724');CYAN=colors.HexColor('#56c4e5');INK=colors.HexColor('#1a2d40');GRAY=colors.HexColor('#526778');PALE=colors.HexColor('#eaf5f8')
PW,PH=A4;LEFT,TOP,BOTTOM=46,58,47
# SimpleDocTemplate's frame has 6 pt padding on each side; leave extra bottom slack.
WIDTH=PW-2*LEFT-12;HEIGHT=PH-TOP-BOTTOM-20
def styles(scale=1):
    return {key:ParagraphStyle(key,fontName=face,fontSize=size*scale,leading=leading*scale,textColor=col,spaceAfter=after*scale,keepWithNext=key in ('h','title','lead'),wordWrap='CJK' if key=='cell' else None)
       for key,face,size,leading,col,after in [('body','Arial',10.3,14.5,INK,9),('cell','Arial',9,12.2,INK,0),('th','Arial-Bold',9,12.2,colors.white,0),
        ('h','Arial-Bold',12.4,16,INK,7),('title','Arial-Bold',26,30,NAVY,10),('lead','Arial',12,16,GRAY,18),('call','Arial-Bold',10.3,14.5,INK,0),('small','Arial',8.5,11.8,GRAY,6)]}
def blockflow(block,ss):
    kind,data=block
    if kind in ('p','h'):return [Paragraph(data,ss['body' if kind=='p' else 'h'])]
    if kind=='b':return [Paragraph('•  '+item,ss['body']) for item in data]
    if kind=='c':
        table=Table([[Paragraph(data,ss['call'])]],colWidths=[WIDTH])
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.5,CYAN),('LINEBEFORE',(0,0),(0,-1),3,CYAN),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11)]))
        return [table,Spacer(1,9)]
    if kind=='t':
        headers,rows,ratios=data;ratios=ratios or [1/len(headers)]*len(headers)
        vals=[[Paragraph(str(x),ss['th']) for x in headers]]+[[Paragraph(str(x),ss['cell']) for x in row] for row in rows]
        t=Table(vals,colWidths=[WIDTH*r for r in ratios],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f0f5f8'),colors.white]),
          ('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#dbe5ea')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        return [t,Spacer(1,12)]
    if kind=='i':
        path,caption=data;im=Image(str(ROOT/path));ratio=WIDTH/im.imageWidth;im.drawWidth=WIDTH;im.drawHeight=im.imageHeight*ratio
        return [im,Paragraph(caption,ss['small'])]
    raise ValueError(kind)

def flowheight(items):
    # Upper bound: include both spaces even though Platypus collapses adjoining margins.
    return sum(x.wrap(WIDTH,HEIGHT)[1]+x.getSpaceBefore()+x.getSpaceAfter() for x in items)

def cover(c,doc):
    c.saveState();c.setFillColor(NAVY);c.rect(0,0,PW,PH,fill=1,stroke=0)
    c.setStrokeColor(colors.HexColor('#173042'));c.setLineWidth(.5)
    for x in range(-900,600,55):c.line(x,0,x+850,PH)
    c.setFillColor(CYAN);c.setFont('Arial-Bold',10);c.drawString(48,787,'POWDER RANGER  /  COMMERCIALISATION & CODE REVIEW')
    c.setFillColor(colors.white);c.setFont('Arial-Bold',42);c.drawString(46,711,'From prototype');c.drawString(46,659,'to paid pilots.')
    c.setFont('Arial',18);c.setFillColor(CYAN);c.drawString(48,615,'Every layer under watch.')
    c.setFont('Arial',11);c.setFillColor(colors.HexColor('#b9cad6'))
    c.drawString(48,573,'Global industrial LPBF teams');c.drawString(48,552,'Market, business models, validation, launch and next steps')
    c.drawImage(str(ROOT/'output/video/volume.png'),65,178,width=465,height=329,preserveAspectRatio=True,mask='auto')
    c.setFont('Arial',8);c.drawString(48,159,'Actual software render from public NIST data. Photographic shape; not material ground truth.')
    c.setStrokeColor(CYAN);c.line(48,135,PW-48,135)
    c.setFont('Arial-Bold',12);c.setFillColor(colors.white);c.drawString(48,109,'DECISION REPORT  /  09 SEPTEMBER 2026')
    c.setFont('Arial',10);c.setFillColor(colors.HexColor('#b9cad6'));c.drawString(48,84,'English  ·  Application 0.3.1 audit  ·  Pricing and forecasts are hypotheses')
    c.restoreState()

def footer(c,doc):
    c.saveState();c.setFillColor(NAVY);c.rect(0,PH-31,PW,31,fill=1,stroke=0)
    c.setFont('Arial-Bold',8);c.setFillColor(colors.white);c.drawString(LEFT,PH-20,'POWDER RANGER')
    c.setFont('Arial',8);c.setFillColor(CYAN);c.drawRightString(PW-LEFT,PH-20,'Every layer under watch.')
    c.setStrokeColor(colors.HexColor('#dbe5ea'));c.line(LEFT,34,PW-LEFT,34)
    c.setFont('Arial',8);c.setFillColor(GRAY);c.drawString(LEFT,21,'Strategy & engineering review  |  9 September 2026')
    c.drawRightString(PW-LEFT,21,f'{doc.page:02d}');c.restoreState()

class ReportDoc(SimpleDocTemplate):
    def afterFlowable(self,flowable):
        if hasattr(flowable,'section_key'):
            self.canv.bookmarkPage(flowable.section_key)
            self.canv.addOutlineEntry(flowable.section_title,flowable.section_key,level=0,closed=False)

def to_md(value):
    value=re.sub(r'<link href="([^"]+)"[^>]*>(.*?)</link>',lambda m:'['+m[2]+']('+m[1]+')',str(value))
    value=value.replace('<b>','**').replace('</b>','**').replace('<br/>','\n\n')
    return html.unescape(re.sub(r'<[^>]+>','',value))

def main():
    ss=styles();story=[Spacer(1,650),PageBreak(),Paragraph('Read the report',ss['title']),Paragraph('Start with the decision, then use the sections as a working plan.',ss['lead'])]
    toc=[]
    for n,pg in enumerate(pages,1):
        toc.append([Paragraph(f'<link href="#section-{n}" color="#166a87">{n:02d}  {pg["title"]}</link>',ss['cell']),Paragraph(str(n+2),ss['cell'])])
    contents=Table(toc,colWidths=[WIDTH-35,35]);contents.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#e0e8ed'))]))
    story.extend([contents,PageBreak()]);diagnostics=[];md=['# Powder Ranger — Commercialisation and code review','9 September 2026. Global industrial LPBF teams. All commercial figures are illustrative EUR ex VAT.']
    for n,pg in enumerate(pages,1):
        for scale in (1,.98,.96,.94,.92,.90,.88):
            ss=styles(scale);items=[Paragraph(f'{n:02d} / '+pg['title'],ss['title']),Paragraph(pg['lead'],ss['lead'])]
            for block in pg['blocks']:items.extend(blockflow(block,ss))
            measured=flowheight(items)
            if measured<HEIGHT-6:break
        if measured>=HEIGHT-6:raise ValueError(f'Page {n} too tall: {measured:.1f} > {HEIGHT:.1f}')
        diagnostics.append({'section':n,'title':pg['title'],'scale':scale,'height':round(measured,1)})
        items[0].section_key='section-'+str(n);items[0].section_title=pg['title']
        story.extend(items)
        if n<len(pages):story.append(PageBreak())
        md.extend(['## '+str(n)+'. '+pg['title'],pg['lead']])
        for kind,data in pg['blocks']:
            if kind=='t':
                headers,rows,_=data;md.extend(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|'])
                md.extend('| '+' | '.join(to_md(x).replace('\n',' ') for x in row)+' |' for row in rows)
            elif kind=='b':md.append('\n'.join('- '+to_md(x) for x in data))
            elif kind=='h':md.append('### '+to_md(data))
            else:md.append(to_md(data))
    filename=OUT/'Powder_Ranger_Global_Launch_Strategy_EN.pdf'
    doc=ReportDoc(str(filename),pagesize=A4,leftMargin=LEFT,rightMargin=LEFT,topMargin=TOP,bottomMargin=BOTTOM,
        title='Powder Ranger — Global launch strategy and engineering review',author='Powder Ranger project',subject='Assisted commercialisation, LPBF market, pricing scenarios, code audit and 90-day plan')
    doc.build(story,onFirstPage=cover,onLaterPages=footer)
    (ROOT/'output/Powder_Ranger_Global_Launch_Strategy_EN.md').write_text('\n\n'.join(md),encoding='utf-8')
    (ROOT/'research/report-layout.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    print(json.dumps({'pdf':str(filename),'expected_pages':len(pages)+2,'sections':len(pages),'minimum_scale':min(d['scale'] for d in diagnostics),'bytes':filename.stat().st_size},indent=2))
if __name__=='__main__':main()
