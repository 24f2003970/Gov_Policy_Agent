"""Self-authored synthetic scans only; never imported into the live corpus."""
from pathlib import Path
import pymupdf

REFERENCES = {
    'english': 'TEST ONLY: Fictional policy dated 1 August 2025.\nLand-holding farmer families receive Rs 6,000 per year in 3 instalments.\nRegistration does not guarantee eligibility. No monthly payment is promised.',
    'hindi': 'केवल परीक्षण: काल्पनिक योजना 1 अगस्त 2025 की है।\nभूमिधारक किसान परिवारों को प्रति वर्ष 6,000 रुपये 3 किस्तों में मिलते हैं।\nपंजीकरण से पात्रता की गारंटी नहीं है। मासिक भुगतान का वादा नहीं है।',
    'mixed': 'TEST ONLY: काल्पनिक योजना 1 अगस्त 2025.\nभूमिधारक किसान परिवार: Rs 6,000 per year, 3 किस्तें।\nNo monthly payment. पात्रता की गारंटी नहीं है।',
}


def scan(text, noisy=False):
    font = Path(r'C:\Windows\Fonts\Nirmala.ttc')
    if not font.is_file(): raise RuntimeError('Hindi test font Nirmala.ttc required')
    digital = pymupdf.open();page = digital.new_page(width=595,height=350)
    css = '@font-face {font-family:test;src:url(Nirmala.ttc);} body {font-family:test;font-size:18pt;line-height:1.7;}'
    page.insert_htmlbox(pymupdf.Rect(30,30,565,320),'<body>'+text.replace('\n','<br>')+'</body>',
        css=css,archive=pymupdf.Archive(str(font.parent)))
    image = page.get_pixmap(matrix=pymupdf.Matrix(2 if noisy else 3,2 if noisy else 3),alpha=False)
    if noisy:
        from PIL import Image, ImageFilter
        import io
        source = Image.open(io.BytesIO(image.tobytes('png'))).convert('L').filter(ImageFilter.GaussianBlur(1.2))
        stream = io.BytesIO();source.save(stream,format='JPEG',quality=25);data=stream.getvalue()
    else: data=image.tobytes('png')
    scanned = pymupdf.open();p=scanned.new_page(width=595,height=350);p.insert_image(p.rect,stream=data)
    result=scanned.tobytes();digital.close();scanned.close();return result


def error_rate(reference, actual, words=False):
    import re,unicodedata
    clean=lambda value:re.sub(r'\s+',' ',unicodedata.normalize('NFC',value)).strip()
    a,b=clean(reference),clean(actual)
    if words:a,b=a.split(),b.split()
    prior=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(row[-1]+1,prior[j]+1,prior[j-1]+(x!=y)))
        prior=row
    return prior[-1]/max(1,len(a))
