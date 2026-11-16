"""TIPSTER PRO V4: compare immutable pre-match archive against ESPN final scores.

Reads tipster_v4_kilitli_arsiv.json; writes ONLY separate V4 result files.
Never modifies the locked archive or existing V1/V2/V3 outputs.
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = Path('tipster_v4_kilitli_arsiv.json')
OUT = Path('tipster_v4_sonuc_raporu.json')
TXT = Path('tipster_v4_sonuc_raporu.txt')

# Codes are from V4 (football-data); ESPN uses a different league namespace.
ESPN_LEAGUES = {
    'E0': 'eng.1', 'E1': 'eng.2', 'E2': 'eng.3', 'E3': 'eng.4',
    'EC': 'eng.5', 'SC0': 'sco.1', 'SC1': 'sco.2', 'SC2': 'sco.3',
    'D1': 'ger.1', 'D2': 'ger.2', 'SP1': 'esp.1', 'SP2': 'esp.2',
    'I1': 'ita.1', 'I2': 'ita.2', 'F1': 'fra.1', 'F2': 'fra.2',
    'N1': 'ned.1', 'P1': 'por.1', 'B1': 'bel.1', 'T1': 'tur.1',
    'G1': 'gre.1', 'NOR1': 'nor.1', 'J1': 'jpn.1'
}


def utc(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def norm(value):
    s = str(value or '').casefold().replace('Ä±', 'i').replace('Ã¸', 'o').replace('Ã¦', 'ae')
    s = unicodedata.normalize('NFKD', s)
    return re.sub('[^a-z0-9]', '', ''.join(c for c in s if not unicodedata.combining(c)))


# Only explicitly verified identity aliases. ESPN event ID remains the primary join key.
ALIASES = {
    'blackburnrovers': 'blackburn', 'stokecity': 'stoke',
    'charltonathletic': 'charlton', 'boltonwanderers': 'bolton',
    'nottinghamforest': 'nottmforest', 'manchesterunited': 'manunited',
    'manchestercity': 'mancity', 'internazionale': 'inter',
    'tottenhamhotspur': 'tottenham', 'caykurrizespor': 'rizespor',
}


def same(a, b):
    x, y = norm(a), norm(b)
    return bool(x and y and (x == y or ALIASES.get(x, x) == ALIASES.get(y, y)))


def fetch(league, ymd):
    url = (f'https://site.api.espn.com/apis/site/v2/sports/soccer/'
           f'{league}/scoreboard?dates={ymd}')
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=20) as resp:
        body = json.load(resp)
    events = body.get('events', [])
    if not isinstance(events, list):
        raise ValueError('ESPN events is not a list')
    return events


def final_score(event):
    status = (event.get('status') or {}).get('type') or {}
    if status.get('completed') is not True:
        return None
    contests = event.get('competitions') or []
    if not contests:
        return None
    competitors = contests[0].get('competitors') or []
    sides = {p.get('homeAway'): p for p in competitors}
    home, away = sides.get('home'), sides.get('away')
    if not home or not away:
        return None
    try:
        h, a = int(home['score']), int(away['score'])
    except (KeyError, ValueError, TypeError):
        return None
    if min(h, a) < 0:
        return None
    return {'home_goals': h, 'away_goals': a,
            'home': (home.get('team') or {}).get('displayName', ''),
            'away': (away.get('team') or {}).get('displayName', ''),
            'event_id': str(event.get('id', '')),
            'status_detail': status.get('detail', '')}


def evaluate_decision(label, h, a, market):
    if label in (None, '', 'RISKLI', 'RÄ°SKLÄ°', 'VERI EKSIK', 'KONTROL DISI'):
        return 'RISKLI' if label in ('RISKLI', 'RÄ°SKLÄ°') else 'KARAR_YOK'
    if market == 'btts':
        if label == 'GOL VAR':
            return 'DOGRU' if h > 0 and a > 0 else 'YANLIS'
        if label == 'GOL YOK':
            return 'DOGRU' if h == 0 or a == 0 else 'YANLIS'
        return 'KARAR_TANINMADI'
    match = re.fullmatch(r'([1-6])\.5\s+(?:UST|ÃST)', str(label))
    if match:
        return 'DOGRU' if h + a >= int(match.group(1)) + 1 else 'YANLIS'
    if label in ('7+ GOL', '7 PLUS GOL'):
        return 'DOGRU' if h + a >= 7 else 'YANLIS'
    return 'KARAR_TANINMADI'


def main():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    records = data.get('records') if isinstance(data, dict) else None
    if not isinstance(records, dict):
        raise ValueError('Kilitli arÅiv biÃ§imi geÃ§ersiz; hiÃ§bir Ã§Ä±ktÄ± deÄiÅtirilmedi')
    now = datetime.now(timezone.utc)
    cache = {}
    results = []
    stats = {'ust': Counter(), 'gol_var_yok': Counter()}
    per_day = defaultdict(lambda: {'ust': Counter(), 'gol_var_yok': Counter()})

    for archive_key, record in records.items():
        if not isinstance(record, dict):
            continue
        kickoff = utc(record.get('tarih'))
        created = utc(record.get('v4_created_at_utc'))
        model = record.get('v4') or {}
        league = record.get('lig')
        output = {'arsiv_anahtari': archive_key, 'id': record.get('id'),
                  'tarih': record.get('tarih'), 'kilit_zamani': record.get('v4_created_at_utc'),
                  'lig': league, 'ev': record.get('ev'), 'dep': record.get('dep'),
                  'ust_tahmini': model.get('ust_karari', record.get('karar')),
                  'gol_var_yok_tahmini': model.get('gol_var_yok_karari'),
                  'durum': 'BEKLIYOR'}
        if not kickoff or not created or created >= kickoff:
            output['durum'] = 'KILIT_GECERSIZ'
        elif not isinstance(model, dict) or not model:
            output['durum'] = 'MODEL_VERISI_EKSIK'
        elif kickoff + timedelta(hours=3) > now:
            output['durum'] = 'BEKLIYOR'
        elif league not in ESPN_LEAGUES:
            output['durum'] = 'LIG_DESTEKLENMIYOR'
        else:
            espn_league = ESPN_LEAGUES[league]
            events = {}
            failed = False
            for offset in (-1, 0, 1):
                day = (kickoff + timedelta(days=offset)).strftime('%Y%m%d')
                key = (espn_league, day)
                if key not in cache:
                    try:
                        cache[key] = fetch(*key)
                    except Exception as exc:
                        cache[key] = exc
                if isinstance(cache[key], Exception):
                    failed = True
                    continue
                for e in cache[key]:
                    if e.get('id') is not None:
                        events[str(e['id'])] = e
            expected_id = str(record.get('id') or '').split('|')[-1]
            event = events.get(expected_id)
            # Never silently match another event by approximate team name.
            if event is None:
                output['durum'] = 'KAYNAK_HATASI' if failed else 'MAC_BULUNAMADI'
            else:
                score = final_score(event)
                if score is None:
                    output['durum'] = 'SONUC_BEKLENIYOR'
                elif not (same(output['ev'], score['home']) and same(output['dep'], score['away'])):
                    output['durum'] = 'TAKIM_KONTROLU'
                    output['eslesen_ev'] = score['home']
                    output['eslesen_dep'] = score['away']
                else:
                    # If ESPN reports a shootout, manually verify regulation/extra-time scores.
                    detail = str(score.get('status_detail', '')).lower()
                    if 'penalt' in detail or 'penalt' in str((event.get('status') or {}).get('type', {}).get('name', '')).lower():
                        output['durum'] = 'SKOR_KONTROLU'
                    else:
                        output['durum'] = 'SONUCLANDI'
                        output['skor'] = f"{score['home_goals']}-{score['away_goals']}"
                        output['ust_sonucu'] = evaluate_decision(output['ust_tahmini'], score['home_goals'], score['away_goals'], 'over')
                        output['gol_var_yok_sonucu'] = evaluate_decision(output['gol_var_yok_tahmini'], score['home_goals'], score['away_goals'], 'btts')
                        day = kickoff.strftime('%Y-%m-%d')
                        for kind, value in (('ust', output['ust_sonucu']), ('gol_var_yok', output['gol_var_yok_sonucu'])):
                            stats[kind][value] += 1
                            per_day[day][kind][value] += 1
        results.append(output)

    def summary(counter):
        ok, bad = counter['DOGRU'], counter['YANLIS']
        return {'dogru': ok, 'yanlis': bad, 'riskli': counter['RISKLI'],
                'karar_yok': counter['KARAR_YOK'], 'karar_taninmadi': counter['KARAR_TANINMADI'],
                'degerlendirilen': ok + bad,
                'basari_yuzdesi': round(100 * ok / (ok + bad), 2) if ok + bad else None}

    report = {'olusturulma_utc': now.isoformat(), 'arsiv_kayit_sayisi': len(records),
              'ust': summary(stats['ust']), 'gol_var_yok': summary(stats['gol_var_yok']),
              'gunluk': {d: {m: summary(c) for m, c in markets.items()}
                         for d, markets in sorted(per_day.items())},
              'durumlar': dict(Counter(r['durum'] for r in results)),
              'kayitlar': results,
              'not': 'Yalnizca kilitli ilk V4 tahminleri. Bu dosya arÅivi deÄiÅtirmez.'}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['TIPSTER PRO V4 - KILITLI TAHMIN SONUC KONTROLU',
             'Olusturulma UTC: ' + now.isoformat(),
             f'ARSIV KAYDI: {len(records)}',
             'UST: ' + json.dumps(report['ust'], ensure_ascii=False),
             'GOL VAR/YOK: ' + json.dumps(report['gol_var_yok'], ensure_ascii=False),
             'DURUMLAR: ' + json.dumps(report['durumlar'], ensure_ascii=False),
             'Not: Dogrulanmis sonuc bulunmadan basari oranina eklenmez.']
    TXT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
