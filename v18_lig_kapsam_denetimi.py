#!/usr/bin/env python3
"""TIPSTER PRO V18: strictly read-only league coverage audit.

Never imports the prediction engine, never changes forecasts/archives, and does not
interpret an empty ESPN scoreboard as evidence of an invalid league.
"""
import argparse
import ast
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# These identifiers are DISCOVERY CANDIDATES, not verified ESPN coverage.
CANDIDATES = {
    'cze.1': ('Çekya', 'Birinci lig'),
    'rou.1': ('Romanya', 'Birinci lig'),
    'cro.1': ('Hırvatistan', 'Birinci lig'),
    'kor.1': ('Güney Kore', 'K League 1'),
    'uru.1': ('Uruguay', 'Birinci lig'),
    'chi.1': ('Şili', 'Birinci lig'),
    'fin.1': ('Finlandiya', 'Veikkausliiga'),
    'isl.1': ('İzlanda', 'Úrvalsdeild'),
    'hun.1': ('Macaristan', 'NB I'),
    'ser.1': ('Sırbistan', 'SuperLiga'),
    'ecu.1': ('Ekvador', 'LigaPro'),
    'per.1': ('Peru', 'Liga 1'),
    'ksa.1': ('Suudi Arabistan', 'Pro League'),
    'egy.1': ('Mısır', 'Premier League'),
}

COUNTRIES = {
    'eng': 'İngiltere', 'sco': 'İskoçya', 'ger': 'Almanya',
    'esp': 'İspanya', 'ita': 'İtalya', 'fra': 'Fransa',
    'tur': 'Türkiye', 'pol': 'Polonya', 'ned': 'Hollanda',
    'por': 'Portekiz', 'bel': 'Belçika', 'sui': 'İsviçre',
    'aut': 'Avusturya', 'den': 'Danimarka', 'nor': 'Norveç',
    'swe': 'İsveç', 'irl': 'İrlanda', 'gre': 'Yunanistan',
    'usa': 'ABD', 'mex': 'Meksika', 'bra': 'Brezilya',
    'arg': 'Arjantin', 'col': 'Kolombiya', 'jpn': 'Japonya',
    'chn': 'Çin', 'aus': 'Avustralya', 'rsa': 'Güney Afrika',
    'uefa': 'UEFA (uluslararası)',
}
BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{}/scoreboard'


