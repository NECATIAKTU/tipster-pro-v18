"""TIPSTER PRO V19 — ücretsiz lig kapsamı denetimi; yalnızca okur.

ESPN scoreboard: şifresiz kamuya açık uç nokta (resmî API/SLA garantisi yok).
Football-Data.co.uk: ücretsiz CSV (yalnızca geçmiş sonuçları doğrular).
Bu modül motoru, arşivi, paneli veya kaynak fikstürü değiştirmez.
"""
import argparse
import csv
import io
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CATALOG = Path(__file__).with_name('ligler.json')
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{}/scoreboard'
FD = 'https://www.football-data.co.uk/mmz4281/{}/{}.csv'


def get_bytes(url, timeout=15):
    with urlopen(Request(url, headers={'User-Agent': 'TIPSTER-V19-free-league-audit/1.0'}), timeout=timeout) as resp:
        return resp.read()


def parse_espn(payload, now, day_horizons=(7, 14, 30)):
    if not isinstance(payload, list):
        raise ValueError('ESPN events listesi bekleniyordu')
    result = {str(n): 0 for n in day_horizons}
    seen = set()
    for e in payload:
        if not isinstance(e, dict) or not e.get('id'):
            continue
        ident = str(e['id'])
        if ident in seen:
            continue
        seen.add(ident)
        try:
            dt = datetime.fromisoformat(e['date'].replace('Z', '+00:00'))
            if dt.tzinfo is None:
                continue
            status = e.get('status', {}).get('type', {})
            competitors = e['competitions'][0]['competitors']
            sides = {c.get('homeAway'): c.get('team', {}).get('displayName', '').strip() for c in competitors}
            if status.get('completed') or status.get('state') != 'pre' or not sides.get('home') or not sides.get('away'):
                continue
            for days in day_horizons:
                if now < dt.astimezone(timezone.utc) < now + timedelta(days=days):
                    result[str(days)] += 1
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            continue
    return result


def check_espn(code, now, horizon, fetch=get_bytes, pause=0):
    events = {}
    errors = []
    successes = 0
    for step in range(horizon + 1):
        day = (now + timedelta(days=step)).date().strftime('%Y%m%d')
        url = ESPN.format(code) + '?' + urlencode({'dates': day, 'limit': 500})
        try:
            data = json.loads(fetch(url).decode('utf-8'))
            if not isinstance(data, dict) or not isinstance(data.get('events'), list):
                raise ValueError('invalid ESPN events format')
            successes += 1
            for event in data['events']:
                if isinstance(event, dict) and event.get('id') is not None:
                    events[str(event['id'])] = event
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append({'gun': day, 'hata': type(exc).__name__ + ': ' + str(exc)[:120]})
        if pause:
            time.sleep(pause)
    return {'basarili_gun': successes, 'hatali_gun': len(errors), 'hatalar': errors[:5],
            'api_olay_sayisi': len(events), 'fikstur': parse_espn(list(events.values()), now),
            'durum': 'ERISIM_YOK' if successes == 0 else ('KISMI_HATA' if errors else ('OLAY_VAR' if events else 'BOS_YANIT'))}


def check_csv(division, season, fetch=get_bytes):
    url = FD.format(season, division)
    try:
        raw = fetch(url)
        if not raw or b'<html' in raw[:200].lower():
            raise ValueError('CSV olmayan yanit')
        rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig', errors='replace')))
        cols = set(rows.fieldnames or ())
        if not {'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'}.issubset(cols):
            raise ValueError('Eksik CSV kolonlari')
        valid = 0
        for row in rows:
            if row.get('Date') and row.get('HomeTeam') and row.get('AwayTeam'):
                try:
                    if int(row['FTHG']) >= 0 and int(row['FTAG']) >= 0:
                        valid += 1
                except (ValueError, TypeError):
                    pass
        return {'durum': 'GECMIS_SONUC_VAR' if valid else 'GECMIS_SONUC_YOK', 'skorlu_mac': valid, 'url': url}
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        return {'durum': 'DOGRULANAMADI', 'hata': type(exc).__name__ + ': ' + str(exc)[:140], 'url': url}


def run(now, horizon=30, season='2627', fetch=get_bytes, include_candidates=False, pause=0):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    leagues = list(catalog['sifir_fikstur'])
    if include_candidates:
        leagues += catalog['yeni_adaylar']
    out = []
    for league in leagues:
        row = dict(league)
        code = league.get('espn_kodu')
        if code:
            row['espn'] = check_espn(code, now, horizon, fetch=fetch, pause=pause)
        else:
            row['espn'] = {'durum': 'KOD_DOGRULANMADI'}
        if 'football_data_csv' in league:
            row['gecmis_csv'] = check_csv(league['football_data_csv'], season, fetch=fetch)
        row['tahmin_motoruna_bagli'] = False
        out.append(row)
    return {'olusturulma_utc': now.isoformat(), 'pencere_gun': horizon,
            'not': 'Salt okunur kaynak testi; 0 mac ligin olmadigini kanitlamaz. Yeni tahmin uretilmedi.',
            'ligler': out}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gun', type=int, choices=[7,14,30], default=30)
    parser.add_argument('--sezon', default='2627')
    parser.add_argument('--adaylari-goster', action='store_true')
    parser.add_argument('--cikti', default='v19_ucretsiz_lig_raporu.json')
    parser.add_argument('--aralik', type=float, default=0.03)
    args = parser.parse_args()
    if not args.sezon.isdigit() or len(args.sezon) != 4 or args.aralik < 0:
        parser.error('Gecersiz sezon veya istek araligi')
    result = run(datetime.now(timezone.utc), args.gun, args.sezon,
                 include_candidates=args.adaylari_goster, pause=args.aralik)
    path = Path(args.cikti)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for r in result['ligler']:
        e = r['espn']
        print(r['ad'], 'ESPN:', e['durum'], 'fikstur:', e.get('fikstur', {}),
              'CSV:', r.get('gecmis_csv', {}).get('durum', '-'))
    print('RAPOR:', path)


if __name__ == '__main__':
    main()
