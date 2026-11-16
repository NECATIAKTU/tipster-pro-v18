
"""TIPSTER PRO V2: ESPN fixture analysis and diagnostic reports."""

import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from coklu_lig_motoru import tum_ligleri_al, mac_analizi, SOURCE_TRACE

MAP = {
    'eng.1': 'E0', 'eng.2': 'E1',
    'eng.3': 'E2', 'eng.4': 'E3',
    'esp.1': 'SP1', 'ger.1': 'D1',
    'ita.1': 'I1', 'fra.1': 'F1',
    'ned.1': 'N1', 'por.1': 'P1',
    'tur.1': 'T1', 'sco.1': 'SC0',
    'bel.1': 'B1',
    
    'eng.5': 'EC',
    'ger.2': 'D2',
    'esp.2': 'SP2',
    'ita.2': 'I2',
    'fra.2': 'F2',
    'gre.1': 'G1',
    'sco.2': 'SC1',
    'sco.3': 'SC2',
    'jpn.1': 'J1',
    'nor.1': 'NOR1',
    'bra.1': 'BRA1',
    'mex.1': 'MEX1',
    'col.1': 'COL1',
}

ALIASES = {
    'manchester united': 'man united',
    'manchester city': 'man city',
    'nottingham forest': 'nottm forest',
    'tottenham hotspur': 'tottenham',
    'newcastle united': 'newcastle',
    'west ham united': 'west ham',
    'brighton and hove albion': 'brighton',
    'brighton hove albion': 'brighton',
    'wolverhampton wanderers': 'wolves',
    'leicester city': 'leicester',
    'ipswich town': 'ipswich',
    'norwich city': 'norwich',
    'birmingham city': 'birmingham',
    'cardiff city': 'cardiff',
    'swansea city': 'swansea',
    'hull city': 'hull',
    'stoke city': 'stoke',
    'blackburn rovers': 'blackburn',
    'deportivo': 'la coruna',
    'sheffield wednesday': 'sheffield weds',
    'queens park rangers': 'qpr',
    'west bromwich albion': 'west brom',
    'leeds united': 'leeds',
    'fortuna sittard': 'for sittard',
    'nec nijmegen': 'nijmegen',
    'fc groningen': 'groningen',
    'feyenoord rotterdam': 'feyenoord',
    'ajax amsterdam': 'ajax',
    'sc cambuur': 'cambuur',
    'pec zwolle': 'zwolle',
    'internazionale': 'inter',
    'ac milan': 'milan',
    'as roma': 'roma',
    'racing genk': 'genk',
    'standard liege': 'standard',
    'kaa gent': 'gent',
    'kv mechelen': 'mechelen',
    'sint truidense': 'st truiden',
    'union st gilloise': 'union saint gilloise',
    'athletic club': 'ath bilbao',
    'celta vigo': 'celta',
    'real betis': 'betis',
    'real sociedad': 'sociedad',
    'atletico madrid': 'ath madrid',
    'heart of midlothian': 'hearts',
    'paris saint germain': 'paris sg',
    'as monaco': 'monaco',
    'stade rennais': 'rennes',
    'aj auxerre': 'auxerre',
    'le havre ac': 'le havre',
    'bayer leverkusen': 'leverkusen',
    'tsg hoffenheim': 'hoffenheim',
    'sc freiburg': 'freiburg',
    'vfb stuttgart': 'stuttgart',
    'borussia monchengladbach': 'm gladbach',
    'borussia dortmund': 'dortmund',
    'caykur rizespor': 'rizespor',
    'istanbul basaksehir': 'basaksehir',
    'sporting cp': 'sporting',
    'c d nacional': 'nacional',
    'vitoria de guimaraes': 'guimaraes',
    'braga': 'sp braga',
    'rayo vallecano': 'vallecano',
    '1 fc union berlin': 'union berlin',
    'fc cologne': 'fc koln',
    'eintracht frankfurt': 'ein frankfurt',
    'hamburg sv': 'hamburg',
    'royal charleroi sc': 'charleroi',
    'oh leuven': 'leuven',
    'gaziantep fk': 'gaziantep',
    'erzurum bb': 'erzurumspor',
    'corum fk': 'corum',
    'amed sfk': 'amedspor',
    'coventry city': 'coventry',
    'bolton wanderers': 'bolton',
    'charlton athletic': 'charlton',
    'cercle brugge ksv': 'cercle brugge',
    'ado den haag': 'den haag',
    
    'kristiansund bk': 'kristiansund',
    'derby county': 'derby',
    'preston north end': 'preston',
    'lincoln city': 'lincoln',
    'tromso il': 'tromso',
    'bodo glimt': 'bodo/glimt',
    'huddersfield town': 'huddersfield',
    'wigan athletic': 'wigan',
    'mansfield town': 'mansfield',
    'bradford city': 'bradford',
    'luton town': 'luton',
    'oxford united': 'oxford',
    'doncaster rovers': 'doncaster',
    'burton albion': 'burton',
    'plymouth argyle': 'plymouth',
    'stockport county': 'stockport',
    'wycombe wanderers': 'wycombe',
    'cambridge united': 'cambridge',
    'peterborough united': 'peterboro',
    'northampton town': 'northampton',
    'oldham athletic': 'oldham',
    'exeter city': 'exeter',
    'cheltenham town': 'cheltenham',
    'bristol rovers': 'bristol rovers',
    'colchester united': 'colchester',
    'crewe alexandra': 'crewe',
    'accrington stanley': 'accrington',
    'york city': 'york',
    'rotherham united': 'rotherham',
    'salford city': 'salford',
    'shrewsbury town': 'shrewsbury',
    'swindon town': 'swindon',
    'grimsby town': 'grimsby',
    'tranmere rovers': 'tranmere',
    'kvc westerlo': 'westerlo',
    'waasland beveren': 'waasland beveren',
    'zulte waregem': 'waregem',
    'racing santander': 'santander',
    'espanyol': 'espanyol',
    'sv elversberg': 'elversberg',
    'sc paderborn 07': 'paderborn',
    'academico de viseu': 'academico viseu',
    'goztepe': 'goztepe',
    'ik start': 'start',
    'hamarkameratene': 'ham kam',
    'sarpsborg fk': 'sarpsborg 08',
    'lillestrom': 'lillestrom',
    'viking fk': 'viking',
    'sk brann': 'brann',
}

