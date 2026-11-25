"""Independent V18 pilot. Never writes to production archive or panel."""
import argparse, json, math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from gol_modeli import bos_takim
from gercek_tahmin_v18 import produce, get_json
import gercek_tahmin_v18 as base


def historical_stats(lig, now, days, fetch=get_json):
    events = {}; errors = 0
    for i in range(1, days+1):
        try:
            for e in fetch(lig, (now-timedelta(days=i)).date())['events']:
                if e.get('id') and e.get('status',{}).get('type',{}).get('completed'):
                    events[str(e['id'])] = e
        except (OSError, ValueError, KeyError, TypeError): errors += 1
    rows=[]
    for e in events.values():
        try:
            dt=datetime.fromisoformat(e['date'].replace('Z','+00:00'))
            if dt >= now: continue
            c=e['competitions'][0]['competitors']
            h=next(x for x in c if x['homeAway']=='home'); a=next(x for x in c if x['homeAway']=='away')
            hn,an=h['team']['displayName'],a['team']['displayName']; hg,ag=int(h['score']),int(a['score'])
            if not hn or not an or hn==an or min(hg,ag)<0: continue
            rows.append((dt,str(e['id']),hn,an,hg,ag))
        except (KeyError, IndexError, StopIteration, ValueError, TypeError): continue
    teams=defaultdict(bos_takim)
    for _,_,h,a,hg,ag in sorted(rows):
        for name,side,g,c in [(h,'ev',hg,ag),(a,'dep',ag,hg)]:
            t=teams[name]; t['mac']+=1; t['attigi']+=g; t['yedigi']+=c
            t[side+'_mac']+=1; t[side+'_attigi']+=g; t[side+'_yedigi']+=c; t['son_maclar'].append((g,c))
    return dict(teams), {'tamamlanmis_mac':len(rows),'hata_gunu':errors,'sorgu_gunu':days}


def pilot(fixture, now, days=90, fetch=get_json):
    # Only in this process, restore immediately. Same production gates and model.
    fixture={**fixture,'maclar':[m for m in fixture['maclar'] if not str(m.get('lig_kodu','')).startswith('uefa.')]}
    old=base.historical_stats
    try:
        base.historical_stats=historical_stats
        result=produce(fixture,now,days,fetch)
    finally: base.historical_stats=old
    result['model']='V18 GOL KESIF PILOT - kalibre edilmemis'
    return result


def audit(records):
    groups=defaultdict(lambda:[0,0,0.0,0.0]); errors=[]
    for r in records:
        if r.get('durum')!='DOGRULANDI': continue
        total=r.get('sonuc',{}).get('toplam_gol'); probs=r.get('olasiliklar',{})
        if not isinstance(total,int): continue
        league=r.get('mac',{}).get('lig_kodu','?')
        for k,p in probs.items():
            try: line=float(k.split('_')[0]); p=float(p)/100
            except (ValueError,TypeError): continue
            if not 0<=p<=1: continue
            y=int(total>line)
            for key in [f'ALL|{k}',f'{league}|{k}']:
                g=groups[key]; g[0]+=1; g[1]+=y; g[2]+=p; g[3]+=(p-y)**2
        choice=str(r.get('kilitli_secim','')).replace(' ÜST','_ust').replace(' UST','_ust')
        if choice in probs and total<=float(choice.split('_')[0]): errors.append({'kimlik':r.get('kimlik'),'lig':league,'secim':choice,'model_yuzdesi':probs[choice],'toplam_gol':total})
    return {'gruplar':{k:{'n':n,'gerceklesen_yuzde':round(100*y/n,2),'ortalama_model_yuzdesi':round(100*p/n,2),'brier':round(b/n,5)} for k,(n,y,p,b) in sorted(groups.items())},'yanlis_kilitli_secimler':errors}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--arsiv'); p.add_argument('--fikstur'); p.add_argument('--cikti',required=True); a=p.parse_args()
    if bool(a.arsiv)==bool(a.fikstur): p.error('Bir veri girişi seçin')
    path=Path(a.cikti)
    if path.name not in ('gol_kesif_denetim.json','gol_kesif_pilot.json'): p.error('Sadece pilot çıktı adı kullanılabilir')
    data=json.loads(Path(a.arsiv or a.fikstur).read_text())
    result=audit(data) if a.arsiv else pilot(data,datetime.now(timezone.utc))
    with path.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
if __name__=='__main__': main()
