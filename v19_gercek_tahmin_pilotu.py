"""Read-only V19 pilot: real ESPN fixtures and completed historical scores.

No historic prediction modifications. No guaranteed confidence/accuracy claims.
Runs in isolated review branch, does not publish to live Pages.
"""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from v19_veri_pilotu import collect_teams, utc
from gercek_tahmin_v18 import get_json
from fikstur_yeni import LIGLER
from gol_modeli import mac_analizi
from tahmin_motoru import indeks_olustur, otomatik_eslestir


def forecast(fixture, now, days=90, fetch=get_json, allowed=None):
    created = utc(fixture.get('olusturulma_utc'))
    if created is None or created > now or (now - created).total_seconds() > 6 * 3600:
        raise ValueError('Fixture stale or future-dated')
    matches = fixture.get('maclar')
    if not isinstance(matches, list):
        raise ValueError('Fixture is missing maclar array')
    grouped = defaultdict(list)
    counters = Counter()
    for match in matches:
        if not isinstance(match, dict):
            counters['invalid_fixture_record'] += 1
            continue
        kickoff = utc(match.get('tarih'))
        league = match.get('lig_kodu')
        if kickoff is None or kickoff <= now:
            counters['already_started_or_invalid_date'] += 1
        elif league not in LIGLER:
            counters['unsupported_league'] += 1
        elif allowed and league not in allowed:
            counters['pilot_scope_not_selected'] += 1
        else:
            grouped[league].append(match)
    predictions = []
    provenance = {}
    for league, items in sorted(grouped.items()):
        teams, source = collect_teams(league, now, days, fetch)
        provenance[league] = source
        if source['failure_days'] > max(2, days // 10) or source['completed_matches'] < 10:
            counters['historical_source_insufficient'] += len(items)
            continue
        index = indeks_olustur(teams)
        for match in items:
            home = otomatik_eslestir(match.get('ev_sahibi'), teams, index)
            away = otomatik_eslestir(match.get('deplasman'), teams, index)
            if not home or not away or home == away:
                counters['team_matching_failed'] += 1
                continue
            if min(teams[home]['mac'], teams[away]['mac']) < 5:
                counters['team_sample_under_5'] += 1
                continue
            try:
                odds = mac_analizi(home, away, teams)
            except (ArithmeticError, ValueError, TypeError, KeyError, ZeroDivisionError):
                counters['model_error'] += 1
                continue
            predictions.append({'id': match.get('id'), 'tarih': match['tarih'],
                'lig_kodu': league, 'lig': LIGLER[league], 'ev_sahibi': match['ev_sahibi'],
                'deplasman': match['deplasman'], 'istatistik_ev': home,
                'istatistik_deplasman': away, 'takim_mac_sayilari': [teams[home]['mac'], teams[away]['mac']],
                'model_tahmini': odds, 'kaynak': 'ESPN completed scores',
                'model_durumu': 'PILOT_KILITLENMEDI', 'guven_durumu': 'DOGRULANMADI'})
            counters['generated'] += 1
    return {'model': 'TIPSTER PRO V19 - BAGIMSIZ GERCEK VERI PILOT',
            'olusturulma_utc': now.isoformat(), 'canli_panel_degisti': False,
            'tahminler_kilitlendi': False,
            'not': 'Deneysel Poisson olasiligi; gecmis basari veya garanti degildir. Canli bahis secimi sayilmaz.',
            'lig_sayisi': len(grouped), 'kapsam': 'Pilot only; real fixture and historical ESPN scores',
            'durum': dict(counters), 'lig_kaynak_denetimi': provenance,
            'tahminler': predictions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fikstur', default='gelecek_maclar.json')
    ap.add_argument('--cikti', default='v19_pilot_tahminleri.json')
    ap.add_argument('--gecmis-gun', type=int, default=90)
    ap.add_argument('--ligler', default='', help='Comma separated ESPN league codes; blank = every league with fixtures')
    args = ap.parse_args()
    if args.gecmis_gun < 30 or args.gecmis_gun > 180:
        ap.error('History days must be within 30..180')
    dest = Path(args.cikti)
    if dest.exists():
        raise SystemExit('Output file exists; not overwriting')
    source = json.loads(Path(args.fikstur).read_text(encoding='utf-8'))
    allowed = set(filter(None, (x.strip() for x in args.ligler.split(',')))) or None
    result = forecast(source, datetime.now(timezone.utc), args.gecmis_gun, allowed=allowed)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',encoding='utf-8')
    print('V19 PILOT:', len(result['tahminler']), 'REAL FIXTURE PREDICTIONS', result['durum'])

if __name__ == '__main__':
    main()
