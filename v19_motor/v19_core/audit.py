"""Read-only pre-match forecast audit against verified V18 archive."""
from collections import Counter,defaultdict
from math import sqrt
from .engine import LINES,utc

def wilson(w,n):
    if not n:return None
    z=1.96;p=w/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d
    half=z*sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return [round(100*(c-half),2),round(100*(c+half),2)]

def archive_audit(rows):
    selected=Counter(); finished=[]; invalid=Counter(); leagues=defaultdict(lambda:[0,0])
    for row in rows:
        choice=row.get('kilitli_secim') or 'BOS';selected[choice]+=1
        if row.get('durum')!='DOGRULANDI':continue
        score=row.get('sonuc') or {}; match=row.get('mac') or {}
        try:
            total=int(score['toplam_gol']); kickoff=utc(match['tarih'])
            calc=utc(match['hesaplama_zamani_utc']);locked=utc(row['kilit_zamani_utc'])
            if min(total,25-total)<0 or calc>=kickoff or locked>=kickoff:
                invalid['YANLIS_SONUC_VEYA_ZAMAN']+=1;continue
        except (KeyError,TypeError,ValueError):invalid['EKSIK_SONUC_VEYA_ZAMAN']+=1;continue
        p=row.get('olasiliklar') or match.get('tahmin') or {}
        if not all(isinstance(p.get(f'{l:.1f}_ust'),(int,float)) and 0<=p[f'{l:.1f}_ust']<=100 for l in LINES):
            invalid['OLASILIK_EKSIK']+=1;continue
        finished.append((row,total,p))
    lines={}
    for l in LINES:
        key=f'{l:.1f}_ust';n=len(finished)
        wins=sum(g>l for _,g,_ in finished)
        forecast=sum(p[key] for _,_,p in finished)/n if n else 0
        brier=sum((p[key]/100-int(g>l))**2 for _,g,p in finished)/n if n else 0
        lines[key]={'n':n,'model_ortalama':round(forecast,2) if n else None,
                    'gercek_oran':round(100*wins/n,2) if n else None,
                    'sapma_puan':round(forecast-100*wins/n,2) if n else None,
                    'brier':round(brier,5) if n else None,'wilson_95':wilson(wins,n)}
    chosen=defaultdict(lambda:[0,0])
    for row,g,p in finished:
        choice=str(row.get('kilitli_secim') or '').replace('Ü','U').upper().strip()
        for l in LINES:
            if choice==f'{l:.1f} UST':
                chosen[choice][0]+=1;chosen[choice][1]+=int(g>l)
                league=(row.get('mac') or {}).get('lig_kodu','BILINMIYOR')
                leagues[league][0]+=1;leagues[league][1]+=int(g>l)
    return {'toplam':len(rows),'dogrulanmis_ve_zaman_gecerli':len(finished),
            'secim_dagilimi':dict(selected),'veri_hatalari':dict(invalid),'tum_cizgiler':lines,
            'kilitli_secimler':{k:{'n':v[0],'dogru':v[1],'basari':round(v[1]/v[0]*100,2),
                                  'wilson_95':wilson(v[1],v[0])} for k,v in chosen.items()},
            'ligler':{k:{'n':v[0],'dogru':v[1],'basari':round(v[1]/v[0]*100,2)} for k,v in leagues.items()},
            'uyari':'Veriler farkli gunler ve secim politikalarindan gelebilir; bu rapor model iyilestirmesi kanitlamaz.'}