def read_league_registry(path):
    """Read LIGLER literal using AST, without executing the user repository code."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(x, ast.Name) and x.id == 'LIGLER' for x in node.targets):
                value = ast.literal_eval(node.value)
                if not isinstance(value, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in value.items()
                ):
                    raise ValueError('LIGLER sozlugu hatali')
                return value
    raise ValueError('Dosyada sabit LIGLER sozlugu bulunamadi')


def archived_codes(path):
    archive = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(archive, list):
        raise ValueError('Arsiv liste biciminde olmali')
    counts = Counter()
    for item in archive:
        if isinstance(item, dict):
            match = item.get('mac')
            if isinstance(match, dict) and isinstance(match.get('lig_kodu'), str):
                counts[match['lig_kodu']] += 1
    return counts, len(archive)


def probe_espn(code, dates, opener=urlopen):
    """A successful empty response proves only access, NOT league match coverage."""
    events = set()
    successes = 0
    errors = []
    for date in dates:
        url = BASE.format(code) + '?' + urlencode({'dates': date.strftime('%Y%m%d'), 'limit': 500})
        try:
            with opener(Request(url, headers={'User-Agent': 'TIPSTER-V18-LEAGUE-AUDIT/1.0'}), timeout=12) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get('events'), list):
                errors.append('unexpected_schema:' + date.isoformat())
                continue
            successes += 1
            for event in payload['events']:
                if isinstance(event, dict) and event.get('id') is not None:
                    events.add(str(event['id']))
        except (OSError, HTTPError, URLError, ValueError, TypeError) as exc:
            errors.append(type(exc).__name__ + ':' + date.isoformat())
    if events:
        status = 'MAC_KANITI_VAR'
    elif successes == len(dates):
        status = 'YANIT_VAR_MAC_KANITI_YOK'
    elif successes:
        status = 'KISMI_YANIT'
    else:
        status = 'DOGRULANAMADI'
    return {'durum': status, 'essiz_mac': len(events), 'basarili_sorgu': successes,
            'toplam_sorgu': len(dates), 'hatalar': errors}


def build_report(registry, counts, archive_total, probe=False, today=None, opener=urlopen):
    today = today or datetime.now(timezone.utc).date()
    # Three sampled calendar days do not test an entire season.
    sample_days = [today - timedelta(days=2), today - timedelta(days=20), today + timedelta(days=7)]
    entries = []
    for code, label in registry.items():
        region = COUNTRIES.get(code.split('.')[0], 'Bilinmiyor')
        entries.append({'kod': code, 'ulke': region, 'lig': label,
                        'tip': 'MEVCUT', 'arsiv_kayit': counts.get(code, 0),
                        'arsiv_durumu': 'KAYIT_VAR' if counts.get(code, 0) else 'KAYIT_YOK',
                        'espn_testi': 'CALISTIRILMADI'})
    for code, (country, label) in CANDIDATES.items():
        if code not in registry:
            entries.append({'kod': code, 'ulke': country, 'lig': label,
                            'tip': 'ADAY_DOGRULANMAMIS', 'arsiv_kayit': counts.get(code, 0),
                            'arsiv_durumu': 'AYRI_TEST_GEREKLI', 'espn_testi': 'CALISTIRILMADI'})
    if probe:
        for entry in entries:
            # Audit only missing-archive existing codes + new candidates; no need to
            # hammer ESPN for already archived leagues in the first pilot.
            if entry['tip'] == 'ADAY_DOGRULANMAMIS' or entry['arsiv_kayit'] == 0:
                result = probe_espn(entry['kod'], sample_days, opener)
                entry['espn_testi'] = result['durum']
                entry['espn_kanit_mac'] = result['essiz_mac']
                entry['basarili_sorgu'] = result['basarili_sorgu']
                entry['sorgu_adedi'] = result['toplam_sorgu']
                entry['sorgu_hatalari'] = result['hatalar']
    return {
        'modul': 'TIPSTER V18 - BAGIMSIZ LIG KAPSAM DENETIMI',
        'rapor_utc': datetime.now(timezone.utc).isoformat(),
        'not': 'Salt okunur denetim. Kayit yok = lig calismiyor demek degildir. '
               'Uc ornek tarih sezon kapsamini kanitlamaz. Kodlar otomatik eklenmez.',
        'toplam_tanimli': len(registry),
        'ulke_sayisi': len({COUNTRIES.get(c.split('.')[0], c.split('.')[0]) for c in registry if not c.startswith('uefa.')}),
        'arsiv_toplam_kayit': archive_total,
        'arsivde_kayitli_lig': sum(1 for c in registry if counts.get(c, 0) > 0),
        'arsivde_kayitsiz_lig': [c for c in registry if counts.get(c, 0) == 0],
        'aday_sayisi': sum(e['tip'] == 'ADAY_DOGRULANMAMIS' for e in entries),
        'canli_espn_testi': probe,
        'ornekteki_tarihler': [d.isoformat() for d in sample_days] if probe else [],
        'ligler': entries,
    }


def write_report(report, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'lig_kapsam_raporu.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    columns = ['tip', 'ulke', 'lig', 'kod', 'arsiv_kayit', 'arsiv_durumu',
               'espn_testi', 'espn_kanit_mac', 'basarili_sorgu', 'sorgu_adedi']
    with (out / 'lig_kapsam_raporu.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(report['ligler'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lig-kaynagi', default='fikstur_yeni.py')
    ap.add_argument('--arsiv', default='v18_tahmin_arsivi.json')
    ap.add_argument('--cikti-klasoru', default='lig_kapsam_raporu')
    ap.add_argument('--espn-ornegi', action='store_true',
                    help='Only candidate + existing no-archive leagues, 3 sampled days each')
    args = ap.parse_args()
    registry = read_league_registry(args.lig_kaynagi)
    counts, total = archived_codes(args.arsiv)
    report = build_report(registry, counts, total, probe=args.espn_ornegi)
    write_report(report, args.cikti_klasoru)
    print('TANIMLI:', report['toplam_tanimli'], 'ULKE:', report['ulke_sayisi'],
          'ARSIVDE KAYITLI:', report['arsivde_kayitli_lig'],
          'KAYITSIZ:', len(report['arsivde_kayitsiz_lig']),
          'YENI ADAY:', report['aday_sayisi'])
    print('RAPOR:', args.cikti_klasoru)


if __name__ == '__main__':
    main()
