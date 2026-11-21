#!/usr/bin/env python3
"""ESPN lig kodu / fikstur araligi teshisi. MEVCUT VERIYE YAZMAZ.

7,14,30 gunluk periyotlari tek seferlik 30 gunluk taramadan hesaplar.
Sifir mac, gecersiz lig, API hatasi ve tarih filtresi ayrilir.
"""
import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fikstur_yeni import LIGLER

BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{}/scoreboard'
DEFAULT_CODES = ('sui.1','tur.2','irl.1','chn.1','sco.2','sco.3','pol.1','pol.2')



def fetch(code, day, timeout=15):
    url = BASE.format(code) + "?" + urlencode({
        "dates": day.strftime("%Y%m%d"),
        "limit": 500
    })

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    )

    try:
        with urlopen(req, timeout=timeout) as response:
            data = json.load(response)

    except HTTPError as exc:
        details = exc.read(500).decode(
            "utf-8", errors="replace"
        )
        print(
    f"ESPN {code} HTTP {exc.code}: {details[:120]}"
)
       raise

    if not isinstance(data, dict):
        raise ValueError("ESPN JSON nesnesi gelmedi")

    if not isinstance(data.get("events"), list):
        raise ValueError(
            "ESPN events listesi gelmedi"
        )

    return data["events"]



def audit(code, now, days, fetcher=fetch):
    end = now + timedelta(days=days)
    errors = []
    unique = {}
    event_states = Counter()
    for offset in range(days + 1):
        day = (now + timedelta(days=offset)).date()
        for attempt in range(2):
            try:
                events = fetcher(code, day)
                break
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                if attempt == 0:
                    time.sleep(.3)
                else:
                    errors.append({'gun': day.isoformat(), 'hata': str(exc)[:180]})
                    events = []
        for event in events:
            event_id = str(event.get('id') or '')
            if event_id:
                unique[event_id] = event
    windows = {}
    for window in (7, 14, 30):
        if window > days:
            continue
        allowed_end = now + timedelta(days=window)
        counts = Counter()
        for event in unique.values():
            try:
                kickoff = datetime.fromisoformat(event['date'].replace('Z','+00:00'))
                if not (now < kickoff < allowed_end):
                    counts['tarih_disi'] += 1
                    continue
                state = event.get('status', {}).get('type', {})
                if state.get('completed') or state.get('state') != 'pre':
                    counts['baslamis'] += 1
                    continue
                competitors = event['competitions'][0]['competitors']
                home = next(x for x in competitors if x.get('homeAway') == 'home')
                away = next(x for x in competitors if x.get('homeAway') == 'away')
                if not home['team'].get('displayName') or not away['team'].get('displayName'):
                    counts['eksik_takim'] += 1
                    continue
                counts['gelecek_mac'] += 1
            except (KeyError, StopIteration, IndexError, TypeError, ValueError):
                counts['bozuk_olay'] += 1
        windows[str(window)] = dict(counts)
    if len(errors) == days + 1:
        situation = 'KAYNAK_ERISIM_HATASI'
    elif unique:
        situation = 'OLAY_VAR'
    elif errors:
        situation = 'KISMEN_HATALI_SIFIR'
    else:
        situation = 'API_BOS_DONDU'
    return {'lig_kodu': code, 'lig': LIGLER.get(code, 'ADAY / TANIMSIZ'), 'api_durumu': situation,
            'benzersiz_api_olayi': len(unique), 'hatali_gun': len(errors), 'hatalar': errors[:10],
            'pencereler': windows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gun', type=int, default=30)
    ap.add_argument('--cikti', default='sifir_lig_raporu')
    ap.add_argument('--ligler', nargs='*', default=list(DEFAULT_CODES))
    args = ap.parse_args()
    if args.gun not in (7, 14, 30):
        ap.error('--gun 7, 14 veya 30 olmali')
    out = Path(args.cikti)
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    report = [audit(code, now, args.gun) for code in args.ligler]
    payload = {'olusturulma_utc': now.isoformat(), 'gun': args.gun,
               'uyari': 'Yalnizca tanisal rapor; lig eklemez, tahmin silmez, model esiklerini degistirmez.',
               'ligler': report}
    (out / 'rapor.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (out / 'rapor.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['lig_kodu','lig','api_durumu','api_olay','hatali_gun','7_gun_mac','14_gun_mac','30_gun_mac'])
        for r in report:
            w.writerow([r['lig_kodu'],r['lig'],r['api_durumu'],r['benzersiz_api_olayi'],r['hatali_gun'],
                        *[r['pencereler'].get(str(n),{}).get('gelecek_mac','') for n in (7,14,30)]])
    for r in report:
        print(r['lig_kodu'], r['api_durumu'],
              '7/14/30:', *(r['pencereler'].get(str(n),{}).get('gelecek_mac','-') for n in (7,14,30)),
              'hata_gun:', r['hatali_gun'])
    print('RAPOR:', out / 'rapor.csv')

if __name__ == '__main__':
    main()
