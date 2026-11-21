#!/usr/bin/env python3
"""TIPSTER KARTAL V1: read-only, stdlib-only independent goal-market audit.
Never edits the input or user's live TIPSTER PRO files.
"""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LINES = ("1.5", "2.5", "3.5", "4.5", "5.5", "6.5")
LEGACY_THRESHOLDS = {"1.5":75.0, **{x:65.0 for x in LINES[1:]}}


def dt(value):
    if not value: return None
    try:
        obj = datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if obj.tzinfo is None: return None
        return obj.astimezone(timezone.utc)
    except (ValueError, TypeError): return None


def prob(value):
    try:
        if isinstance(value, bool): return None
        x=float(str(value).replace('%','').replace(',','.'))
        return x if math.isfinite(x) and 0 <= x <= 100 else None
    except (ValueError, TypeError): return None


def matches(data):
    if isinstance(data,list):return data
    if isinstance(data,dict):
        for key in ('tahminler','kayitlar','maclar','records'):
            if isinstance(data.get(key),list): return data[key]
    raise ValueError('Beklenen JSON liste/tahminler/kayitlar/maclar icermiyor')


def unwrap(row):
    if not isinstance(row,dict): return None
    m = row.get('mac') if isinstance(row.get('mac'),dict) else row
    p = m.get('tahmin') if isinstance(m.get('tahmin'),dict) else m.get('olasiliklar')
    if not isinstance(p,dict):p=m
    old = row.get('olasiliklar')
    if isinstance(old,dict):p=old
    return {
       'id':str(row.get('kimlik') or m.get('id') or ''),
       'lig':str(m.get('lig_kodu') or m.get('lig') or ''),
       'ev':str(m.get('ev_sahibi') or ''), 'dep':str(m.get('deplasman') or ''),
       'tarih':m.get('tarih'),
       'hesaplama':m.get('hesaplama_zamani_utc') or m.get('hesaplama_zamani'),
       'kilit':row.get('kilit_zamani_utc'),
       'secim':row.get('kilitli_secim'),
       'durum':row.get('durum'),
       'gol': (row.get('sonuc') or {}).get('toplam_gol') if isinstance(row.get('sonuc'),dict) else None,
       'beklenen_gol':prob(p.get('beklenen_gol')),
       'p':{s:prob(p.get(s+'_ust')) for s in LINES},
    }


def valid_bet(r):
    start=dt(r['tarih']); created=dt(r['hesaplama']); lock=dt(r['kilit'])
    return bool(start and created and lock and created < start and lock < start)


def legacy_select(r,thresholds=LEGACY_THRESHOLDS):
    for line in reversed(LINES):
        p=r['p'][line]
        if p is not None and p >= thresholds[line]:return line
    return 'RISKLI'


def wilson(w,n,z=1.96):
    if not n:return None
    p=w/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(100*(c-h),2),round(100*(c+h),2)]


def metrics(rows):
    n=len(rows)
    if not n:return {'n':0,'kazanan':0,'oran':None,'wilson_95':None,'brier':None,'log_loss':None}
    wins=sum(int(y) for p,y in rows)
    bs=sum((p-y)**2 for p,y in rows)/n
    ll=-sum(y*math.log(max(1e-9,min(1-1e-9,p)))+(1-y)*math.log(max(1e-9,min(1-1e-9,1-p))) for p,y in rows)/n
    return {'n':n,'kazanan':wins,'oran':round(wins/n*100,2),'wilson_95':wilson(wins,n), 'brier':round(bs,5),'log_loss':round(ll,5)}


def calibration(rows):
    bins=defaultdict(list)
    for p,y in rows:
        idx=min(9,int(p*10));bins[idx].append((p,y))
    out=[]
    for idx,items in sorted(bins.items()):
        out.append({'aralik':f'{idx*10}-{(idx+1)*10}%', 'adet':len(items), 'ortalama_model':round(100*sum(x for x,_ in items)/len(items),2), 'gercek':round(100*sum(y for _,y in items)/len(items),2)})
    return out


def _num_goals(r):
    try:
        x=int(r['gol']);return x if x>=0 and str(r['gol']).strip() not in ('True','False') else None
    except (ValueError,TypeError):return None


def audit(records):
    data=[x for row in records if (x:=unwrap(row)) is not None]
    by_line=Counter();selected=Counter(); missing=Counter(); future=[];mono=[];badtime=[]
    for r in data:
        selected[legacy_select(r)]+=1
        for line in LINES:
            if r['p'][line] is not None and r['p'][line] >= LEGACY_THRESHOLDS[line]:by_line[line]+=1
            if r['p'][line] is None: missing[line]+=1
        nums=[r['p'][s] for s in LINES]
        if all(x is not None for x in nums) and any(a+1e-7<b for a,b in zip(nums,nums[1:])):
            mono.append(r['id'])
        if dt(r['tarih']) is None or dt(r['hesaplama']) is None or dt(r['hesaplama'])>=dt(r['tarih']):badtime.append(r['id'])
    return {'kayit':len(data),'esik_ustunde_cizgiler':dict(by_line),'eski_secim_dagilimi':dict(selected), 'olasilik_eksigi':dict(missing), 'monotonluk_ihlali':mono[:100], 'mac_oncesi_zaman_sorunu':badtime[:100], 'not':'Bu sayilar model secim simülasyonudur, kilitli tahmin basarisi degildir.'}


