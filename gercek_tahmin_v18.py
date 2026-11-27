"""V18: 42 ESPN liginde kaynak-dogrulanabilir gol olasiligi uretimi.

Guncel fikstur zorunludur; gecmis mac verisi eksikse tahmin uretilmez.
Mevcut tahminler.json / kayitlar.json dosyalarina dokunmaz.
"""
import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fikstur_yeni import LIGLER
from gol_modeli import mac_analizi, bos_takim
from tahmin_motoru import otomatik_eslestir, indeks_olustur, tarih_utc

BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{}/scoreboard'


def get_json(lig, day):
    url = BASE.format(lig) + '?' + urlencode({'dates': day.strftime('%Y%m%d'), 'limit': 500})
    with urlopen(Request(url, headers={'User-Agent':'TIPSTER-PRO-V18/1.0'}), timeout=18) as response:
        return json.load(response)


def historical_stats(lig, now, days, fetch=get_json):
    events = {}
    errors = 0
    for i in range(1, days + 1):
        day = (now - timedelta(days=i)).date()
        try:
            payload = fetch(lig, day)
            if not isinstance(payload.get('events'), list):
                raise ValueError('events listesi eksik')
            for e in payload['events']:
                if e.get('status', {}).get('type', {}).get('completed'):
                    events[str(e.get('id'))] = e
        except (OSError, ValueError, KeyError, TypeError):
            errors += 1
    teams = defaultdict(bos_takim)
    valid = 0
    for event in sorted(events.values(), key=lambda e: e.get('date') or ''):
        try:
            competitors = event['competitions'][0]['competitors']
            home = next(c for c in competitors if c['homeAway'] == 'home')
            away = next(c for c in competitors if c['homeAway'] == 'away')
            h, a = home['team']['displayName'], away['team']['displayName']
            hg, ag = int(home['score']), int(away['score'])
            if not h or not a or hg < 0 or ag < 0 or h == a:
                continue
        except (KeyError, IndexError, StopIteration, ValueError, TypeError):
            continue
        teams[h]['mac'] += 1; teams[h]['attigi'] += hg; teams[h]['yedigi'] += ag
        teams[a]['mac'] += 1; teams[a]['attigi'] += ag; teams[a]['yedigi'] += hg
        teams[h]['ev_mac'] += 1
        teams[h]['ev_attigi'] += hg
        teams[h]['ev_yedigi'] += ag
        teams[h]['son_maclar'].append((hg, ag))
        teams[a]['dep_mac'] += 1
        teams[a]['dep_attigi'] += ag
        teams[a]['dep_yedigi'] += hg
        teams[a]['son_maclar'].append((ag, hg))
        valid += 1
    return dict(teams), {'tamamlanmis_mac': valid, 'hata_gunu': errors, 'sorgu_gunu': days}


def produce(fixture, now, days=90, fetch=get_json):
    created = tarih_utc(fixture.get('olusturulma_utc'))
    if created is None or created > now + timedelta(minutes=5) or now - created > timedelta(hours=24):
        raise ValueError('FIKSTUR_GUNCEL_DEGIL: fikstur_yeni.py ile yeniden olusturun')
    matches = fixture.get('maclar')
    if not isinstance(matches, list):
        raise ValueError('Gecersiz maclar listesi')
    by_league = defaultdict(list)
    status = Counter()
    for match in matches:
        if not isinstance(match, dict):
            status['GECERSIZ_MAC'] += 1; continue
        kickoff = tarih_utc(match.get('tarih'))
        if kickoff is None or kickoff <= now:
            status['BASLAMIS_VEYA_TARIHSIZ'] += 1; continue
        league = match.get('lig_kodu')
        if league not in LIGLER:
            status['LIG_BILINMIYOR'] += 1; continue
        by_league[league].append(match)
    predictions = []
    audit = {}
    for league, fixtures in sorted(by_league.items()):
        teams, provenance = historical_stats(league, now, days, fetch)
        audit[league] = {'lig': LIGLER[league], **provenance, 'takim_sayisi': len(teams)}
        # Partial source failures cannot be silently treated as complete history.
        if provenance['hata_gunu'] > max(2, days // 10) or provenance['tamamlanmis_mac'] < 10:
            status['GECMIS_VERI_EKSIK'] += len(fixtures)
            audit[league]['durum'] = 'YETERSIZ_VERI'; continue
        index = indeks_olustur(teams)
        for match in fixtures:
            home = otomatik_eslestir(match.get('ev_sahibi'), teams, index)
            away = otomatik_eslestir(match.get('deplasman'), teams, index)
            if not home or not away or home == away:
                status['TAKIM_ESLESMEDI'] += 1; continue
            if min(teams[home]['mac'], teams[away]['mac']) < 5:
                status['YETERSIZ_TAKIM_GECMISI'] += 1; continue
            try:
                result = mac_analizi(home, away, teams)
            except (ValueError, ArithmeticError, KeyError, TypeError, ZeroDivisionError):
                status['MODEL_HATASI'] += 1; continue
            predictions.append({
                'id': match.get('id'), 'tarih': match['tarih'], 'lig_kodu': league,
                'lig': LIGLER[league], 'ev_sahibi': match['ev_sahibi'],
                'deplasman': match['deplasman'], 'istatistik_ev': home,
                'istatistik_deplasman': away, 'tahmin': result,
                'hesaplama_zamani_utc': now.isoformat(),
                'veri_kaynagi': 'ESPN tamamlanmis mac skorları',
                'gecmis_gun': days, 'kaynak_mac_sayisi': provenance['tamamlanmis_mac'],
                'gol_gecmisi': {
                'ev': teams[home]['son_maclar'],
                'dep': teams[away]['son_maclar'],
                },
            })
            status['TAHMIN_URETILDI'] += 1
    return {'olusturulma_utc': now.isoformat(), 'model': 'TIPSTER PRO V18',
            'not': 'Model olasiliklari kalibre edilmis basari oranlari degildir.',
            'tahminler': predictions, 'durum_sayilari': dict(status), 'lig_denetimi': audit}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fikstur', default='gelecek_maclar.json')
    parser.add_argument('--cikti', default='v18_yeni_tahminler.json')
    parser.add_argument('--gecmis-gun', type=int, default=90)
    args = parser.parse_args()
    if not 30 <= args.gecmis_gun <= 180:
        parser.error('--gecmis-gun 30..180 olmali')
    fixture = json.loads(Path(args.fikstur).read_text(encoding='utf-8'))
    result = produce(fixture, datetime.now(timezone.utc), args.gecmis_gun)
    output = Path(args.cikti)
    if output.exists():
        raise FileExistsError(f'Eski cikti korunuyor: {output}; yeni dosya adi kullanin')
    temp = output.with_suffix(output.suffix + '.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, output)
    print('URETILEN:', len(result['tahminler']), 'DURUM:', result['durum_sayilari'])

if __name__ == '__main__':
    main()