# TIPSTER PRO - 71 TAKIM TOPLU ESLESME ONARIMI
# Kaynak: Toplu eslesme kontrol raporu

ALIASES.update({
    # Belcika
    'kv kortrijk': 'kortrijk',
    'oh leuven': 'oud heverlee leuven',
    'union st gilloise': 'st gilloise',
    'waasland beveren': 'beveren',

    # Ingiltere Premier League
    'nottingham forest': 'nott m forest',

    # Ingiltere League Two
    'bristol rovers': 'bristol rvs',

    # Ingiltere National League
    'aldershot town': 'aldershot',
    'boston united': 'boston utd',
    'carlisle united': 'carlisle',
    'fc halifax town': 'halifax',
    'forest green rovers': 'forest green',
    'harrogate town': 'harrogate',
    'hartlepool united': 'hartlepool',
    'kidderminster harriers': 'kidderminster',
    'scunthorpe united': 'scunthorpe',
    'solihull moors': 'solihull',
    'southend united': 'southend',
    'sutton united': 'sutton',
    'yeovil town': 'yeovil',

    # Ispanya La Liga
    'espanyol': 'espanol',

    # Ispanya La Liga 2
    'cd sabadell': 'sabadell',
    'rc celta fortuna': 'celta b',
    'real oviedo': 'oviedo',
    'real sociedad ii': 'sociedad b',
    'real valladolid': 'valladolid',
    'sporting gijon': 'sp gijon',

    # Fransa Ligue 2
    'as nancy lorraine': 'nancy',
    'clermont foot': 'clermont',
    'dijon fco': 'dijon',
    'pau': 'pau fc',
    'red star fc 93': 'red star',
    'rodez aveyron': 'rodez',
    'saint etienne': 'st etienne',
    'stade laval': 'laval',
    'stade de reims': 'reims',

    # Almanya Bundesliga
    'fc cologne': 'koln',

    # Almanya Bundesliga 2
    '1 fc heidenheim 1846': 'heidenheim',
    '1 fc magdeburg': 'magdeburg',
    '1 fc nurnberg': 'nurnberg',
    'arminia bielefeld': 'bielefeld',
    'dynamo dresden': 'dresden',
    'energie cottbus': 'cottbus',
    'hannover 96': 'hannover',
    'hertha berlin': 'hertha',
    'karlsruher sc': 'karlsruhe',
    'sv darmstadt 98': 'darmstadt',
    'spvgg greuther furth': 'greuther furth',
    'tsv eintracht braunschweig': 'braunschweig',
    'vfl bochum': 'bochum',
    'vfl osnabruck': 'osnabruck',
    'vfl wolfsburg': 'wolfsburg',

    # Yunanistan
    'aek athens': 'aek',
    'asteras tripoli': 'asteras tripolis',
    'levadiakos': 'levadeiakos',
    'olympiacos': 'olympiakos',

    # Italya Serie B
    'hellas verona': 'verona',
    'us avellino': 'avellino',

    # Norvec
    'bodo glimt': 'bod glimt',
    'hamarkameratene': 'hamkam',
    'lillestrom': 'lillestr m',
    'tromso': 'troms',

    # Portekiz
    'sporting cp': 'sp lisbon',

    # Iskocya Championship
    'ayr united': 'ayr',
    'dunfermline athletic': 'dunfermline',
    'greenock morton': 'morton',
    'inverness caledonian thistle': 'inverness c',
    'partick thistle': 'partick',
    'queen s park': 'queens park',
    'raith rovers': 'raith rvs',

    # Turkiye
    'goztepe': 'goztep',
    'istanbul basaksehir': 'buyuksehyr',
})


