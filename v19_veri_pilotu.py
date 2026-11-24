"""V19 independent read-only football data and prediction-archive audit pilot.

This module never edits the V18 prediction engine, existing archive, or panel.
No betting profitability claims. ESPN source calls need authorization and availability.
"""
import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LINES = ('1.5', '2.5', '3.5', '4.5', '5.5', '6.5')


def utc(text):
    if not isinstance(text, str):
        return None
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo is not None else None
    except ValueError:
        return None


def empty_team():
    return {'mac': 0, 'attigi': 0, 'yedigi': 0, 'ev_mac': 0,
            'ev_attigi': 0, 'ev_yedigi': 0, 'dep_mac': 0,
            'dep_attigi': 0, 'dep_yedigi': 0, 'son_maclar': []}


def collect_teams(league, now, days, fetch):
    """Collect completed pre-cutoff ESPN events, chronological home/away/form stats.

    fetch(league, date) is injected for offline, deterministic tests.
    Does not substitute fabricated matches for source failures.
    """
    events = {}
    failures = []
    for i in range(1, days + 1):
        day = (now - timedelta(days=i)).date()
        try:
            payload = fetch(league, day)
            if not isinstance(payload, dict) or not isinstance(payload.get('events'), list):
                raise ValueError('events array absent')
            for event in payload['events']:
                if not isinstance(event, dict):
                    continue
                event_id = str(event.get('id', '')).strip()
                kickoff = utc(event.get('date'))
                if (not event_id or kickoff is None or kickoff >= now or
                        (event.get('status') or {}).get('type', {}).get('completed') is not True):
                    continue
                events[event_id] = event
        except (OSError, TimeoutError, ValueError, KeyError, TypeError) as ex:
            failures.append({'date': day.isoformat(), 'error': type(ex).__name__})
    teams = defaultdict(empty_team)
    accepted = 0
    for event in sorted(events.values(), key=lambda x: (utc(x['date']), str(x['id']))):
        try:
            participants = event['competitions'][0]['competitors']
            home = next(c for c in participants if c.get('homeAway') == 'home')
            away = next(c for c in participants if c.get('homeAway') == 'away')
            h = home['team']['displayName'].strip()
            a = away['team']['displayName'].strip()
            hg, ag = int(home['score']), int(away['score'])
            if not h or not a or h == a or min(hg, ag) < 0:
                continue
        except (KeyError, IndexError, TypeError, ValueError, StopIteration, AttributeError):
            continue
        x, y = teams[h], teams[a]
        x['mac'] += 1
        x['attigi'] += hg
        x['yedigi'] += ag
        x['ev_mac'] += 1
        x['ev_attigi'] += hg
        x['ev_yedigi'] += ag
        x['son_maclar'].append((hg, ag))
        y['mac'] += 1
        y['attigi'] += ag
        y['yedigi'] += hg
        y['dep_mac'] += 1
        y['dep_attigi'] += ag
        y['dep_yedigi'] += hg
        y['son_maclar'].append((ag, hg))
        accepted += 1
    return dict(teams), {'completed_matches': accepted, 'query_days': days,
                         'failure_days': len(failures), 'failures': failures[:15],
                         'teams': len(teams), 'home_away_and_form_enabled': True}


def valid_forecast(row, now):
    if not isinstance(row, dict) or not isinstance(row.get('mac'), dict):
        return None
    m = row['mac']
    kickoff = utc(m.get('tarih'))
    created = utc(m.get('hesaplama_zamani_utc'))
    locked = utc(row.get('kilit_zamani_utc'))
    if not (kickoff and created and locked and created <= locked < kickoff):
        return None
    league = m.get('lig_kodu')
    if not isinstance(league, str) or not league:
        return None
    return {'kickoff': kickoff, 'league': league, 'created': created, 'locked': locked}


