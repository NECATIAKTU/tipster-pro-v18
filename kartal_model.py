#!/usr/bin/env python3
"""Alternative model research: past match events -> pre-match only home/away shrinkage.
No connection to V18 live engine, no edits, no external network.
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from kartal import dt,LINES,write_json


def poisson_tail(lam,line):
    k=int(float(line))
    term=math.exp(-lam);cdf=term
    for j in range(1,k+1):
        term*=lam/j;cdf+=term
    return max(0.,min(1.,1.-cdf))*100


def model_events(events,fixtures,now=None,window=180,min_games=5):
    now=now or datetime.now(timezone.utc)
    cleaned=[];problems=[]
    for e in events:
        try:
            t=dt(e['tarih']); hg=int(e['ev_gol']);ag=int(e['dep_gol'])
            if not t or t>=now or (now-t).days>window or min(hg,ag)<0:continue
            home=str(e['ev_sahibi']).strip();away=str(e['deplasman']).strip();lig=str(e['lig_kodu']).strip()
            if not all([home,away,lig]) or home==away:continue
            cleaned.append((t,lig,home,away,hg,ag))
        except (KeyError,ValueError,TypeError):problems.append('gecersiz_tarih_skor_alan')
    cleaned.sort()
    by_league=defaultdict(list)
    for m in cleaned:by_league[m[1]].append(m)
    output=[]
    for fix in fixtures:
        if not isinstance(fix,dict):continue
        kick=dt(fix.get('tarih'))
        if not kick or kick<=now:continue
        lig=str(fix.get('lig_kodu') or '');home=str(fix.get('ev_sahibi') or '');away=str(fix.get('deplasman') or '')
        # cutoff is strictly before fixture, never training on future matches
        prev=[m for m in by_league[lig] if m[0]<min(now,kick)]
        hs=[m for m in prev if m[2]==home]; aws=[m for m in prev if m[3]==away]
        ha=[m for m in prev if m[2]==home or m[3]==home]
        aa=[m for m in prev if m[2]==away or m[3]==away]
        row={'id':fix.get('id'),'ev_sahibi':home,'deplasman':away,'lig_kodu':lig,'tarih':fix.get('tarih'),'model':'KARTAL_DENEYSEL','durum':'INCELEME'}
        if len(prev)<20 or min(len(ha),len(aa))<min_games:
            row['neden']='YETERSIZ_LIG_VEYA_TAKIM_VERISI';output.append(row);continue
        mean_home=sum(m[4] for m in prev)/len(prev)
        mean_away=sum(m[5] for m in prev)/len(prev)
        if min(mean_home,mean_away)<0.1:
            row['neden']='LIG_REFERANSI_GUVENSIZ';output.append(row);continue
        def smooth(values,prior,weight=8):return (sum(values)+weight*prior)/(len(values)+weight)
        # home attack and away conceded, away attack and home conceded (within league)
        a=smooth([m[4] for m in hs],mean_home)
        b=smooth([m[4] for m in aws],mean_home)
        c=smooth([m[5] for m in aws],mean_away)
        d=smooth([m[5] for m in hs],mean_away)
        lam_h=max(0.05,min(5, a*b/mean_home))
        lam_a=max(0.05,min(5, c*d/mean_away))
        total=lam_h+lam_a
        row.update({'durum':'DENEYSEL_HESAPLANDI','beklenen_ev':round(lam_h,3),'beklenen_deplasman':round(lam_a,3),'beklenen_gol':round(total,3),'mac_sayisi_lig':len(prev),'ev_saha_mac':len(hs),'dep_saha_mac':len(aws),'ev_toplam_mac':len(ha),'dep_toplam_mac':len(aa),'olasiliklar':{s:round(poisson_tail(total,s),2) for s in LINES},'uyari':'Kalibre edilmemis deneysel model; V18 tahminini degistirmez'})
        output.append(row)
    return {'model':'KARTAL_DENEYSEL_V1','veri_kesim_utc':now.isoformat(),'analizler':output,'hatalar':dict((x,problems.count(x)) for x in set(problems))}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--gecmis',required=True,help='Format: maclar:[{tarih,lig_kodu,ev_sahibi,deplasman,ev_gol,dep_gol}]')
    ap.add_argument('--fikstur',required=True);ap.add_argument('--cikti',default='kartal_rapor/04_deneysel_model.json')
    ns=ap.parse_args()
    events=json.loads(Path(ns.gecmis).read_text(encoding='utf8'))
    fixtures=json.loads(Path(ns.fikstur).read_text(encoding='utf8'))
    if isinstance(events,dict):events=events.get('maclar',[])
    if isinstance(fixtures,dict):fixtures=fixtures.get('maclar',[])
    res=model_events(events,fixtures)
    write_json(Path(ns.cikti),res)
    print('Deneysel analiz:',len(res['analizler']))
if __name__=='__main__':main()
