#!/usr/bin/env python3
"""TIPSTER PRO TOP listeleri: maç öncesi kayıt + ESPN FT sonuç denetimi.
Yalnızca kendi dosyalarını değiştirir. Eşleşmeyen/skoru doğrulanamayan maç BEKLEMEDE kalır.
"""
import csv
import json
import os
import re
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('Europe/London')
ARCHIVE = Path('tipster_top_kilitli_tahminler.json')
REPORT_JSON = Path('tipster_top_sonuc_raporu.json')
REPORT_TXT = Path('tipster_top_sonuc_raporu.txt')
LISTS = [('GUNLUK_TOP10', Path('tipster_gunluk_top10.csv')),
         ('HAFTALIK_TOP20', Path('tipster_haftalik_top20.csv'))]
# CSV id prefixleri ESPN lig kimlikleridir; farklı kimlikleri tahmin ederek eşleştirmeyiz.
LEAGUES = {
    'arg.1','aus.1','aut.1','bel.1','bra.1','chn.1','col.1','den.1',
    'eng.1','eng.2','eng.3','eng.4','eng.5','esp.1','esp.2',
    'fra.1','fra.2','ger.1','ger.2','ita.1','ita.2','mex.1',
    'ned.1','nor.1','por.1','sco.1','sco.2','sco.3','swe.1',
    'tur.1','usa.1','jpn.1','rsa.1','gre.1',
    'uefa.champions','uefa.europa','uefa.europa.conf'
}


