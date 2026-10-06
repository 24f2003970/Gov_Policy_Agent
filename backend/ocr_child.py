"""Credential-free, one-page renderer/Tesseract child. Parent owns its whole process tree."""
import argparse
import csv
import json
import os
import math
from pathlib import Path
import subprocess
import sys
import pymupdf


def extract(path, ordinal, work, manifest, packs, dpi, max_pixels, seconds):
    with pymupdf.open(path) as document:
        page = document[ordinal - 1]
        scale = dpi / 72
        pixels = (math.ceil(page.rect.width*scale)+1) * (math.ceil(page.rect.height*scale)+1)
        if pixels > max_pixels: raise ValueError('ocr_pixel_limit')
        image = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csGRAY, alpha=False)
        if image.width * image.height > max_pixels: raise ValueError('ocr_pixel_limit')
        image.save(work/'page.png')
    environment = {k:v for k,v in os.environ.items() if not k.startswith('GOV_')}
    environment['OMP_THREAD_LIMIT'] = '1'
    subprocess.run([manifest['executable'],str(work/'page.png'),str(work/'result'),
        '--tessdata-dir',str(packs),'-l','eng+hin','--oem','1','--psm','3','-c','tessedit_create_tsv=1','-c','tessedit_create_txt=1'],
        check=True,timeout=seconds,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    tsv = work/'result.tsv'
    if tsv.stat().st_size > 8*1024*1024: raise ValueError('ocr_output_limit')
    words = []
    with tsv.open(encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream,delimiter='\t',quoting=csv.QUOTE_NONE):
            if row['level'] != '5' or not row['text'].strip(): continue
            words.append({'text':row['text'],'confidence':float(row['conf']),
                'line':[int(row[k]) for k in ('block_num','par_num','line_num')],
                'box':[int(row[k]) for k in ('left','top','width','height')]})
            if len(words)>20000: raise ValueError('ocr_word_limit')
    raw = work/'result.txt'
    if raw.stat().st_size>400000:raise ValueError('ocr_text_limit')
    text = raw.read_bytes().decode('utf-8')
    if len(text)>100000: raise ValueError('ocr_text_limit')
    mean = sum(w['confidence'] for w in words)/len(words) if words else 0
    low = sum(w['confidence']<50 for w in words)/len(words) if words else 1
    flags = ['manual_review_required','ocr_layout_not_guaranteed']
    if len(text.strip())<30 or len(words)<5 or mean<70 or low>0.25: flags.append('low_quality')
    return {'text':text,'quality_flags':flags,'boxes':words,
        'signals':{'mean_word_confidence':round(mean,2),'low_word_fraction':round(low,4),
            'word_count':len(words),'width':image.width,'height':image.height,'dpi':dpi,
            'signal_notice':'OCR engine signals, not factual confidence or measured transcription accuracy.',
            'preprocessing_revision':'gray-pdf-rotation-v1','text_serialization':'tesseract-txt-v1','deskew':'not_applied'}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('request');args = parser.parse_args()
    # Parent must assign the Windows Job before any descendant can be launched.
    if sys.stdin.buffer.read(1) != b'1': sys.exit(2)
    request = json.loads(Path(args.request).read_text('utf-8'))
    work = Path(args.request).parent
    try:
        result = extract(request['path'],request['ordinal'],work,request['manifest'],Path(request['packs']),
            request['dpi'],request['max_pixels'],request['seconds'])
    except Exception as exc:
        code = 'ocr_timeout' if isinstance(exc,subprocess.TimeoutExpired) else str(exc) if isinstance(exc,ValueError) and str(exc).startswith('ocr_') else 'ocr_failed'
        result = {'error':code}
    (work/'output.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
