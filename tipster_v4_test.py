"""TIPSTER PRO V4 - independent, experimental pre-match shadow model.

Reads V2 predictions and finished matches from football-data.co.uk (current season).
Writes new files only; never edits V2/V3 results or archives.
Uses strictly matches dated before each fixture; no hindsight on completed fixtures.
"""
import csv
import io
import json
import math
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

V2 = Path('tipster_v2_sonuc.json')
OUT = Path('tipster_v4_test.json')
TXT = Path('tipster_v4_rapor.txt')
SEASON = '2627'
PRIOR_GAMES = 5.0
MIN_TEAM_MATCHES = 5
THRESHOLDS = [(6, 55), (5, 55), (4, 55), (3, 60), (2, 65), (1, 75)]


def parse_date(s):
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            pass
    return None


def fetch_league(code):
    if not (isinstance(code, str) and code.isalnum()):
        raise ValueError('Invalid league code')
    url = f'https://www.football-data.co.uk/mmz4281/{SEASON}/{code}.csv'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
    matches = []
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig', errors='replace'))):
        try:
            date = parse_date(row.get('Date'))
            home, away = (row.get('HomeTeam') or '').strip(), (row.get('AwayTeam') or '').strip()
            hg, ag = int(row['FTHG']), int(row['FTAG'])
            if not date or not home or not away or home == away or min(hg, ag) < 0:
                continue
            matches.append((date, home, away, hg, ag))
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(matches, key=lambda m: m[0]), url


def pct_over(lam, limit):
    term = math.exp(-lam)
    cumulative = term
    for k in range(1, limit + 1):
        term *= lam / k
        cumulative += term
    return round(100 * max(0, min(1, 1 - cumulative)), 2)


def smoothed(goals, count, prior_mean):
    return (goals + PRIOR_GAMES * prior_mean) / (count + PRIOR_GAMES)


def model(history, fixture_day, home, away):
    # Exclude matches played on or after kickoff date; avoids same-day leakage.
    past = [m for m in history if m[0] < fixture_day]
    if len(past) < 15:
        return None, 'LIG_GECMISI_YETERSIZ'
    n = len(past)
    league_home = sum(m[3] for m in past) / n
    league_away = sum(m[4] for m in past) / n
    if league_home <= 0 or league_away <= 0:
        return None, 'LIG_GOL_ORTALAMASI_GECERSIZ'

    stats = defaultdict(lambda: {'total': 0, 'h_n': 0, 'h_for': 0, 'h_against': 0,
                                  'a_n': 0, 'a_for': 0, 'a_against': 0})
    forms = defaultdict(list)
    for _, h, a, hg, ag in past:
        hs, aw = stats[h], stats[a]
        hs['total'] += 1
        hs['h_n'] += 1; hs['h_for'] += hg; hs['h_against'] += ag
        aw['total'] += 1
        aw['a_n'] += 1; aw['a_for'] += ag; aw['a_against'] += hg
        forms[h].append((hg, ag))
        forms[a].append((ag, hg))
    h, a = stats.get(home), stats.get(away)
    if not h or not a or min(h['total'], a['total']) < MIN_TEAM_MATCHES:
        return None, 'TAKIM_GECMISI_YETERSIZ'

    h_attack = smoothed(h['h_for'], h['h_n'], league_home)
    h_defence = smoothed(h['h_against'], h['h_n'], league_away)
    a_attack = smoothed(a['a_for'], a['a_n'], league_away)
    a_defence = smoothed(a['a_against'], a['a_n'], league_home)
    lam_home = h_attack * a_defence / league_home
    lam_away = a_attack * h_defence / league_away

    # Small, bounded correction for last five played matches; experimental.
    if len(forms[home]) >= 3 and len(forms[away]) >= 3:
        h_recent = forms[home][-5:]
        a_recent = forms[away][-5:]
        h_scored = sum(x[0] for x in h_recent) / len(h_recent)
        a_allowed = sum(x[1] for x in a_recent) / len(a_recent)
        a_scored = sum(x[0] for x in a_recent) / len(a_recent)
        h_allowed = sum(x[1] for x in h_recent) / len(h_recent)
        form_home = (h_scored + a_allowed) / 2
        form_away = (a_scored + h_allowed) / 2
        lam_home = 0.85 * lam_home + 0.15 * form_home
        lam_away = 0.85 * lam_away + 0.15 * form_away

    lam_home = max(0.05, min(4.0, lam_home))
    lam_away = max(0.05, min(4.0, lam_away))
    lam = lam_home + lam_away
    over = {f'{k}.5_ust': pct_over(lam, k) for k in range(1, 7)}
    over['7_plus_gol'] = over['6.5_ust']
    btts = round(100 * (1 - math.exp(-lam_home)) * (1 - math.exp(-lam_away)), 2)
    goal_decision = 'GOL VAR' if btts >= 55 else ('GOL YOK' if btts <= 45 else 'RISKLI')
    over_decision = next((f'{k}.5 UST' for k, threshold in THRESHOLDS
                          if over[f'{k}.5_ust'] >= threshold), 'RISKLI')
    return {'beklenen_ev': round(lam_home, 3), 'beklenen_dep': round(lam_away, 3),
            'beklenen_toplam': round(lam, 3), 'ust_olasiliklari': over,
            'gol_var_olasilik': btts, 'gol_yok_olasilik': round(100 - btts, 2),
            'gol_var_yok_karari': goal_decision, 'ust_karari': over_decision,
            'lig_gecmis_mac': n, 'ev_gecmis_mac': h['total'], 'dep_gecmis_mac': a['total']}, None