def norm(s):
    s = str(s or '')
    s = s.replace('ı', 'i').replace('İ', 'I')
    s = s.replace('ß', 'ss')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(
        c for c in s
        if not unicodedata.combining(c)
    ).lower()
    s = s.replace('&', ' and ')
    return ' '.join(
        re.sub(r'[^a-z0-9 ]', ' ', s).split()
    )


ALIAS = {
    norm(k): norm(v)
    for k, v in ALIASES.items()
}


def canon(s):
    s = norm(s)

    if s in ALIAS:
        return ALIAS[s]

    for prefix in ('fc ', 'afc '):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    return ALIAS.get(s, s)


def match(name, teams):
    target = canon(name)

    if not target:
        return None, 'empty', 0

    exact = [
        t for t in teams
        if canon(t) == target
    ]

    if len(exact) == 1:
        return exact[0], 'exact', 1.0

    if len(exact) > 1:
        return None, 'ambiguous_exact', 0

    scored = sorted(
        (
            (
                SequenceMatcher(
                    None, target, canon(t)
                ).ratio(),
                t,
            )
            for t in teams
        ),
        reverse=True,
    )

    if not scored:
        return None, 'no_teams', 0

    first = scored[0]
    second = (
        scored[1][0]
        if len(scored) > 1 else 0
    )

    if (
        first[0] >= 0.95
        and first[0] - second >= 0.10
    ):
        return (
            first[1],
            'fuzzy_review',
            round(first[0], 3),
        )

    return None, 'unmatched', round(first[0], 3)


