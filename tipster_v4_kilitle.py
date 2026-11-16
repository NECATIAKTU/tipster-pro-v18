"""TIPSTER PRO V4: preserve first eligible pre-match model output.

Run immediately after tipster_v4_test.py. Does not alter V2/V3/V4 reports.
GitHub Actions must commit tipster_v4_kilitli_arsiv.json after this step.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path('tipster_v4_test.json')
ARCHIVE = Path('tipster_v4_kilitli_arsiv.json')


def parse_utc(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return result.astimezone(timezone.utc) if result.tzinfo else None


def read_records():
    if not ARCHIVE.exists():
        return {}
    with ARCHIVE.open(encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get('records'), dict):
        raise ValueError('Arsiv yapisi gecersiz; eski dosyaya dokunulmadi')
    return data['records']


def main():
    with SOURCE.open(encoding='utf-8') as f:
        data = json.load(f)
    matches = data.get('matches')
    if not isinstance(matches, list):
        raise ValueError('V4 matches listesi bulunamadi')
    records = read_records()
    now = datetime.now(timezone.utc)
    added = 0
    ignored = 0
    unchanged = 0
    for item in matches:
        if not isinstance(item, dict):
            ignored += 1
            continue
        kickoff = parse_utc(item.get('tarih'))
        created = parse_utc(item.get('v4_created_at_utc'))
        decision = item.get('karar')
        match_id = item.get('id')
        # Store only real model outputs generated before kickoff.
        if (kickoff is None or created is None or created >= kickoff or created > now
                or not match_id or decision in (None, 'VERI EKSIK', 'KONTROL DISI')
                or not isinstance(item.get('v4'), dict)):
            ignored += 1
            continue
        key = f"{match_id}|{kickoff.isoformat()}"
        if key in records:
            unchanged += 1
            continue
        records[key] = item
        added += 1

    output = {'schema_version': 1, 'records': records}
    tmp = ARCHIVE.with_suffix('.json.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, ARCHIVE)
    print(f'V4 KILIT: yeni={added} onceki={unchanged} atlanan={ignored} toplam={len(records)}')


if __name__ == '__main__':
    main()