def main():
    source = json.loads(V2.read_text(encoding='utf-8'))
    predictions = source.get('predictions', [])
    if not isinstance(predictions, list):
        raise ValueError('V2 predictions is not a list')
    now = datetime.now(timezone.utc)
    cache = {}
    errors = {}
    decisions = []
    counts = Counter()
    for p in predictions:
        row = {k: p.get(k) for k in ('id', 'tarih', 'lig', 'ev', 'dep')}
        row['v4_created_at_utc'] = now.isoformat()
        try:
            kickoff = datetime.fromisoformat(str(p['tarih']).replace('Z', '+00:00'))
            if kickoff.tzinfo is None or kickoff.astimezone(timezone.utc) <= now:
                raise ValueError('NOT_PREMATCH')
            code = p['lig']
            if code not in cache and code not in errors:
                try:
                    cache[code] = fetch_league(code)
                except Exception as exc:
                    errors[code] = f'{type(exc).__name__}: {str(exc)[:100]}'
            if code in errors:
                row.update({'karar': 'VERI EKSIK', 'neden': 'LIG_VERISI_ALINAMADI', 'hata': errors[code]})
            else:
                result, problem = model(cache[code][0], kickoff.date(),
                                        p['eslesen_ev'], p['eslesen_dep'])
                if problem:
                    row.update({'karar': 'VERI EKSIK', 'neden': problem})
                else:
                    row.update({'karar': result['ust_karari'], 'v4': result,
                                'veri_kaynagi': cache[code][1]})
        except (KeyError, TypeError, ValueError) as exc:
            row.update({'karar': 'KONTROL DISI', 'neden': str(exc)})
        counts[row['karar']] += 1
        decisions.append(row)
    output = {'created_at_utc': now.isoformat(), 'model': 'V4_SHADOW_EXPERIMENTAL',
              'aciklama': 'No existing archives modified. Experimental, not validated.',
              'v2_analyzed': len(predictions), 'v4_evaluated': len(decisions),
              'counts': dict(counts), 'source_errors': errors, 'matches': decisions}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = ['TIPSTER PRO V4 - GOL MODELI TEST',
              f'UTC: {now.isoformat()}', f'V2 ANALIZ: {len(predictions)}',
              f'V4 KAYIT: {len(decisions)}', 'DENEYSEL - GERCEK BASARI ORANI DEGIL',
              *[f'{k}: {v}' for k, v in counts.most_common()]]
    TXT.write_text('\n'.join(report) + '\n', encoding='utf-8')
    print('\n'.join(report))


if __name__ == '__main__':
    main()
