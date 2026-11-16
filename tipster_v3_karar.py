"""TIPSTER PRO V3: non-destructive decision/report layer over V2 results.
Run after tipster_pro_v2.py. Does not change historical archives.
"""
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

INPUT = Path('tipster_v2_sonuc.json')
SKIPPED = Path('tipster_v2_eksikler.json')
OUTPUT = Path('tipster_v3_kararlar.json')
REPORT = Path('tipster_v3_rapor.txt')

# Initial experimental thresholds, NOT validated hit rates.
THRESHOLDS = [('6.5_ust', 55), ('5.5_ust', 55), ('4.5_ust', 55),
              ('3.5_ust', 60), ('2.5_ust', 65), ('1.5_ust', 75)]

def poisson_over(lam, limit):
    if not math.isfinite(lam) or lam < 0:
        raise ValueError('Invalid expected goals')
    term = math.exp(-lam)
    cdf = term
    for k in range(1, limit + 1):
        term *= lam / k
        cdf += term
    return round(100 * max(0.0, min(1.0, 1.0 - cdf)), 2)

def decide(analysis):
    if not isinstance(analysis, dict):
        return {'karar': 'VERI EKSIK', 'neden': 'Analiz bulunamadi'}
    try:
        lam = float(analysis['beklenen_gol'])
        if not math.isfinite(lam) or lam < 0:
            raise ValueError('Invalid lambda')
    except (KeyError, TypeError, ValueError):
        return {'karar': 'VERI EKSIK', 'neden': 'Beklenen gol gecersiz'}

    # V2 rounded expected goals; values are approximate model estimates.
    odds = {f'{n}.5_ust': poisson_over(lam, n) for n in range(1, 7)}
    odds['7_plus_gol'] = odds['6.5_ust']
    # Without separately estimated home/away lambdas, BTTS is not identifiable.
    odds['gol_var_yok'] = 'HESAPLANAMADI'
    selection = next((name.replace('_ust', ' UST') for name, threshold in THRESHOLDS
                      if odds[name] >= threshold), 'RISKLI')
    return {'karar': selection, 'beklenen_gol': lam, 'olasiliklar': odds,
            'model_durumu': 'DOGRULANMAMIS',
            'neden': 'Esikler deneyseldir; geriye donuk test gerektirir'}

def main():
    source = json.loads(INPUT.read_text(encoding='utf-8'))
    predictions = source.get('predictions', [])
    skipped = json.loads(SKIPPED.read_text(encoding='utf-8')) if SKIPPED.exists() else []
    now = datetime.now(timezone.utc)
    rows = []
    counts = Counter()
    for p in predictions:
        decision = decide(p.get('analiz'))
        row = {'id': p.get('id'), 'tarih': p.get('tarih'), 'lig': p.get('espn_lig'),
               'ev': p.get('ev'), 'dep': p.get('dep'), 'v2_created_at_utc': p.get('created_at_utc'),
               'v3_created_at_utc': now.isoformat(), 'kaynak': 'TIPSTER_V2', **decision}
        rows.append(row)
        counts[decision['karar']] += 1
    for p in skipped:
        rows.append({'id': p.get('id'), 'tarih': p.get('tarih'), 'lig': p.get('lig'),
                     'ev': p.get('ev'), 'dep': p.get('dep'), 'karar': 'VERI EKSIK',
                     'neden': p.get('neden', 'bilinmiyor'),
                     'v3_created_at_utc': now.isoformat()})
        counts['VERI EKSIK'] += 1
    result = {'created_at_utc': now.isoformat(), 'model': 'TIPSTER_V3_EXPERIMENTAL',
              'not': 'Not a pre-match locked forecast for games already started. No archive changes.',
              'toplam': len(rows), 'sayac': dict(counts), 'kayitlar': rows}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['TIPSTER PRO V3 - DENEYSEL TAHMIN DAGILIMI',
             'Olusturulma UTC: ' + now.isoformat(),
             'Bu rapor eski tahminleri geriye donuk olarak degistirmez.',
             f'TOPLAM: {len(rows)}',
             *[f'{k}: {v}' for k, v in counts.most_common()]]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
