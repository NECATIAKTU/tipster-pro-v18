"""TIPSTER PRO - Poland standalone test module.
No existing archives/files are modified. Requires Python 3.11+.
Source: open-matchday (non-commercial, attribution required).
"""
import csv
import io
import json
import math
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

BASE = 'https://raw.githubusercontent.com/oladeeayo/open-matchday/master/data'
LEAGUES = {
    'POL_1_ekstraklasa': 'Polonya Ekstraklasa',
    'POL_2_division-1': 'Polonya I Liga',
    'POL_3_division-2': 'Polonya II Liga',
}

def fetch_csv(folder, name):
    url = f'{BASE}/{folder}/{name}_2627.csv'
    req = Request(url, headers={'User-Agent': 'TIPSTER-PRO/1.0'})
    with urlopen(req, timeout=25) as r:
        data = r.read().decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(data)))

def parse_date(s):
    return datetime.strptime(s.strip()[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)

def prob_over(lam, line):
    k = int(line + 0.5)
    return 100 * (1 - sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k)))

def run():
    now = datetime.now(timezone.utc)
    output = {'created_utc': now.isoformat(), 'source': 'open-matchday', 'predictions': [], 'leagues': {}}
    for folder, label in LEAGUES.items():
        try:
            results = fetch_csv(folder, 'results')
            fixtures = fetch_csv(folder, 'fixtures')
            print(label, "Fikstur toplam:", len(fixtures), "Ilk tarihler:", [f.get('date') for f in fixtures[:5]])
            past = []
            for r in results:
                try:
                    d = parse_date(r['date'])
                    hg, ag = int(r['ft_home']), int(r['ft_away'])
                    if d.date() < now.date() and hg >= 0 and ag >= 0:
                        past.append((d, r['home'].strip(), r['away'].strip(), hg, ag))
                except (KeyError, ValueError, TypeError):
                    continue
            past.sort()
            count = 0
            for f in fixtures:
                try:
                    d = parse_date(f['date'])
                    # Fixture CSV time can be ambiguous; require tomorrow onward, no same-day locking.
                    if not (now.date() < d.date() <= (now + timedelta(days=7)).date()):
                        continue
                    home, away = f['home'].strip(), f['away'].strip()
                    # Strictly prior match data only, last 10 appearances per team.
                    home_hist = [(hg, ag) for dt, h, a, hg, ag in past if dt < d and h == home][-10:]
                    away_hist = [(ag, hg) for dt, h, a, hg, ag in past if dt < d and a == away][-10:]
                    record = {'league': label, 'date': f['date'], 'home': home, 'away': away,
                              'source': 'open-matchday', 'status': 'RISKLI'}
                    if len(home_hist) >= 5 and len(away_hist) >= 5:
                        h_for = sum(x for x, _ in home_hist) / len(home_hist)
                        h_against = sum(y for _, y in home_hist) / len(home_hist)
                        a_for = sum(x for x, _ in away_hist) / len(away_hist)
                        a_against = sum(y for _, y in away_hist) / len(away_hist)
                        lam = max(0.2, min(5.0, (h_for + a_against + a_for + h_against) / 2))
                        record.update({'expected_goals': round(lam, 2),
                                       'p_over_2_5_raw': round(prob_over(lam, 2.5), 1),
                                       'p_over_3_5_raw': round(prob_over(lam, 3.5), 1),
                                       'p_over_4_5_raw': round(prob_over(lam, 4.5), 1),
                                       'status': 'TEST_ONLY_UNCALIBRATED'})
                    output['predictions'].append(record)
                    count += 1
                except (KeyError, ValueError, TypeError):
                    continue
            output['leagues'][label] = {'past_results': len(past), 'future_fixtures': count, 'error': None}
        except Exception as exc:
            output['leagues'][label] = {'past_results': 0, 'future_fixtures': 0, 'error': str(exc)}
    # Never overwrite the user's existing forecast or historical records.
    with open('polonya_test_raporu.json', 'w', encoding='utf-8') as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(json.dumps(output['leagues'], ensure_ascii=False, indent=2))
    print('Tahmin adaylari:', len(output['predictions']), '| Dosya: polonya_test_raporu.json')
    print('UYARI: Olasiliklar kalibre edilmemistir, aktif bahis tahmini olarak kullanmayin.')

if __name__ == '__main__':
    run()
