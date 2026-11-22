"""Five-stage non-invasive V18/V19 auditing utilities (standard library)."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import exp, isfinite, log, sqrt
import json
from pathlib import Path

LINES = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)

def utc(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        raise ValueError('missing timestamp')
    if dt.tzinfo is None:
        raise ValueError('timezone required')
    return dt.astimezone(timezone.utc)

def normalize_event(row):
    """ESPN completed event or standard V19 row. Kickoff is not a result availability time."""
    if all(k in row for k in ('ev_sahibi', 'deplasman','ev_gol','dep_gol','lig_kodu')):
        ev, dep = row['ev_sahibi'], row['deplasman']
        h, a = int(row['ev_gol']), int(row['dep_gol'])
        league = row['lig_kodu']
        date = row['tarih']
        rid = row.get('id', '')
    elif 'competitions' in row:
        comps = row.get('competitions') or []
        if not comps: raise ValueError('missing competition')
        competitors = comps[0].get('competitors') or []
        if len(competitors) != 2: raise ValueError('competitors count')
        if not (row.get('status',{}).get('type',{}).get('completed') or comps[0].get('status',{}).get('type',{}).get('completed')):
            raise ValueError('not completed')
        home = next(c for c in competitors if c.get('homeAway')=='home')
        away = next(c for c in competitors if c.get('homeAway')=='away')
        ev, dep = home['team']['displayName'], away['team']['displayName']
        h,a = int(home['score']), int(away['score'])
        league = row.get('lig_kodu') or row.get('lig')
        date = row['date']; rid = row.get('id', '')
    else:
        ev, dep = row['ev'], row['dep']
        h, a = int(row['ev_gol']), int(row['dep_gol'])
        league = row['lig']; date = row['tarih']; rid = row.get('id', '')
    ev, dep, league = str(ev).strip(), str(dep).strip(), str(league or '').strip()
    t = utc(date)
    if not ev or not dep or ev == dep or not league or min(h,a)<0 or max(h,a)>25:
        raise ValueError('invalid match')
    return dict(id=str(rid),tarih=t.isoformat(),lig_kodu=league,ev_sahibi=ev,deplasman=dep,ev_gol=h,dep_gol=a)

def load_history(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    rows=data if isinstance(data,list) else data.get('matches', data.get('maclar', []))
    if not isinstance(rows,list): raise ValueError('historical matches must be list')
    converted=[];issues=Counter();seen=set()
    for row in rows:
        try:
            rec=normalize_event(row)
            key=(rec['lig_kodu'],rec['id']) if rec['id'] else (rec['lig_kodu'],rec['tarih'],rec['ev_sahibi'],rec['deplasman'])
            if key in seen: issues['duplicate']+=1;continue
            seen.add(key);converted.append(rec)
        except (TypeError,KeyError,ValueError,StopIteration,IndexError,OverflowError,AttributeError):
            issues['invalid_or_unfinished']+=1
    converted.sort(key=lambda r:(r['tarih'],r['lig_kodu'],r['ev_sahibi']))
    return converted,dict(issues)

def poisson_tail(lam,line):
    if not isfinite(lam) or lam<0: raise ValueError('invalid lambda')
    k=int(line);prob=exp(-lam);summed=prob
    for i in range(1,k+1):
        prob*=lam/i;summed+=prob
    return max(0,min(1,1-summed))

def weighted_mean(rows,key,cutoff,half_life=45):
    pairs=[]
    for m in rows:
        days=(cutoff-utc(m['tarih'])).total_seconds()/86400
        if days < 0: continue
        pairs.append((m[key],exp(-log(2)*days/half_life)))
    return sum(x*w for x,w in pairs)/sum(w for _,w in pairs) if pairs else None

def forecast(history, fixture, *, cutoff=None, min_league=25, min_team=6):
    """Uses only rows before kickoff and before availability cutoff; conservative date-only restriction.
    Without verified result-time timestamps, prior SAME-DAY scores are excluded.
    """
    kick=utc(fixture['tarih']); cutoff=utc(cutoff) if cutoff else kick
    effective=min(kick,cutoff)
    lig=fixture['lig_kodu'];home=fixture['ev_sahibi'];away=fixture['deplasman']
    if home==away or not home or not away: return {'durum':'PAS','neden':'TAKIM_GECERSIZ'}
    prev=[r for r in history if r['lig_kodu']==lig and utc(r['tarih']).date()<effective.date()]
    if len(prev)<min_league: return {'durum':'PAS','neden':'LIG_VERISI_YETERSIZ','lig_mac':len(prev)}
    ha=[r for r in prev if r['ev_sahibi']==home or r['deplasman']==home]
    aa=[r for r in prev if r['ev_sahibi']==away or r['deplasman']==away]
    if min(len(ha),len(aa))<min_team:return {'durum':'PAS','neden':'TAKIM_VERISI_YETERSIZ'}
    hg=[r for r in prev if r['ev_sahibi']==home]; ag=[r for r in prev if r['deplasman']==away]
    if min(len(hg),len(ag))<3:return {'durum':'PAS','neden':'SAHA_VERISI_YETERSIZ'}
    baseh=weighted_mean(prev,'ev_gol',effective);basea=weighted_mean(prev,'dep_gol',effective)
    if baseh is None or basea is None or min(baseh,basea)<0.15:return {'durum':'PAS','neden':'LIG_BAZI_YETERSIZ'}
    def shrink(rows,field,prior):
        val=weighted_mean(rows,field,effective)
        return (len(rows)*val+8*prior)/(len(rows)+8)
    lamh=max(.05,min(5,shrink(hg,'ev_gol',baseh)*shrink(ag,'ev_gol',baseh)/baseh))
    lama=max(.05,min(5,shrink(ag,'dep_gol',basea)*shrink(hg,'dep_gol',basea)/basea))
    total=lamh+lama
    return {'durum':'MODEL_HESAPLANDI','beklenen_gol':round(total,3),'beklenen_ev':round(lamh,3),'beklenen_dep':round(lama,3),
            'olasiliklar':{f'{l:.1f}_ust':round(100*poisson_tail(total,l),2) for l in LINES},
            'orneklem':{'lig':len(prev),'ev_saha':len(hg),'dep_saha':len(ag)},
            'uyari':'Research only; probabilities not validated or calibrated'}

def wilson(w,n):
    if not n:return None
    z=1.96;p=w/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    margin=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(100*(c-margin),2),round(100*(c+margin),2)]

def archive_report(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    rows=data if isinstance(data,list) else data.get('kayitlar',[])
    if not isinstance(rows,list):raise ValueError('archive records missing')
    stats=Counter();markets=defaultdict(lambda:Counter());ligs=defaultdict(lambda:Counter());grades=[];briers=defaultdict(list)
    for row in rows:
        if not isinstance(row,dict):stats['invalid_record']+=1;continue
        status=row.get('durum');stats[status or 'unknown']+=1
        if status!='DOGRULANDI':continue
        try:
            mac=row['mac'];total=int(row['sonuc']['toplam_gol']);start=utc(mac['tarih']);made=utc(mac['hesaplama_zamani_utc']);locked=utc(row['kilit_zamani_utc'])
            if not 0<=total<=50 or not made<start or not locked<start: raise ValueError('bad time or score')
        except (ValueError,KeyError,TypeError,OverflowError):stats['invalid_confirmed']+=1;continue
        stats['valid_confirmed']+=1
        probs=row.get('olasiliklar') or mac.get('tahmin') or {}
        for line in LINES:
            p=probs.get(f'{line:.1f}_ust')
            if isinstance(p,(int,float)) and 0<=p<=100:
                briers[f'{line:.1f}_ust'].append((p/100-int(total>line))**2)
        choice=str(row.get('kilitli_secim') or '').strip().upper().replace('Ü','U')
        if choice=='RISKLI':stats['confirmed_riskli']+=1;continue
        if choice not in {f'{x:.1f} UST' for x in LINES}:stats['confirmed_no_pick']+=1;continue
        line=float(choice.split()[0]);correct=int(total>line)
        grades.append(correct);markets[choice]['n']+=1;markets[choice]['dogru']+=correct
        league=str(mac.get('lig_kodu','BILINMIYOR'));ligs[league]['n']+=1;ligs[league]['dogru']+=correct
    return {'arsiv_toplam':len(rows),'durumlar':dict(stats),'degerlendirilen':len(grades),'dogru':sum(grades),
            'yanlis':len(grades)-sum(grades),'basari_yuzdesi':round(100*sum(grades)/len(grades),2) if grades else None,
            'guven_araligi_95':wilson(sum(grades),len(grades)),
            'pazarlar':{k:{**dict(v),'basari_yuzdesi':round(100*v['dogru']/v['n'],2),'wilson_95':wilson(v['dogru'],v['n'])} for k,v in markets.items()},
            'ligler':{k:{**dict(v),'basari_yuzdesi':round(100*v['dogru']/v['n'],2)} for k,v in ligs.items()},
            'brier':{k:round(sum(v)/len(v),5) for k,v in briers.items() if v},
            'not':'Only verified pre-match locked selections; no profitability or prospective accuracy claim'}

def backtest(history,limit=None):
    rows=history if limit is None else history[-limit:]
    valid=[];rejected=Counter()
    for idx,row in enumerate(rows):
        # full history incl preceding rows, but conservative cutoff excludes ALL same-day results
        model=forecast(history,row)
        if model['durum']!='MODEL_HESAPLANDI':rejected[model['neden']]+=1;continue
        valid.append((row,model))
    metrics={}
    for line in LINES:
        k=f'{line:.1f}_ust';n=len(valid)
        if not n:metrics[k]={'n':0};continue
        preds=[m['olasiliklar'][k]/100 for _,m in valid];y=[int(r['ev_gol']+r['dep_gol']>line) for r,_ in valid]
        metrics[k]={'n':n,'tahmin_ortalama':round(100*sum(preds)/n,2),'gercek_oran':round(100*sum(y)/n,2),
                    'brier':round(sum((p-z)**2 for p,z in zip(preds,y))/n,5),'wilson_95':wilson(sum(y),n)}
    return {'giris':len(rows),'hesaplanan':len(valid),'atlanma':dict(rejected),'cizgiler':metrics,
            'not':'Date-only results assumed known from next day, not kickoff; league/team IDs require independent review'}

def decision_audit(report, config):
    thresholds=config.get('esikler',{})
    issues=[]
    for line in LINES:
        key=f'{line:.1f}'
        val=thresholds.get(key)
        if not isinstance(val,(float,int)) or isinstance(val,bool) or not 0<=val<=100:issues.append('INVALID_THRESHOLD_'+key)
    if config.get('otomatik_secim_aktif',False):issues.append('LIVE_AUTOMATIC_SELECTION_ENABLED_REQUIRES_SEPARATE_APPROVAL')
    return {'esikler':thresholds,'uyarilar':issues,'arsiv_basari':report.get('basari_yuzdesi'),
            'karar':'SADECE_DENETIM','neden':'Model calibration, market price, and independent temporal validation required'}

def publication_guard(archive_path,panel_path):
    archive=json.loads(Path(archive_path).read_text(encoding='utf-8-sig'))
    panel=json.loads(Path(panel_path).read_text(encoding='utf-8-sig'))
    rows=archive if isinstance(archive,list) else archive.get('kayitlar',[])
    items=panel.get('tahminler',[])
    problems=[]
    if not isinstance(rows,list) or not isinstance(items,list):problems.append('NOT_LIST');return {'onay':False,'hatalar':problems}
    ids=[x.get('kimlik') for x in rows if isinstance(x,dict)]
    if len(ids)!=len(rows) or any(not x for x in ids):problems.append('INVALID_ARCHIVE_ID')
    if len(ids)!=len(set(ids)):problems.append('DUPLICATE_ARCHIVE_ID')
    if items:
        if not panel.get('olusturulma_utc'):problems.append('PANEL_TIME_MISSING')
        for item in items:
            try:
                if not utc(item['hesaplama_zamani_utc'])<utc(item['tarih']):problems.append('POST_KICKOFF_PREDICTION');break
            except (KeyError,ValueError,TypeError):problems.append('INVALID_PANEL_DATE');break
    else:problems.append('EMPTY_PANEL_NO_NEW_PUBLICATION')
    return {'onay':not problems,'hatalar':problems,'arsiv_kayit':len(rows),'panel_mac':len(items),
            'not':'Audit gate only: does not modify or publish files'}
