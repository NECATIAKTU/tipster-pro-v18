#!/usr/bin/env python3
"""TIPSTER PRO V18: immutable pre-match picks and verified ESPN full-time results.

Pure Python, standard library only. Independent of prediction engine calculations.
Old archives without a locked market are NEVER assigned a backdated recommendation.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gercek_tahmin_v18 import get_json

ARSIV = Path('v18_tahmin_arsivi.json')
SONUCLAR = Path('v18_dogrulanan_sonuclar.json')
AYARLAR = Path('v18_sonuc_ayarlari.json')
CIZGILER = ('1.5', '2.5', '3.5', '4.5', '5.5', '6.5')


def utc(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo is not None else None
    except ValueError:
        return None


def oku(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def yaz(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def kimlik(match):
    if not isinstance(match, dict):
        return None
    league = str(match.get('lig_kodu') or '').strip()
    event = str(match.get('id') or '').strip()
    if not league or not event:
        return None
    if '|' in event:
        prefix, suffix = event.split('|', 1)
        if prefix != league or not suffix or '|' in suffix:
            return None
        return event
    return f'{league}|{event}'


def olasiliklar(match):
    raw = match.get('tahmin') if isinstance(match, dict) else None
    if not isinstance(raw, dict):
        return {}
    inner = raw.get('olasiliklar')
    sources = [inner, raw] if isinstance(inner, dict) else [raw]
    result = {}
    for line in CIZGILER:
        field = f'{line}_ust'
        for source in sources:
            candidate = source.get(field)
            try:
                value = float(str(candidate).replace('%', '').replace(',', '.'))
            except (TypeError, ValueError):
                continue
            if 0 <= value <= 100:
                result[field] = value
                break
    return result


def ayarlar_oku():
    cfg = oku(AYARLAR, {})
    if not isinstance(cfg, dict):
        raise ValueError('Ayar dosyasi JSON nesnesi olmali')
    thresholds = cfg.get('esikler', {})
    if not isinstance(thresholds, dict) or set(thresholds) != set(CIZGILER):
        raise ValueError('Tum 1.5-6.5 gol cizgileri icin esik gerekli')
    for k, v in thresholds.items():
        if type(v) not in (float, int) or not 0 <= v <= 100:
            raise ValueError(f'Gecersiz esik: {k}')
    if cfg.get('secim_politikasi') != 'YUKSEK_CIZGIDEN_BASLA_V1':
        raise ValueError('Bilinmeyen secim politikasi')
    if type(cfg.get('otomatik_secim_aktif')) is not bool:
        raise ValueError('otomatik_secim_aktif true/false olmali')
    return cfg


def kilitli_secim_uret(probabilities, cfg=None):
    """Proposed transparent policy; not a model-validated betting recommendation."""
    cfg = cfg or ayarlar_oku()
    if not cfg['otomatik_secim_aktif']:
        return None
    for line in reversed(CIZGILER):
        if probabilities.get(f'{line}_ust', -1) >= cfg['esikler'][line]:
            return f'{line} UST'
    return 'RISKLI'


def arsivle(source, now=None):
    now = now or datetime.now(timezone.utc)
    data = oku(Path(source), {})
    if not isinstance(data, dict) or data.get('model') != 'TIPSTER PRO V18' or not isinstance(data.get('tahminler'), list):
        raise ValueError('Gecersiz V18 model ciktisi')
    cfg = ayarlar_oku()
    archive = oku(ARSIV, [])
    if not isinstance(archive, list):
        raise ValueError('Arsiv JSON listesi olmali')
    existing = {r.get('kimlik') for r in archive if isinstance(r, dict)}
    added = skipped = updated = 0

    for match in data['tahminler']:
        id_ = kimlik(match)
        if not id_:
            skipped += 1
            continue

        if id_ in existing:
            record = next(
                (r for r in archive if isinstance(r, dict) and r.get('kimlik') == id_),
                None,
            )
            start = utc(record['mac'].get('tarih')) if record and isinstance(record.get('mac'), dict) else None
            created = utc(record['mac'].get('hesaplama_zamani_utc')) if record and isinstance(record.get('mac'), dict) else None

            if (
                record
                and 'kilitli_secim' not in record
                and record.get('durum') == 'BEKLIYOR'
                and start
                and created
                and created < start
                and now < start
            ):
                probabilities = record.get('olasiliklar') or olasiliklar(record['mac'])
                choice = kilitli_secim_uret(probabilities, cfg)
                if choice is not None:
                    record['kilitli_secim'] = choice
                    record['kilit_zamani_utc'] = now.isoformat()
                    record['secim_politikasi'] = cfg['secim_politikasi']
                    record['secim_esikleri'] = dict(cfg['esikler'])
                    updated += 1
            skipped += 1
            continue

        start = utc(match.get('tarih'))
        created = utc(match.get('hesaplama_zamani_utc'))
        if not start or not created or not (created <= now < start):
            skipped += 1
            continue

        probabilities = olasiliklar(match)
        choice = kilitli_secim_uret(probabilities, cfg)
        record = {
            'kimlik': id_,
            'mac': dict(match),
            'kilit_zamani_utc': now.isoformat(),
            'durum': 'BEKLIYOR',
            'sonuc': None,
            'olasiliklar': probabilities,
        }
        if choice is not None:
            record['kilitli_secim'] = choice
            record['secim_politikasi'] = cfg['secim_politikasi']
            record['secim_esikleri'] = dict(cfg['esikler'])
        archive.append(record)
        existing.add(id_)
        added += 1

    if added or updated:
        yaz(ARSIV, archive)
    print(f'ARSIV: toplam={len(archive)} yeni={added} guncellenen={updated} atlanan={skipped}')
    return added


def _completed_event(event):
    if not isinstance(event, dict):
        return None
    status = event.get('status') or {}
    category = status.get('type') or {}
    if category.get('completed') is not True:
        return None
    try:
        competitors = event['competitions'][0]['competitors']
        home = next(c for c in competitors if c.get('homeAway') == 'home')
        away = next(c for c in competitors if c.get('homeAway') == 'away')
        hs, as_ = int(home['score']), int(away['score'])
        if min(hs, as_) < 0:
            return None
        event_id = str(event['id']).strip()
        if not event_id:
            return None
    except (KeyError, IndexError, StopIteration, ValueError, TypeError):
        return None
    return event_id, {
        'ev_gol': hs, 'dep_gol': as_, 'toplam_gol': hs + as_,
        'skor': f'{hs}-{as_}', 'durum': 'TAMAMLANDI',
        'kaynak': 'ESPN',
    }


def espn_sonuclari(archive, fetch=None, now=None):
    fetch = fetch or get_json
    now = now or datetime.now(timezone.utc)
    dates = set()
    for record in archive:
        if not isinstance(record, dict) or record.get('durum') == 'DOGRULANDI':
            continue
        match = record.get('mac') or {}
        start = utc(match.get('tarih'))
        league = match.get('lig_kodu')
        if start and isinstance(league, str) and league and start <= now:
            for offset in (-1, 0, 1):
                dates.add((league, (start + timedelta(days=offset)).date()))
    results, failed = {}, []
    for league, day in sorted(dates):
        try:
            payload = fetch(league, day)
            if not isinstance(payload, dict) or not isinstance(payload.get('events'), list):
                raise ValueError('events bulunamadi')
            for event in payload['events']:
                parsed = _completed_event(event)
                if parsed is None:
                    continue
                event_id, score = parsed
                if '|' in event_id:
                    prefix, suffix = event_id.split('|', 1)
                    if prefix != league or not suffix or '|' in suffix:
                        continue
                    identifier = event_id
                else:
                    identifier = f'{league}|{event_id}'
                old = results.get(identifier)
                if old is not None and old['skor'] != score['skor']:
                    print('UYARI: API skor celiskisi:', identifier)
                    results.pop(identifier, None)
                    continue
                results[identifier] = score
        except (OSError, ValueError, KeyError, TypeError, TimeoutError) as e:
            failed.append(f'{league} {day}: {e}')
    for line in failed[:20]:
        print('UYARI: ESPN sorgusu basarisiz:', line)
    print(f'ESPN: taranan_lig_gun={len(dates)} sorgu_hatasi={len(failed)} bulunan={len(results)}')
    return results


def _grade(record, score):
    match = record.get('mac') or {}
    start = utc(match.get('tarih'))
    made = utc(match.get('hesaplama_zamani_utc'))
    locked = utc(record.get('kilit_zamani_utc'))
    selection = str(record.get('kilitli_secim') or '').replace(',', '.').upper().strip()
    if not (start and made and locked and made < start and locked < start):
        return None
    m = re.fullmatch(r'(1\.5|2\.5|3\.5|4\.5|5\.5|6\.5)\s+UST', selection)
    if not m:
        return None
    return 'DOGRU' if score['toplam_gol'] > float(m.group(1)) else 'YANLIS'


def kontrol(fetch=None, now=None):
    now = now or datetime.now(timezone.utc)
    archive = oku(ARSIV, [])
    if not isinstance(archive, list):
        raise ValueError('Arsiv JSON listesi olmali')
    found = espn_sonuclari(archive, fetch=fetch, now=now)
    output = []
    for record in archive:
        if not isinstance(record, dict):
            raise ValueError('Arsivde gecersiz kayit var')
        record = dict(record)
        key = record.get('kimlik')
        previous = record.get('sonuc') if record.get('durum') == 'DOGRULANDI' else None
        fresh = found.get(key)
        if isinstance(previous, dict) and isinstance(previous.get('toplam_gol'), int):
            if fresh is not None and fresh.get('skor') != previous.get('skor'):
                record['skor_uyarisi'] = 'ESPN_SKOR_DEGISTI_KONTROL_ET'
            score = previous
        else:
            score = fresh
        if score is None:
            record['durum'] = 'BEKLIYOR'
            record['sonuc'] = None
            record.pop('tahmin_sonucu', None)
            output.append(record)
            continue
        record['durum'] = 'DOGRULANDI'
        record['sonuc'] = score
        if previous is None:
            record['sonuc_dogrulama_zamani_utc'] = now.isoformat()
        probs = record.get('olasiliklar') or {}
        record['cizgi_sonuclari'] = {
            f'{line}_ust': {
                'model_yuzdesi': probs.get(f'{line}_ust'),
                'gerceklesti': score['toplam_gol'] > float(line),
            }
            for line in CIZGILER if probs.get(f'{line}_ust') is not None
        }
        grade = _grade(record, score)
        if grade:
            record['tahmin_sonucu'] = grade
        else:
            record.pop('tahmin_sonucu', None)
        output.append(record)
    if output != archive:
        yaz(ARSIV, output)
    wins = sum(x.get('tahmin_sonucu') == 'DOGRU' for x in output)
    losses = sum(x.get('tahmin_sonucu') == 'YANLIS' for x in output)
    confirmed = sum(x.get('durum') == 'DOGRULANDI' for x in output)
    results = {
        'model': 'TIPSTER PRO V18', 'olusturulma_utc': now.isoformat(),
        'toplam_arsiv': len(output), 'dogrulanan_mac': confirmed,
        'bekleyen_mac': len(output) - confirmed,
        'degerlendirilen_tahmin': wins + losses, 'dogru': wins, 'yanlis': losses,
        'basari_yuzdesi': round(100 * wins / (wins + losses), 2) if wins + losses else None,
        'not': 'Yalnizca mac oncesi kilitli UST secimleri basari hesabina girer. Model olasiliklari basari orani degildir.',
        'kayitlar': output,
    }
    yaz(SONUCLAR, results)
    print('DOGRULANAN:', confirmed, 'BEKLEYEN:', len(output) - confirmed)
    print('DOGRU:', wins, 'YANLIS:', losses, 'BASARI:', results['basari_yuzdesi'])
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arsivle', metavar='V18_JSON')
    parser.add_argument('--kontrol', action='store_true')
    args = parser.parse_args()
    if not args.arsivle and not args.kontrol:
        parser.print_help()
        return
    if args.arsivle:
        arsivle(args.arsivle)
    if args.kontrol:
        kontrol()


if __name__ == '__main__':
    main()

