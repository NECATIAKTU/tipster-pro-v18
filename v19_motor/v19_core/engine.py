"""Leakage-safe match pregame goal forecasting research engine (stdlib only)."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import math

LINES=(1.5,2.5,3.5,4.5,5.5,6.5)

def utc(value):
    if isinstance(value,datetime): d=value
    else:
        if not value: raise ValueError('Eksik UTC tarih')
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('Timezone olmadan tarih kabul edilmez')
    return d.astimezone(timezone.utc)

def poisson_tail(lam,line):
    if not math.isfinite(lam) or lam < 0: raise ValueError('Gecersiz lambda')
    k=int(line); p=math.exp(-lam); acc=p
    for i in range(1,k+1): p=p*lam/i; acc+=p
    return max(0.,min(1.,1.-acc))

def normalize_match(m):
    t=utc(m['tarih']); h=str(m['ev_sahibi']).strip(); a=str(m['deplasman']).strip()
    league=str(m['lig_kodu']).strip()
    hg=int(m['ev_gol']);ag=int(m['dep_gol'])
    if not h or not a or h==a or not league or min(hg,ag)<0 or max(hg,ag)>25:
        raise ValueError('Gecersiz skor/takim/lig')
    return {'tarih':t,'ev_sahibi':h,'deplasman':a,'lig_kodu':league,'ev_gol':hg,'dep_gol':ag}

def sanitize(events):
    seen=set();clean=[];issues=defaultdict(int)
    for row in events:
        try:
            m=normalize_match(row)
            key=(m['tarih'],m['lig_kodu'],m['ev_sahibi'],m['deplasman'])
            if key in seen:
                issues['mukerrer']+=1;continue
            seen.add(key);clean.append(m)
        except (ValueError,TypeError,KeyError,OverflowError):issues['gecersiz']+=1
    clean.sort(key=lambda m:(m['tarih'],m['lig_kodu'],m['ev_sahibi'],m['deplasman']))
    return clean,dict(issues)

def weighted_mean(games,goal_key,now,half_life=45):
    weights=[math.exp(-math.log(2)*max(0,(now-x['tarih']).total_seconds()/86400)/half_life) for x in games]
    w=sum(weights)
    return sum(x[goal_key]*weight for x,weight in zip(games,weights))/w if w else None

def forecast(events,fixture,min_league=25,min_team=6,prior_strength=8,half_life=45):
    """All events must be finished strictly BEFORE fixture kickoff; rolling evaluator supplies cutoff."""
    kick=utc(fixture['tarih']);lig=str(fixture['lig_kodu'])
    home=str(fixture['ev_sahibi']).strip();away=str(fixture['deplasman']).strip()
    if not home or not away or home==away: return {'durum':'PAS','neden':'TAKIM_KIMLIGI_GECERSIZ'}
    prev=[m for m in events if m['lig_kodu']==lig and m['tarih']<kick]
    if len(prev)<min_league: return {'durum':'PAS','neden':'LIG_VERISI_YETERSIZ','lig_mac':len(prev)}
    home_all=[x for x in prev if x['ev_sahibi']==home or x['deplasman']==home]
    away_all=[x for x in prev if x['ev_sahibi']==away or x['deplasman']==away]
    if min(len(home_all),len(away_all))<min_team:
        return {'durum':'PAS','neden':'TAKIM_VERISI_YETERSIZ','ev_mac':len(home_all),'dep_mac':len(away_all)}
    hg=[x for x in prev if x['ev_sahibi']==home];ag=[x for x in prev if x['deplasman']==away]
    if min(len(hg),len(ag))<3: return {'durum':'PAS','neden':'SAHA_ORNEKLEMI_YETERSIZ','ev_saha':len(hg),'dep_saha':len(ag)}
    home_base=weighted_mean(prev,'ev_gol',kick,half_life)
    away_base=weighted_mean(prev,'dep_gol',kick,half_life)
    if home_base is None or away_base is None or min(home_base,away_base)<0.15:
        return {'durum':'PAS','neden':'LIG_GOL_BAZI_GUVENSIZ'}
    def shrink(arr,key,prior):
        # sample-size weighted prior protects small samples from extreme estimates
        measured=weighted_mean(arr,key,kick,half_life)
        return (len(arr)*measured+prior_strength*prior)/(len(arr)+prior_strength)
    home_scored=shrink(hg,'ev_gol',home_base)
    away_conceded=shrink(ag,'ev_gol',home_base)
    away_scored=shrink(ag,'dep_gol',away_base)
    home_conceded=shrink(hg,'dep_gol',away_base)
    # league-average relative attack vs opposing defense; no arbitrary upward boost
    lh=max(.05,min(5.,home_scored*away_conceded/home_base))
    la=max(.05,min(5.,away_scored*home_conceded/away_base))
    total=lh+la
    probs={f'{l:.1f}_ust':round(100*poisson_tail(total,l),2) for l in LINES}
    return {'durum':'MODEL_HESAPLANDI','beklenen_ev':round(lh,3),'beklenen_deplasman':round(la,3),
            'beklenen_gol':round(total,3),'olasiliklar':probs,'veri':{'lig_mac':len(prev),
            'ev_toplam':len(home_all),'dep_toplam':len(away_all),'ev_saha':len(hg),'dep_saha':len(ag)},
            'model':'V19_DENEYSEL_SHRINKAGE_POISSON','uyari':'Kalibrasyon ve saha testi olmadan kesin oran degildir.'}

def select(model,thresholds=None,min_home_away=3):
    """Select highest line only if calibrated thresholds are explicitly supplied.
    In research mode, no real picks are made. Never defaults to a 1.5 pick.
    """
    if model.get('durum')!='MODEL_HESAPLANDI':return {'karar':'PAS','neden':model.get('neden','MODEL_YOK')}
    if thresholds is None:return {'karar':'INCELEME','neden':'KALIBRASYON_ONAYI_YOK'}
    if min(model['veri']['ev_saha'],model['veri']['dep_saha'])<min_home_away:
        return {'karar':'PAS','neden':'SAHA_YETERSIZ'}
    for l in reversed(LINES):
        key=f'{l:.1f}';p=model['olasiliklar'].get(key+'_ust')
        if p is not None and key in thresholds and p>=thresholds[key]:
            return {'karar':key+' UST','model_yuzde':p,'neden':'DENEYSEL_ESIK'}
    return {'karar':'RISKLI','neden':'ESIK_ALTINDA'}

def walk_forward(raw, min_league=25,min_team=6,limit=None):
    """Chronological backtest; same-timestamp matches never train on each other."""
    matches,issues=sanitize(raw)
    if limit is not None:matches=matches[-limit:]
    scored=[];skips=defaultdict(int)
    for i,m in enumerate(matches):
        # Strictly preceding events, NOT inclusive; no future score leakage
        earlier=[e for e in matches[:i] if e['tarih']<m['tarih']]
        r=forecast(earlier,m,min_league=min_league,min_team=min_team)
        if r['durum']!='MODEL_HESAPLANDI':skips[r['neden']]+=1;continue
        total=m['ev_gol']+m['dep_gol']
        scored.append({'lig':m['lig_kodu'],'tarih':m['tarih'].isoformat(),'ev':m['ev_sahibi'],
                       'dep':m['deplasman'],'gercek_gol':total,'lambda':r['beklenen_gol'],'p':r['olasiliklar']})
    metrics={}
    for l in LINES:
        key=f'{l:.1f}_ust'; n=len(scored)
        if n:
            obs=sum(x['gercek_gol']>l for x in scored)/n
            pred=sum(x['p'][key]/100 for x in scored)/n
            brier=sum((x['p'][key]/100-int(x['gercek_gol']>l))**2 for x in scored)/n
            metrics[key]={'n':n,'ortalama_model':round(pred*100,2),'gercek':round(obs*100,2),'brier':round(brier,5)}
        else:metrics[key]={'n':0,'durum':'ORNEK_YOK'}
    return {'giris':len(matches),'hesaplanan':len(scored),'atlanma':dict(skips),'veri_sorunlari':issues,
            'metrikler':metrics,'not':'Gecmise donuk model denetimi. Canli basari garantisi yok.'}
