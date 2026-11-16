"""TIPSTER PRO V3: read-only fixture/model coverage and data integrity audit.
Does not produce predictions, alter archives, or imply model validation.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path


def load(path):
    with Path(path).open(encoding='utf-8') as fh:
        return json.load(fh)


def items(obj, field):
    value = obj.get(field) if isinstance(obj, dict) else None
    if not isinstance(value, list):
        raise ValueError(f'{field}: beklenen liste bulunamadi')
    return value


def identity(record):
    if not isinstance(record, dict):
        return None
    match_id = str(record.get('id') or '').strip()
    return match_id or None


def audit(fixtures, v2, extra):
    fixtures_by_id = {}
    invalid_fixtures = 0
    duplicate_fixtures = 0
    for record in fixtures:
        key = identity(record)
        if not key:
            invalid_fixtures += 1
        elif key in fixtures_by_id:
            duplicate_fixtures += 1
        else:
            fixtures_by_id[key] = record

    prediction_sets = {'V2': v2, 'EK_LIG': extra}
    by_source = {}
    duplicate_prediction_ids = {}
    invalid_predictions = {}
    predictions_by_id = defaultdict(list)
    for source, records in prediction_sets.items():
        seen = set()
        duplicates = 0
        invalid = 0
        for record in records:
            key = identity(record)
            if not key:
                invalid += 1
                continue
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            predictions_by_id[key].append(source)
        by_source[source] = len(seen)
        duplicate_prediction_ids[source] = duplicates
        invalid_predictions[source] = invalid

    covered = set(fixtures_by_id) & set(predictions_by_id)
    missing = set(fixtures_by_id) - set(predictions_by_id)
    outside = set(predictions_by_id) - set(fixtures_by_id)
    overlaps = set(k for k, sources in predictions_by_id.items() if len(sources) > 1)
    missing_by_league = Counter()
    missing_by_day = Counter()
    missing_records = []
    for key in sorted(missing):
        match = fixtures_by_id[key]
        league = match.get('lig_kodu') or 'BILINMIYOR'
        day = str(match.get('tarih') or '')[:10]
        missing_by_league[league] += 1
        missing_by_day[day] += 1
        missing_records.append({'id': key, 'tarih': match.get('tarih'), 'lig_kodu': league,
                                'ev_sahibi': match.get('ev_sahibi'), 'deplasman': match.get('deplasman')})

    return {
        'audit_utc': datetime.now(timezone.utc).isoformat(),
        'uyari': 'Yalnizca kimlik ve kapsam denetimi. Tahmin dogrulugu, kilitleme veya dunya fikstur kapsami olculmez.',
        'fixture_unique': len(fixtures_by_id),
        'fixture_duplicates': duplicate_fixtures,
        'fixture_invalid': invalid_fixtures,
        'prediction_unique_by_source': by_source,
        'prediction_duplicates_by_source': duplicate_prediction_ids,
        'prediction_invalid_by_source': invalid_predictions,
        'fixture_with_model_output': len(covered),
        'fixture_without_model_output': len(missing),
        'coverage_pct': round(100 * len(covered) / len(fixtures_by_id), 2) if fixtures_by_id else None,
        'cross_source_overlaps': len(overlaps),
        'cross_source_overlap_ids': sorted(overlaps),
        'prediction_ids_not_in_fixture': len(outside),
        'prediction_ids_not_in_fixture_sample': sorted(outside)[:30],
        'missing_by_league': dict(sorted(missing_by_league.items())),
        'missing_by_utc_day': dict(sorted(missing_by_day.items())),
        'missing_matches': missing_records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', default='gelecek_maclar.json')
    parser.add_argument('--v2', default='tipster_v2_sonuc.json')
    parser.add_argument('--extra', default='tipster_ek_lig_tahminler.json')
    parser.add_argument('--output', default='tipster_v3_kalite_raporu.json')
    args = parser.parse_args()
    report = audit(items(load(args.fixtures), 'maclar'),
                   items(load(args.v2), 'predictions'),
                   items(load(args.extra), 'tahminler'))
    destination = Path(args.output)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Fikstur:', report['fixture_unique'], '| Model ciktisi:', report['fixture_with_model_output'],
          '| Eksik:', report['fixture_without_model_output'], '| Kapsam:', report['coverage_pct'])
    print('Uyari: Bu bir tahmin basari raporu degildir.')


if __name__ == '__main__':
    main()