def backtest(records):
    data=[x for row in records if (x:=unwrap(row)) is not None]
    finished=[r for r in data if r['durum']=='DOGRULANDI' and _num_goals(r) is not None and valid_bet(r)]
    scored={line:[] for line in LINES}
    locked=Counter(); locked_selected=defaultdict(list)
    for r in finished:
        goal=_num_goals(r)
        for line in LINES:
            p=r['p'][line]
            if p is not None:scored[line].append((p/100,int(goal>float(line))))
        choice=str(r['secim'] or '').upper().replace('Ü','U').strip()
        if choice in [s+' UST' for s in LINES]:
            line=choice.split()[0]
            p=r['p'][line]
            if p is not None:
                locked_selected[line].append((p/100,int(goal>float(line))))
                locked['secilen']+=1
        elif choice=='RISKLI':locked['riskli']+=1
        else:locked['belirsiz']+=1
    return {'kilit_ve_zaman_dogrulanmis_skorlu':len(finished), 'kilitli_secim':dict(locked), 'tum_maclar_her_cizgi':{l:{'metrik':metrics(scored[l]),'kalibrasyon':calibration(scored[l])} for l in LINES}, 'sadece_kilitli_secimler':{l:metrics(locked_selected[l]) for l in LINES}, 'uyari':'Ayni macin tum cizgilerde degerlendirilmesi bagimsiz bahisler anlamina gelmez. Olasiliklar kalibre edilmemistir.'}


def discovery(records, now):
    """Discovery is a research ranking, NOT a betting recommendation or model revision."""
    data=[x for row in records if (x:=unwrap(row)) is not None]
    out=[]
    for r in data:
        kick=dt(r['tarih']); calc=dt(r['hesaplama'])
        if not kick or not calc or calc>=kick or kick<=now:continue
        if any(r['p'][x] is None for x in LINES):continue
        ps=[r['p'][x] for x in LINES]
        if any(ps[i]<ps[i+1] for i in range(5)):continue
        for line in LINES[1:]:
            p=r['p'][line]
            # Mathematical risk-neutral index: expected gol tail, not a claimed calibrated edge.
            # Threshold is purely for exploration and explicitly not a bet trigger.
            if p>=15:
                out.append({'id':r['id'],'lig':r['lig'],'ev':r['ev'],'dep':r['dep'],'tarih':r['tarih'], 'cizgi':line,'model_yuzde':p,'eski_secim':legacy_select(r), 'durum':'KESIF_INCELEME', 'not':'Kalibre edilmemis model: bahse hazir degil'})
    return sorted(out,key=lambda x:(-float(x['cizgi']),-x['model_yuzde'],x['tarih']))


def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def main(argv=None):
    ap=argparse.ArgumentParser(description='Read-only V18 audit; does not change live engine')
    ap.add_argument('--tahmin',help='v18_canli_cikti.json / panel_tahminler.json')
    ap.add_argument('--arsiv',help='v18_dogrulanan_sonuclar.json')
    ap.add_argument('--cikti-klasoru',default='kartal_rapor')
    ap.add_argument('--simdi-utc',help='Sadece offline test icin ISO UTC')
    args=ap.parse_args(argv)
    if not args.tahmin and not args.arsiv:ap.error('En az --tahmin veya --arsiv gerekli')
    out=Path(args.cikti_klasoru)
    now=dt(args.simdi_utc) if args.simdi_utc else datetime.now(timezone.utc)
    if now is None:ap.error('Gecersiz --simdi-utc')
    if args.tahmin:
        obj=json.loads(Path(args.tahmin).read_text(encoding='utf8'))
        rs=matches(obj);report=audit(rs)
        write_json(out/'01_gol_cizgisi_teshis.json',report)
        rows=discovery(rs,now)
        write_json(out/'02_yuksek_gol_kesfi.json',{'olusturma':now.isoformat(),'satirlar':rows,'aciklama':'On inceleme: bahis tavsiyesi veya kalibre model sonucu degil'})
        with (out/'02_yuksek_gol_kesfi.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['id','lig','ev','dep','tarih','cizgi','model_yuzde','eski_secim','durum','not']);w.writeheader();w.writerows(rows)
        print('Tahmin kaydi:',report['kayit'],'Eski secimler:',report['eski_secim_dagilimi'],'Kesif satiri:',len(rows))
    if args.arsiv:
        obj=json.loads(Path(args.arsiv).read_text(encoding='utf8'))
        report=backtest(matches(obj))
        write_json(out/'03_gercek_kalibrasyon.json',report)
        print('Zaman ve kilit dogrulanmis mac:',report['kilit_ve_zaman_dogrulanmis_skorlu'])
    print('Raporlar:',out)

if __name__=='__main__':main()
