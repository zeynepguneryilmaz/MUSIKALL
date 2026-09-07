#!/usr/bin/env python3
import requests, json
for entry in ['adrb2_human','aa2ar_human','drd2_rat']:
    url=f'https://gpcrdb.org/services/mutant/{entry}/'
    r=requests.get(url,timeout=120)
    print('\n',entry,r.status_code,r.url,r.headers.get('content-type'),len(r.content))
    try:
        data=r.json()
        print('n=',len(data),'type=',type(data).__name__)
        if data:
            print('keys=',sorted(data[0].keys()))
            print('row=',json.dumps(data[0],ensure_ascii=False)[:2000])
    except Exception as e:
        print('json error',repr(e),r.text[:500])
