"""Append-only publication snapshots; no changes to V18 predictions."""
import argparse,json,re
from pathlib import Path
from datetime import datetime,timezone

def dt(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('UTC required')
    return t

def append(history,panel,run_id):
    if history.get('version')!=1 or not isinstance(history.get('yayinlar'),list): raise ValueError('Invalid history')
    if any(x['id']==run_id for x in history['yayinlar']): return history
    now=dt(panel['olusturulma_utc']); rows=[]; seen=set()
    for r in panel['tahminler']:
        m=re.fullmatch(r'([1-6]\.5) UST',r['kilitli_secim'])
        if not m: continue
        p=r['olasiliklar'][m[1]+'_ust']; start=dt(r['tarih'])
        if not dt(r['hesaplama_zamani_utc']) <= dt(r['kilit_zamani_utc']) <= now < start: raise ValueError('Invalid lock')
        if r['id'] in seen or not 0<=p<=100: raise ValueError('Invalid row')
        seen.add(r['id']); rows.append(dict(id=r['id'],lig=r['lig'],mac=r['ev_sahibi']+' - '+r['deplasman'],tarih=r['tarih'],secim=r['kilitli_secim'],yuzde=p,kilit=r['kilit_zamani_utc']))
    rows.sort(key=lambda r:-r['yuzde']) # stable, same as panel
    if history['yayinlar'] and now < dt(history['yayinlar'][-1]['zaman']): raise ValueError('Out of order publication')
    return dict(version=1,yayinlar=history['yayinlar']+[dict(id=run_id,zaman=now.isoformat(),adaylar=rows)])

def main():
    p=argparse.ArgumentParser();p.add_argument('panel');p.add_argument('history');p.add_argument('run_id');a=p.parse_args()
    path=Path(a.history); history=json.loads(path.read_text()) if path.exists() else dict(version=1,yayinlar=[])
    result=append(history,json.loads(Path(a.panel).read_text()),a.run_id)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(path)
    print('TOP ARSIV YAYIN SAYISI:',len(result['yayinlar']))
if __name__=='__main__':main()