def audit_archive(archive, now):
    if not isinstance(archive, list):
        raise ValueError('Expected archive list')
    rejected = Counter()
    choices = Counter()
    groups = defaultdict(list)
    settled = []
    future = []
    identities = set()
    for row in archive:
        if not isinstance(row, dict):
            rejected['non_object_record'] += 1
            continue
        identity = row.get('kimlik')
        if not isinstance(identity, str) or not identity or identity in identities:
            rejected['missing_or_duplicate_identity'] += 1
            continue
        identities.add(identity)
        meta = valid_forecast(row, now)
        if meta is None:
            rejected['invalid_pre_match_lock_or_timestamp'] += 1
            continue
        choice = str(row.get('kilitli_secim') or '').strip().upper()
        choices[choice or 'MISSING'] += 1
        market = re.fullmatch(r'(1\.5|2\.5|3\.5|4\.5|5\.5|6\.5) UST', choice)
        if meta['kickoff'] > now:
            future.append(row)
            if market is None:
                rejected['future_riskli_or_no_pick'] += 1
            continue
        if row.get('durum') != 'DOGRULANDI' or not isinstance(row.get('sonuc'), dict):
            rejected['pending_or_unverified'] += 1
            continue
        result_date = utc(row.get('sonuc_dogrulama_zamani_utc'))
        result = row['sonuc']
        home, away = result.get('ev_gol'), result.get('dep_gol')
        if (result_date is None or result_date < meta['kickoff'] or
                type(home) is not int or type(away) is not int or min(home, away) < 0):
            rejected['bad_or_early_result'] += 1
            continue
        if market is None:
            rejected['settled_riskli_or_no_pick'] += 1
            continue
        line = market.group(1)
        probability = (row.get('olasiliklar') or {}).get(line + '_ust')
        if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 100:
            rejected['invalid_probability'] += 1
            continue
        entry = {'league': meta['league'], 'line': line,
                 'kickoff': meta['kickoff'], 'verified': result_date,
                 'correct': int(home + away > float(line)), 'model_probability': probability / 100}
        groups[(meta['league'], line)].append(entry)
        settled.append(entry)
    grouped = []
    for (league, line), entries in sorted(groups.items()):
        win = sum(x['correct'] for x in entries)
        n = len(entries)
        grouped.append({'league': league, 'line': line, 'samples': n,
                        'correct': win, 'accuracy_pct': round(win * 100 / n, 2),
                        'mean_probability_pct': round(sum(x['model_probability'] for x in entries) * 100 / n, 2)})
    total = len(settled)
    won = sum(e['correct'] for e in settled)
    return {'created_utc': now.isoformat(), 'read_only': True,
            'archive_records': len(archive), 'unique_ids': len(identities),
            'verified_locked_over': total, 'correct': won, 'wrong': total-won,
            'accuracy_pct': round(100 * won / total, 2) if total else None,
            'mean_model_probability_pct': round(100 * sum(e['model_probability'] for e in settled) / total, 2) if total else None,
            'future_records': len(future),
            'choices': dict(choices), 'excluded': dict(rejected),
            'league_line_groups': grouped,
            'groups_with_30_or_more': sum(g['samples'] >= 30 for g in grouped),
            'largest_group': max((g['samples'] for g in grouped), default=0),
            'note': 'Historical sample audit, not a validated betting advantage. No retroactive recommendations.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arsiv', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--zaman', default=None, help='ISO UTC audit time; default current UTC')
    args = ap.parse_args()
    now = utc(args.zaman) if args.zaman else datetime.now(timezone.utc)
    if now is None:
        ap.error('Invalid --zaman')
    input_path, output_path = Path(args.arsiv), Path(args.cikti)
    if output_path.exists():
        raise SystemExit('Output exists; refusing overwrite')
    data = input_path.read_bytes()
    report = audit_archive(json.loads(data), now)
    report['input_sha256'] = hashlib.sha256(data).hexdigest()
    report['input_name'] = input_path.name
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('GECMIS:', report['verified_locked_over'], 'DOGRU:', report['correct'],
          'GRUP:', len(report['league_line_groups']), '30+ GRUP:', report['groups_with_30_or_more'])
    print('REPORT:', output_path)


if __name__ == '__main__':
    main()
