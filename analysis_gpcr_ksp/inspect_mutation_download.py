#!/usr/bin/env python3
from pathlib import Path
import io, json, requests, pandas as pd

out=Path('analysis_gpcr_ksp/mutation_check'); out.mkdir(parents=True,exist_ok=True)
urls=[
 'https://gpcrdb.org/mutations/family/001/download',
 'https://gpcrdb.org/mutations/family/001_001/download',
]
summary=[]
for url in urls:
    rec={'url':url}
    try:
        r=requests.get(url,timeout=180,allow_redirects=True)
        rec.update(status=r.status_code,content_type=r.headers.get('content-type'),nbytes=len(r.content),final_url=r.url)
        fn='download_'+url.split('/')[-2].replace('_','-')+'.bin'
        (out/fn).write_bytes(r.content)
        try:
            df=pd.read_excel(io.BytesIO(r.content))
            rec.update(rows=len(df),cols=len(df.columns),columns=list(map(str,df.columns)))
            df.head(20).to_csv(out/(fn+'.head.csv'),index=False)
        except Exception as e:
            rec['read_excel_error']=repr(e)
            (out/(fn+'.head.txt')).write_text(r.text[:5000] if 'text' in (r.headers.get('content-type') or '') else repr(r.content[:500]))
    except Exception as e:
        rec['error']=repr(e)
    summary.append(rec)
print(json.dumps(summary,indent=2))
(out/'summary.json').write_text(json.dumps(summary,indent=2))
