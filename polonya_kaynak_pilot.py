#!/usr/bin/env python3
"""TIPSTER V18: salt okunur Polonya kaynak pilotu; tahmin uretmez.
Yalnizca football-data.co.uk Ekstraklasa gecmis CSV dosyasini indirir,
semayi kontrol eder ve raporlar. Dig(er) liglere veri atamaz.
"""
import argparse
import csv
import io
import json
import hashlib
from collections import Counter
from datetime import datetime, date, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = 'https://football-data.co.uk/new/POL.csv'
REQUIRED = ('Date', 'Home', 'Away', 'HG', 'AG')
MAX_BYTES = 12_000_000

def parse_date(value):
    value = (value or '').strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None

def parse_score(value):
    try:
        n = int(str(value).strip())
        return n if 0 <= n <= 30 else None
    except (ValueError, TypeError):
        return None

def parse_csv(content, today):
    raw = content.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(raw))
    columns = set(reader.fieldnames or [])
    variants = [
        {'Date':'Date','Home':'Home','Away':'Away','HG':'HG','AG':'AG'},
        {'Date':'Date','Home':'HomeTeam','Away':'AwayTeam','HG':'FTHG','AG':'FTAG'},
    ]
    layout = next((v for v in variants if all(v[x] in columns for x in REQUIRED)), None)
    if layout is None:
        raise ValueError('Beklenmeyen CSV basliklari: ' + ', '.join(sorted(columns)[:30]))
    unique = {}
    issues = Counter()
    for row in reader:
        matchdate = parse_date(row.get(layout['Date']))
        home = (row.get(layout['Home']) or '').strip()
        away = (row.get(layout['Away']) or '').strip()
        hg = parse_score(row.get(layout['HG']))
        ag = parse_score(row.get(layout['AG']))
        if not matchdate or not home or not away or home.casefold() == away.casefold():
            issues['gecersiz_satir'] += 1
            continue
        if matchdate > today:
            issues['gelecek_olay_ayrildi'] += 1
            continue
        if hg is None or ag is None:
            issues['sonuc_eksik'] += 1
            continue
        identity = (matchdate.isoformat(), home.casefold(), away.casefold())
        if identity in unique:
            issues['tekrar'] += 1
        unique[identity] = dict(tarih=matchdate.isoformat(), ev_sahibi=home,
                                deplasman=away, ev_gol=hg, dep_gol=ag,
                                lig_kodu='pol.1', veri_kaynagi=SOURCE)
    games = sorted(unique.values(), key=lambda x: (x['tarih'], x['ev_sahibi']))
    return games, dict(issues)

def download(url=SOURCE):
    req = Request(url, headers={'User-Agent':'TIPSTER-V18-Poland-Source-Audit/1.0','Accept':'text/csv,*/*'})
    with urlopen(req, timeout=25) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('CSV boyutu limit ustu')
    return data

def run(outdir, input_path=None):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    report = {'olusturulma_utc':datetime.now(timezone.utc).isoformat(),
              'kaynak':SOURCE, 'lig':'Polonya Ekstraklasa',
              'canli_sisteme_etki':'YOK', 'i_liga':'AYRI KAYNAK GEREKLI',
              'fikstur':'BU KAYNAKLA DOGRULANMADI'}
    try:
        payload = Path(input_path).read_bytes() if input_path else download()
        matches, issues = parse_csv(payload, datetime.now(timezone.utc).date())
        report.update(durum='CSV_OK', toplam_gecmis_mac=len(matches),
                      dosya_sha256=hashlib.sha256(payload).hexdigest(),
                      son_mac_tarihi=matches[-1]['tarih'] if matches else None,
                      sorunlar=issues, son_90_gun=sum(
                          (datetime.now(timezone.utc).date() - date.fromisoformat(m['tarih'])).days <= 90
                          for m in matches))
        with (outdir/'polonya_ekstraklasa_gecmis.json').open('w', encoding='utf-8') as f:
            json.dump({'kayitlar':matches,'kaynak':SOURCE}, f, ensure_ascii=False, indent=2)
        with (outdir/'polonya_ekstraklasa_gecmis.csv').open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['tarih','ev_sahibi','deplasman','ev_gol','dep_gol','lig_kodu','veri_kaynagi'])
            writer.writeheader(); writer.writerows(matches)
    except Exception as exc:
        report.update(durum='KAYNAK_HATASI', hata=f'{type(exc).__name__}: {exc}')
    (outdir/'polonya_kaynak_raporu.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['durum'] == 'CSV_OK' else 1

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--cikti', default='polonya_pilot_raporu')
    p.add_argument('--yerel-csv', default=None)
    a=p.parse_args()
    raise SystemExit(run(a.cikti, a.yerel_csv))
