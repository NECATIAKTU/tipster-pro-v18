"""Read-only weekly unique fixture/prediction coverage. No fabricated matches."""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter

ROOT=Path(__file__).resolve().parent
TARGET=100

def dt(value):
    try:
        x=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return None if x.tzinfo is None else x.astimezone(timezone.utc)
    except (ValueError,TypeError):return None

def records(path):
    if not path.is_file():return []
    try:obj=json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError,OSError):return []
    if isinstance(obj,list):return obj
    if isinstance(obj,dict):
        for key in ('maclar','matches','tahminler','events'):
            if isinstance(obj.get(key),list):return obj[key]
    return []

def identity(m):
    if not isinstance(m,dict):return None
    league=str(m.get('lig_kodu') or m.get('lig') or m.get('league') or '').strip().casefold()
    home=str(m.get('ev_sahibi') or m.get('home') or m.get('home_team') or '').strip().casefold()
    away=str(m.get('deplasman') or m.get('away') or m.get('away_team') or '').strip().casefold()
    kickoff=dt(m.get('tarih') or m.get('baslama') or m.get('kickoff') or m.get('date'))
    if not (league and home and away and kickoff):return None
    return (league,home,away,kickoff.isoformat()),kickoff

def evaluate(now=None, root=ROOT):
    now=now or datetime.now(timezone.utc)
    monday=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    end=monday+timedelta(days=7)
    fixtures={}; predictions={}; skipped=Counter()
    for m in records(root/'gelecek_maclar.json'):
        parsed=identity(m)
        if not parsed:skipped['fikstur_kimlik_eksik']+=1;continue
        key,kickoff=parsed
        if monday<=kickoff<end:fixtures[key]=m
    for m in records(root/'tahminler.json'):
        parsed=identity(m)
        if not parsed:skipped['tahmin_kimlik_eksik']+=1;continue
        key,kickoff=parsed
        if not monday<=kickoff<end:continue
        created=dt(m.get('hesaplama_zamani') or m.get('olusturulma_utc') or m.get('created_at'))
        if not created or created>=kickoff or created>now:
            skipped['tahmin_zaman_dogrulanamadi']+=1;continue
        if not isinstance(m.get('tahmin'),dict) or not m['tahmin']:
            skipped['tahmin_verisi_eksik']+=1;continue
        predictions[key]=m
    return {'hafta_baslangic_utc':monday.isoformat(),'hafta_bitis_utc':end.isoformat(),
            'haftalik_hedef_farkli_mac':TARGET,'fikstur_farkli_mac':len(fixtures),
            'zaman_dogrulanmis_tahmin_farkli_mac':len(predictions),
            'hedefe_kalan':max(0,TARGET-len(predictions)),
            'hedef_karsilama_yuzdesi':round(100*len(predictions)/TARGET,2),
            'tahmin_uretilemeyen_fikstur':len(set(fixtures)-set(predictions)),
            'atlanan_kayitlar':dict(skipped),
            'uyari':'Sadece tahminler.json sayilir; diger motor arsivleri ayrica birlestirilmelidir. Gercek kaynak ve kalite garantisi degildir.'}

if __name__=='__main__':
    report=evaluate()
    (ROOT/'haftalik_kapasite_raporu.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
