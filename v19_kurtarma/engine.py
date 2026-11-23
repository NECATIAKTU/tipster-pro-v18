"""Read-only, timestamp-safe recovery of unpredicted future fixtures.

Uses existing V18 prediction primitives. No invented score, fixture or odds.
Historical ESPN matches are fetched only for leagues with genuine missing matches.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from gercek_tahmin_v18 import historical_stats
from tahmin_motoru import otomatik_eslestir, indeks_olustur
from gol_modeli import mac_analizi
from fikstur_yeni import LIGLER

LINES = ('1.5','2.5','3.5','4.5','5.5','6.5')

def utc(v):
    if not isinstance(v, str): return None
    try:
        d=datetime.fromisoformat(v.replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, OverflowError): return None

def fixture_key(m):
    if not isinstance(m,dict): return None
    league=str(m.get('lig_kodu') or '').strip()
    event=str(m.get('id') or '').strip()
    if not league or not event: return None
    if '|' in event:
        prefix,suffix=event.split('|',1)
        return event if prefix==league and suffix and '|' not in suffix else None
    return f'{league}|{event}'

def check_input(fixture, v18, now):
    if not isinstance(fixture,dict) or not isinstance(fixture.get('maclar'),list): raise ValueError('Fikstur dosyasi gecersiz')
    ftime=utc(fixture.get('olusturulma_utc'))
    if not ftime or not timedelta(0)<=now-ftime<=timedelta(hours=24): raise ValueError('Fikstur 24 saatten eski veya tarih gelecekte')
    if not isinstance(v18,dict) or v18.get('model')!='TIPSTER PRO V18' or not isinstance(v18.get('tahminler'),list):raise ValueError('V18 ciktisi gecersiz')
    ptime=utc(v18.get('olusturulma_utc'))
    if not ptime or not timedelta(0)<=now-ptime<=timedelta(hours=24):raise ValueError('V18 ciktisi 24 saatten eski veya tarih gelecekte')

def safe_selection(p):
    thresholds={'1.5':75,'2.5':65,'3.5':65,'4.5':65,'5.5':65,'6.5':65}
    for l in reversed(LINES):
        value=p.get(l+'_ust')
        if isinstance(value,(int,float)) and not isinstance(value,bool) and value>=thresholds[l]: return l+' UST'
    return 'RISKLI'

def recover(fixture, v18, archive, *, now=None, fetch=None, history_days=180, max_leagues=42):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Timezone required')
    if history_days<30 or history_days>180:raise ValueError('history_days 30..180')
    check_input(fixture,v18,now)
    if not isinstance(archive,list):raise ValueError('Archive must be a list')
    archived={r.get('kimlik') for r in archive if isinstance(r,dict)}
    existing={fixture_key(r) for r in v18['tahminler'] if isinstance(r,dict)}
    by_league=defaultdict(list);audit=[];counts=Counter();seen=set()
    for m in fixture['maclar']:
        key=fixture_key(m)
        if not key:
            counts['GECERSIZ_KIMLIK']+=1;continue
        if key in seen:
            counts['FIKSTUR_TEKRARI']+=1;continue
        seen.add(key)
        start=utc(m.get('tarih'))
        if not start or start<=now:
            counts['BASLAMIS_VEYA_TARIHSIZ']+=1;continue
        if key in existing:
            counts['V18_TAHMIN_VAR']+=1;continue
        if key in archived:
            counts['ARSIVDE_VAR']+=1;continue
        league=m.get('lig_kodu')
        if league not in LIGLER:
            counts['LIG_DESTEKLENMIYOR']+=1
            audit.append({'kimlik':key,'ev_sahibi':m.get('ev_sahibi'),'deplasman':m.get('deplasman'),'neden':'LIG_DESTEKLENMIYOR'});continue
        by_league[league].append(m)
    recovered=[]
    for idx,(league,ms) in enumerate(sorted(by_league.items())):
        if idx>=max_leagues:
            for m in ms:
                counts['LIG_LIMITI']+=1
                audit.append({'kimlik':fixture_key(m),'neden':'LIG_LIMITI'})
            continue
        try:
            if fetch is None:
                teams,meta=historical_stats(league,now,history_days)
            else:
                teams,meta=historical_stats(league,now,history_days,fetch=fetch)
            if meta['hata_gunu']>max(2,history_days//10) or meta['tamamlanmis_mac']<10:
                for m in ms:
                    counts['GECMIS_VERI_EKSIK']+=1
                    audit.append({'kimlik':fixture_key(m),'neden':'GECMIS_VERI_EKSIK','lig':league})
                continue
            index=indeks_olustur(teams)
        except (OSError,ValueError,KeyError,TypeError,TimeoutError) as exc:
            for m in ms:
                counts['VERI_ERISIM_HATASI']+=1
                audit.append({'kimlik':fixture_key(m),'neden':'VERI_ERISIM_HATASI','lig':league,'detay':type(exc).__name__})
            continue
        for m in ms:
            key=fixture_key(m)
            home=otomatik_eslestir(m.get('ev_sahibi'),teams,index)
            away=otomatik_eslestir(m.get('deplasman'),teams,index)
            if not home or not away or home==away:
                reason='TAKIM_ESLESMEDI';counts[reason]+=1
                audit.append({'kimlik':key,'neden':reason,'lig':league,'ev_sahibi':m.get('ev_sahibi'),'deplasman':m.get('deplasman'),'eslesen_ev':home,'eslesen_dep':away})
                continue
            if min(teams[home].get('mac',0),teams[away].get('mac',0))<5:
                reason='YETERSIZ_TAKIM_GECMISI';counts[reason]+=1
                audit.append({'kimlik':key,'neden':reason,'lig':league,'ev_mac':teams[home].get('mac',0),'dep_mac':teams[away].get('mac',0)})
                continue
            try:
                p=mac_analizi(home,away,teams)
                if any(not isinstance(p.get(l+'_ust'),(int,float)) or not 0<=p[l+'_ust']<=100 for l in LINES):raise ValueError('probability')
            except (ValueError,ArithmeticError,KeyError,TypeError,ZeroDivisionError,OverflowError):
                counts['MODEL_HATASI']+=1;audit.append({'kimlik':key,'neden':'MODEL_HATASI'});continue
            if utc(m.get('tarih'))<=now: # protect against runtime delay / stale fixture
                counts['BASLAMIS_VEYA_TARIHSIZ']+=1;continue
            recovered.append({'id':key,'tarih':m['tarih'],'lig_kodu':league,'lig':LIGLER[league],
                'ev_sahibi':m['ev_sahibi'],'deplasman':m['deplasman'],
                'istatistik_ev':home,'istatistik_deplasman':away,'tahmin':p,
                'hesaplama_zamani_utc':now.isoformat(),'veri_kaynagi':'ESPN tamamlanmis mac skorları',
                'gecmis_gun':history_days,'kaynak_mac_sayisi':meta['tamamlanmis_mac'],
                'kurtarma_kaynagi':'V19_BAGIMSIZ_KURTARMA','oneri':safe_selection(p)})
            counts['KURTARILAN']+=1
    original=[]
    for m in v18['tahminler']:
        if not isinstance(m,dict):continue
        t=utc(m.get('tarih'));made=utc(m.get('hesaplama_zamani_utc'))
        if t and made and made<t and now<t and fixture_key(m):original.append(m)
    combined={fixture_key(m):m for m in original}
    for m in recovered:combined.setdefault(fixture_key(m),m)
    panel={'model':'TIPSTER PRO V18','olusturulma_utc':now.isoformat(),
           'not':'V18 + bagimsiz V19 kurtarma ONIZLEME. Canli panele otomatik aktarilmaz. Olasiliklar garanti degildir.',
           'tahminler':sorted(combined.values(),key=lambda m:m['tarih']),
           'durum_sayilari':{'V18_GECERLI':len(original),'V19_KURTARILAN':len(recovered)},
           'lig_denetimi':v18.get('lig_denetimi',{})}
    report={'surum':'V19_KURTARMA_1','uretilme_utc':now.isoformat(),
            'fikstur_mac':len(fixture['maclar']),'v18_tahmin':len(v18['tahminler']),
            'arsiv_kayit':len(archive),'kurtarilan':len(recovered),
            'panel_onizleme_mac':len(panel['tahminler']),
            'nedenler':dict(sorted(counts.items())), 'detaylar':audit,
            'aciklama':'280 atlanan arşiv sayısı ile V18 modelinin eleme sayısı farklıdır; bu rapor yalnızca fikstürde gerçekten tahmini eksik gelecek maçları inceler.'}
    return recovered,panel,report

def write_new_json(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False,indent=2);f.write('\n')
