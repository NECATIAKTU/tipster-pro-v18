#!/usr/bin/env python3
"""TIPSTER NECATI: denetlenebilir günlük TOP10 ve 7 günlük TOP20.
CSV'den okur; tarih, olasılık tutarlılığı, tekrar ve model eşiklerini denetler.
Yalnızca seçilen rapor dosyalarını yazar. Yüzdeler model tahminidir.
"""
import argparse, csv, json, math, os, tempfile, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ZONE=ZoneInfo('Europe/London')
FIELDS=['sira','tarih_londra','tarih_utc','mac','tahmin','model_yuzdesi','kaynak','id']
MARKETS=[('3.5 ÜST','3.5_ust',65),('2.5 ÜST','2.5_ust',65),('1.5 ÜST','1.5_ust',75)]

def parse_dt(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError,OverflowError): return None

def pct(value):
    try:
        if isinstance(value,bool): return None
        x=float(value)
        return x if math.isfinite(x) and 0<=x<=100 else None
    except (ValueError,TypeError): return None

def read_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f)
        needed={'id','tarih_utc','kaynak','mac','1.5_ust','2.5_ust','3.5_ust'}
        if not needed.issubset(r.fieldnames or []):
            raise ValueError('Eksik CSV sutunlari: '+', '.join(sorted(needed-set(r.fieldnames or []))))
        return list(r)

def choose(rows,start,end,limit,now=None):
    now=now or datetime.now(timezone.utc)
    valid=[]; rejected={}
    def reject(reason): rejected[reason]=rejected.get(reason,0)+1
    for r in rows:
        when=parse_dt(r.get('tarih_utc'))
        if when is None: reject('gecersiz_tarih');continue
        if when<=now: reject('baslamis_mac');continue
        if not start<=when.astimezone(ZONE)<end: continue
        if not r.get('mac','').strip() or not r.get('kaynak','').strip(): reject('eksik_mac_kaynak');continue
        if not r.get('id','').strip(): reject('eksik_kimlik');continue
        values={k:pct(r.get(k)) for k in ('1.5_ust','2.5_ust','3.5_ust')}
        if any(v is None for v in values.values()): reject('gecersiz_olasilik');continue
        if not(values['1.5_ust']>=values['2.5_ust']>=values['3.5_ust']): reject('tutarsiz_olasilik');continue
        computed=r.get('hesaplama_zamani') or r.get('hesaplama_zamani_utc')
        if computed:
            created=parse_dt(computed)
            if created is None or created>=when or created>now: reject('gecersiz_tahmin_zamani');continue
        else:
            # Without an auditable calculation time, never publish as verified pre-match.
            reject('zaman_dogrulanamadi');continue
        # Bir maç için yalnızca en yüksek gol çizgisindeki yeterli olasılığı kullan.
        options=[(market,values[key],threshold) for market,key,threshold in MARKETS if values[key]>=threshold]
        if not options: reject('esik_alti_riskli');continue
        market,prob,_=options[0]
        # 3.5'e ulaşabilen adaylar, aynı yüzdeli daha düşük çizgilerden önce gelir.
        rank={'3.5 ÜST':3,'2.5 ÜST':2,'1.5 ÜST':1}[market]
        key=(when.isoformat()+'|'+re.sub(r'\s+', ' ', r['mac'].strip().casefold()))
        valid.append((key,prob,rank,when,r,market))
    # Tekrarlı kayıtlar için en iyi olasılığı seçmek yerine deterministik ilk kaydı tut.
    valid.sort(key=lambda x:(x[3],x[4].get('kaynak',''),x[4].get('mac',''),-x[1]))
    unique={}
    for item in valid:
        if item[0] not in unique: unique[item[0]]=item
        else: reject('mukerrer_mac')
    candidates=sorted(unique.values(),key=lambda x:(-x[1],-x[2],x[3],x[0]))[:limit]
    out=[]
    for i,(_,p,_,when,r,market) in enumerate(candidates,1):
        out.append({'sira':i,'tarih_londra':when.astimezone(ZONE).strftime('%Y-%m-%d %H:%M %Z'),
            'tarih_utc':when.isoformat(),'mac':r['mac'].strip(),'tahmin':market,
            'model_yuzdesi':f'{p:.2f}','kaynak':r['kaynak'].strip(),'id':r.get('id','').strip()})
    return out,rejected,len(unique)

def atomic_write(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f: f.write(content)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def save(out,prefix,title,directory):
    import io
    buf=io.StringIO(newline=''); w=csv.DictWriter(buf,fieldnames=FIELDS);w.writeheader();w.writerows(out)
    atomic_write(directory/(prefix+'.csv'),'\ufeff'+buf.getvalue())
    lines=[title,'Model olasiliklari; dogrulanmis basari yuzdesi degildir.',f'Bulunan aday: {len(out)}','']
    lines.extend(f"{r['sira']:>2}. {r['tarih_londra']} | {r['mac']} | {r['tahmin']} %{r['model_yuzdesi']}" for r in out)
    atomic_write(directory/(prefix+'.txt'),'\n'.join(lines)+'\n')

def run(rows,date,now=None):
    now=now or datetime.now(timezone.utc)
    base=datetime.combine(date,datetime.min.time(),ZONE)
    day,dr,dc=choose(rows,base,base+timedelta(days=1),10,now)
    week,wr,wc=choose(rows,base,base+timedelta(days=7),20,now)
    return day,week,{'olusturulma_utc':now.isoformat(),'gunluk':{'aday':dc,'secilen':len(day),'reddedilen':dr},'haftalik':{'aday':wc,'secilen':len(week),'reddedilen':wr},'not':'Model olasiligi dogrulanmis basari degildir. Kaynak CSV hesaplama zamani vermiyorsa secim reddedilir. Canli fikstur teyidi bu modulun disindadir.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='tipster_yuzdelik_rapor.csv');ap.add_argument('--date');ap.add_argument('--output-dir',default='.')
    args=ap.parse_args();date=datetime.strptime(args.date,'%Y-%m-%d').date() if args.date else datetime.now(ZONE).date()
    rows=read_rows(Path(args.input));day,week,audit=run(rows,date)
    dest=Path(args.output_dir)
    save(day,'tipster_gunluk_top10',f'TIPSTER NECATI GUNLUK TOP 10 | {date} (Londra)',dest)
    save(week,'tipster_haftalik_top20',f'TIPSTER NECATI 7 GUNLUK TOP 20 | {date} - {date+timedelta(days=6)} (Londra)',dest)
    atomic_write(dest/'tipster_top_secim_denetimi.json',json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(f'GUNLUK TOP10: {len(day)} | HAFTALIK TOP20: {len(week)} | GIRIS: {len(rows)}')
if __name__=='__main__': main()