def read_json(path, default):
    if not Path(path).exists():
        return default

    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')

    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(
            value, f,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(tmp, path)


def kickoff(s):
    try:
        d = datetime.fromisoformat(
            str(s).replace('Z', '+00:00')
        )

        if d.tzinfo is None:
            return None

        return d.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None


def main():
    now = datetime.now(timezone.utc)

    source = read_json('gelecek_maclar.json', {})

    games = (
        source.get('maclar', [])
        if isinstance(source, dict)
        else source
    )

    if not isinstance(games, list):
        raise ValueError(
            'gelecek_maclar.json: maclar must be a list'
        )

    leagues = tum_ligleri_al()

    predictions = []
    skipped = []
    reasons = Counter()
    by_league = Counter()
    match_types = Counter()
    seen = set()

    for game in games:
        if not isinstance(game, dict):
            reasons['invalid_record'] += 1
            continue

        espn = game.get('lig_kodu', '')
        home = game.get('ev_sahibi', '')
        away = game.get('deplasman', '')
        dt = kickoff(game.get('tarih'))

        key = (
            espn,
            norm(home),
            norm(away),
            dt.isoformat() if dt else '',
        )

        if key in seen:
            reasons['duplicate'] += 1
            continue

        seen.add(key)
        reason = None
        detail = {}

        if not dt:
            reason = 'invalid_time'

        elif dt <= now:
            reason = 'already_started'

        elif espn not in MAP:
            reason = 'unsupported_league'

        elif MAP[espn] not in leagues:
            reason = 'missing_league_data'

        else:
            league = MAP[espn]
            teams = leagues[league]

            h, ht, hs = match(home, teams)
            a, at, away_score = match(away, teams)

            detail = {
                'matched_home': h,
                'matched_away': a,
                'home_type': ht,
                'away_type': at,
                'home_score': hs,
                'away_score': away_score,
            }

            if not h or not a or h == a:
                reason = 'unmatched_team'

            elif 'fuzzy_review' in (ht, at):
                reason = 'fuzzy_requires_review'

            else:
                try:
                    result = mac_analizi(
                        league, h, a, leagues
                    )

                except (
                    ValueError,
                    KeyError,
                    ZeroDivisionError,
                ) as exc:
                    reason = 'insufficient_stats'
                    detail['error'] = str(exc)

                else:
                    match_types[ht] += 1
                    match_types[at] += 1

                    predictions.append({
                        'id': game.get('id'),
                        'tarih': dt.isoformat(),
                        'espn_lig': espn,
                        'lig': league,
                        'ev': home,
                        'dep': away,
                        'eslesen_ev': h,
                        'eslesen_dep': a,
                        'model': 'ESPN_POISSON_V2',
                        'istatistik_kaynaklari': [
                            SOURCE_TRACE[(league, season)]
                            for season in ('2627', '2526')
                            if (league, season) in SOURCE_TRACE
                        ],
                        'created_at_utc': now.isoformat(),
                        'analiz': result,
                        'status': 'PREMATCH_MODEL_OUTPUT_UNVALIDATED',
                    })

        if reason:
            reasons[reason] += 1
            by_league[(espn, reason)] += 1

            skipped.append({
                'id': game.get('id'),
                'lig': espn,
                'tarih': game.get('tarih'),
                'ev': home,
                'dep': away,
                'neden': reason,
                **detail,
            })

    report = {
        'run_at_utc': now.isoformat(),
        'source_trace_count': len(SOURCE_TRACE),
        'source_count': len(games),
        'unique_count': len(seen),
        'predicted_count': len(predictions),
        'reasons': dict(reasons),
        'match_types': dict(match_types),
        'league_issues': [
            {
                'lig': k[0],
                'neden': k[1],
                'adet': v,
            }
            for k, v in sorted(
                by_league.items(),
                key=lambda x: -x[1],
            )
        ],
        'predictions': predictions,
    }

    save_json('tipster_v2_sonuc.json', report)
    save_json('tipster_v2_eksikler.json', skipped)

    archive_path = 'tipster_v2_arsiv.json'
    old = read_json(
        archive_path,
        {'records': {}},
    )

    records = (
        old.get('records', {})
        if isinstance(old, dict)
        else {}
    )

    if not isinstance(records, dict):
        raise ValueError(
            'Invalid archive structure'
        )

    added = 0

    for p in predictions:
        key = '|'.join([
            str(p['id'] or ''),
            p['tarih'],
            p['espn_lig'],
            norm(p['ev']),
            norm(p['dep']),
            p['model'],
        ])

        if key not in records:
            records[key] = p
            added += 1

    save_json(
        archive_path,
        {'records': records},
    )

    print(
        'TIPSTER PRO V2',
        '| total:', len(games),
        '| analyzed:', len(predictions),
        '| skipped:', len(skipped),
        '| archive_new:', added,
        '| archive_total:', len(records),
    )

    print('REASONS:', dict(reasons))
    print('MATCH TYPES:', dict(match_types))

    print(
        'FILES: tipster_v2_sonuc.json '
        'tipster_v2_eksikler.json '
        'tipster_v2_arsiv.json'
    )


if __name__ == '__main__':
    main()
