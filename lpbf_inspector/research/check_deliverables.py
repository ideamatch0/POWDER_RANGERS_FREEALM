from pathlib import Path
import json,math,re
from PIL import Image,ImageDraw,ImageFont
import pdfplumber
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];pdf=ROOT/'output/pdf/Powder_Ranger_Global_Launch_Strategy_EN.pdf'
reader=PdfReader(pdf);assert len(reader.pages)==33,len(reader.pages);assert len(reader.outline)==31
assert [reader.get_destination_page_number(x)+1 for x in reader.outline]==list(range(3,34))
checks=[];word_count=0
with pdfplumber.open(pdf) as book:
    for i,p in enumerate(book.pages,1):
        words=p.extract_words();word_count+=len(words)
        outside=[w['text'] for w in words if w['x0']<0 or w['x1']>p.width+.1 or w['top']<0 or w['bottom']>p.height]
        assert not outside,(i,outside)
        checks.append({'page':i,'words':len(words),'out_of_page':outside})
    assert '€6,855' in book.pages[22].extract_text()
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
files=sorted((ROOT/'tmp/pdfs').glob('strategy-*.png'))
for p in files:
    if int(p.stem.split('-')[-1])>len(reader.pages):
        assert p.parent.resolve()==(ROOT/'tmp/pdfs').resolve();p.unlink()
files=sorted((ROOT/'tmp/pdfs').glob('strategy-*.png'));assert len(files)==33
for start in range(0,len(files),6):
    sheet=Image.new('RGB',(1260,1260),'#dbe4ec');d=ImageDraw.Draw(sheet)
    for j,p in enumerate(files[start:start+6]):
        im=Image.open(p);im.thumbnail((400,575));x=10+(j%3)*420;y=12+(j//3)*630
        sheet.paste(im,(x,y));d.text((x,y+582),'Page '+str(start+j+1),font=font,fill='#1a2d40')
    sheet.save(ROOT/f'tmp/pdfs/contact-{start//6+1}.jpg',quality=93)
report={'pdf_pages':len(reader.pages),'bookmarks':len(reader.outline),'words':word_count,'page_checks':checks}
(ROOT/'research/deliverable-checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='page_checks'},indent=2))
