"""TIPSTER PRO: read-only coverage audit; never edits prediction archives."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/London')

def load(path, default):
    p = Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def day(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return d.astimezone(TZ).date().isoformat() if d.tzinfo else 'INVALID'
    except (ValueError, TypeError, AttributeError):
        return 'INVALID'

def main():
    fixture = load('gelecek_maclar.json', {})
    v2 = load('tipster_v2_sonuc.json', {})
    skipped = load('tipster_v2_eksikler.json', [])
    games = fixture.get('maclar', [])
    preds = v2.get('predictions', [])
    if not isinstance(games, list) or not isinstance(preds, list) or not isinstance(skipped, list):
        raise ValueError('Unexpected fixture/V2 report format')
    counts = {}
    for game in games:
        date = day(game.get('tarih'))
        slot = counts.setdefault(date, {'fikstur': 0, 'v2_tahmin': 0, 'v2_eksik': 0, 'nedenler': Counter(), 'ligler': Counter()})
        slot['fikstur'] += 1
        slot['ligler'][game.get('lig_kodu', '?')] += 1
    for p in preds:
        slot = counts.setdefault(day(p.get('tarih')), {'fikstur': 0, 'v2_tahmin': 0, 'v2_eksik': 0, 'nedenler': Counter(), 'ligler': Counter()})
        slot['v2_tahmin'] += 1
    for p in skipped:
        slot = counts.setdefault(day(p.get('tarih')), {'fikstur': 0, 'v2_tahmin': 0, 'v2_eksik': 0, 'nedenler': Counter(), 'ligler': Counter()})
        slot['v2_eksik'] += 1
        slot['nedenler'][p.get('neden', '?')] += 1
    clean = {d: {'fikstur': c['fikstur'], 'v2_tahmin': c['v2_tahmin'], 'v2_eksik': c['v2_eksik'], 'nedenler': dict(c['nedenler']), 'ligler': dict(c['ligler'])} for d,c in sorted(counts.items())}
    result = {'denetim_utc': datetime.now(timezone.utc).isoformat(), 'saat_dilimi': 'Europe/London', 'fikstur_olusturulma_utc': fixture.get('olusturulma_utc'), 'fikstur_toplam': len(games), 'v2_tahmin_toplam': len(preds), 'v2_eksik_toplam': len(skipped), 'gunler': clean, 'uyarilar': ['Bu rapor yalnizca ESPN fiksturundeki maclari sayar; Flashscore toplam kapsamini olcmez.', 'Fikstur toplama baslamis/bitmis maclari disladigi icin gunluk tam takvim degildir.', 'V2 model ciktilari bagimsiz dogrulanmis tahminler degildir.']}
    Path('tipster_kapsam_raporu.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['TIPSTER PRO - KAPSAM DENETIMI', 'Saat dilimi: Europe/London', f"Fikstur: {len(games)} | V2: {len(preds)} | Eksik: {len(skipped)}", '']
    for d, c in clean.items():
        lines.append(f"{d} | fikstur {c['fikstur']} | V2 {c['v2_tahmin']} | eksik {c['v2_eksik']}")
        if c['nedenler']:
            lines.append('  Nedenler: ' + ', '.join(f'{k}={v}' for k,v in sorted(c['nedenler'].items())))
    lines += ['', *result['uyarilar']]
    Path('tipster_kapsam_raporu.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
