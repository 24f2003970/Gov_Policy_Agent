"""Actual Tesseract against isolated self-authored scan transcripts; no live imports."""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from ocr_fixtures import REFERENCES,scan,error_rate
from app.config import Settings,ROOT
from app.ocr import prepared,run_page


if __name__=='__main__':
    settings=Settings();packs,manifest=prepared(settings)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='gov-ocr-evaluation-') as temporary:
        for name,reference in [*REFERENCES.items(),('noisy_hindi',REFERENCES['hindi'])]:
            path=Path(temporary)/(name+'.pdf');path.write_bytes(scan(reference,name.startswith('noisy')))
            result=run_page(settings,{'path':str(path),'ordinal':1,'manifest':manifest,'packs':str(packs),
                'dpi':300,'max_pixels':12000000,'seconds':30},lambda:True)
            if 'error' in result:raise RuntimeError(result['error'])
            rows.append({'fixture':name,'reference':reference,**result,
                'cer':error_rate(reference,result['text']),'wer':error_rate(reference,result['text'],True)})
    target=ROOT/'runtime/ocr-results.json';target.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ('fixture','cer','wer','quality_flags','text')} for r in rows],ensure_ascii=False,indent=2))