def parse_date(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def norm(value):
    s = str(value or '').casefold().replace('ı','i').replace('ø','o').replace('æ','ae')
    s = unicodedata.normalize('NFKD', s)
    return re.sub('[^a-z0-9]', '', ''.join(c for c in s if not unicodedata.combining(c)))


def atomic_json(path, data):
    fd, tmp = tempfile.mkstemp(prefix='.tipster_top_', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def load_archive():
    if not ARCHIVE.exists(): return []
    data = json.loads(ARCHIVE.read_text(encoding='utf-8'))
    if not isinstance(data, list): raise ValueError('Arşiv liste değil; güvenlik için durduruldu')
    return data


def capture(archive, now):
    existing = {(x['liste'],x['id'],x['tahmin'],x['tarih_utc']) for x in archive}
    count = 0
    for list_name, path in LISTS:
        if not path.exists():
            print(f'UYARI: {path} yok; mevcut arşiv korundu')
            continue
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            required = {'id','tarih_utc','mac','tahmin','model_yuzdesi'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f'{path}: eksik sütunlar')
            for row in reader:
                dt = parse_date(row.get('tarih_utc'))
                if dt is None or dt <= now: continue  # maç başladıysa geriye dönük kilitleme YOK
                match_id = (row.get('id') or '').strip()
                market = (row.get('tahmin') or '').strip().upper().replace('UST','ÜST')
                if not match_id or market not in ('2.5 ÜST','2.5 ALT','3.5 ÜST'): continue
                if list_name == 'HAFTALIK_TOP20' and market == '2.5 ALT': continue
                key = (list_name,match_id,market,dt.isoformat())
                if key in existing: continue
                try: pct = float(row['model_yuzdesi'])
                except (TypeError,ValueError): continue
                if not 0 <= pct <= 100: continue
                item = {'liste':list_name,'id':match_id,'tarih_utc':dt.isoformat(),
                        'mac':row['mac'],'tahmin':market,'model_yuzdesi':pct,
                        'kaynak':row.get('kaynak',''),'kilit_zamani_utc':now.isoformat(),
                        'durum':'BEKLEMEDE','skor':None,'dogrulama_kaynagi':None}
                archive.append(item);existing.add(key);count += 1
    return count


def event_score(event):
    status = (event.get('status') or {}).get('type') or {}
    if status.get('completed') is not True: return None
    comps = event.get('competitions') or []
    if not comps: return None
    sides = {x.get('homeAway'):x for x in comps[0].get('competitors',[])}
    h,a = sides.get('home'),sides.get('away')
    if not h or not a: return None
    try: hg,ag = int(h['score']),int(a['score'])
    except (KeyError,ValueError,TypeError): return None
    if min(hg,ag) < 0: return None
    return hg,ag,(h.get('team') or {}).get('displayName',''),(a.get('team') or {}).get('displayName','')


def check(archive, now):
    cache = {}
    checked = 0
    for item in archive:
        if item['durum'] in ('DOGRU','YANLIS'): continue
        dt = parse_date(item['tarih_utc'])
        if not dt or dt + timedelta(minutes=90) > now: continue
        match = re.fullmatch(r'([^|]+)\|(\d+)',item['id'])
        if not match: continue
        league,event_id = match.groups()
        if league not in LEAGUES: continue
        date = dt.strftime('%Y%m%d')
        key = (league,date)
        if key not in cache:
            try:
                url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date}'
                req = Request(url,headers={'User-Agent':'Mozilla/5.0'})
                with urlopen(req,timeout=15) as response:
                    payload = json.load(response)
                events = payload.get('events',[])
                cache[key] = {str(e.get('id')):e for e in events} if isinstance(events,list) else {}
            except (OSError,ValueError,TypeError) as exc:
                print(f'UYARI ESPN {league} {date}: {exc}')
                cache[key] = {}
        event = cache[key].get(event_id)
        if not event: continue
        result = event_score(event)
        if result is None: continue
        hg,ag,home,away = result
        parts = re.split(r'\s+[-–]\s+',item['mac'],maxsplit=1)
        # Event ID tek başına yeterli değil: takım adlarını da doğrula.
        if len(parts) != 2 or norm(parts[0]) != norm(home) or norm(parts[1]) != norm(away):
            continue
        total = hg+ag
        prediction = item['tahmin']
        correct = (total>=3 if prediction=='2.5 ÜST' else
                   total<=2 if prediction=='2.5 ALT' else total>=4)
        item['durum'] = 'DOGRU' if correct else 'YANLIS'
        item['skor'] = f'{hg}-{ag}'
        item['dogrulama_kaynagi'] = f'ESPN {league} event {event_id}'
        item['dogrulama_zamani_utc'] = now.isoformat()
        checked += 1
    return checked


def report(archive, now):
    groups = defaultdict(list)
    for item in archive: groups[item['liste']].append(item)
    stats = {}
    lines = [f'TIPSTER PRO TOP SONUC TAKIP | {now.isoformat()}',
             'Basari = DOGRU / (DOGRU + YANLIS); BEKLEMEDE haric.','']
    for name,_ in LISTS:
        items = groups[name]
        correct = sum(x['durum']=='DOGRU' for x in items)
        wrong = sum(x['durum']=='YANLIS' for x in items)
        pending = len(items)-correct-wrong
        rate = round(100*correct/(correct+wrong),2) if correct+wrong else None
        stats[name] = {'toplam':len(items),'dogru':correct,'yanlis':wrong,
                       'beklemede':pending,'basari_yuzdesi':rate}
        lines.append(f'{name} | TOPLAM {len(items)} | DOGRU {correct} | YANLIS {wrong} | BEKLEMEDE {pending} | BASARI {str(rate)+"%" if rate is not None else "HENUZ HESAPLANAMAZ"}')
        for x in sorted(items,key=lambda r:(r['tarih_utc'],r['id'])):
            lines.append(f"  {x['tarih_utc']} | {x['mac']} | {x['tahmin']} %{x['model_yuzdesi']:.2f} | {x['skor'] or '-'} | {x['durum']}")
        lines.append('')
    atomic_json(REPORT_JSON,{'olusturulma_utc':now.isoformat(),'ozet':stats,'kayitlar':archive})
    REPORT_TXT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return stats


def main():
    now = datetime.now(timezone.utc)
    archive = load_archive()
    added = capture(archive,now)
    verified = check(archive,now)
    atomic_json(ARCHIVE,archive)
    stats = report(archive,now)
    print(f'TOP SONUC TAKIP: yeni kilit {added} | dogrulanan {verified} | arsiv {len(archive)}')
    for k,v in stats.items(): print(f'{k}: {v}')


if __name__=='__main__': main()
