"""Safe, opt-in V19 staging merge for pre-match predictions.

Never modifies V18 source, V18 archives, or deployed Pages. Only verified
zero-cost sources with permission for public reuse can be accepted.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utc(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None


def identity(record):
    return (str(record.get('lig_kodu', '')).strip(), str(record.get('id', '')).strip())


def combine(v18, additions, allowed, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(v18, dict) or v18.get('model') != 'TIPSTER PRO V18':
        raise ValueError('Gecersiz V18 formati')
    originals = v18.get('tahminler')
    if not isinstance(originals, list):
        raise ValueError('V18 tahmin listesi eksik')
    if not isinstance(additions, list) or not isinstance(allowed, list):
        raise ValueError('V19 veya kaynak izin listesi gecersiz')
    approved = {
        x['kaynak_kodu'] for x in allowed
        if isinstance(x, dict) and isinstance(x.get('kaynak_kodu'), str)
        and x.get('tamamen_ucretsiz') is True
        and x.get('panel_yayin_izni') is True
        and x.get('ucretli_plan_gerekiyor') is False
        and isinstance(x.get('izin_dayanagi'), str)
        and x['izin_dayanagi'].strip()
    }
    output = list(originals)
    known = {identity(x) for x in originals if isinstance(x, dict)}
    report = {'v18_korunan': len(originals), 'v19_eklenen': 0,
              'v19_izin_yok': 0, 'v19_gecersiz': 0, 'v19_tekrar': 0}
    for row in additions:
        if not isinstance(row, dict):
            report['v19_gecersiz'] += 1
            continue
        if row.get('kaynak_kodu') not in approved:
            report['v19_izin_yok'] += 1
            continue
        key = identity(row)
        kickoff = utc(row.get('tarih'))
        calculated = utc(row.get('hesaplama_zamani_utc'))
        if (not all(key) or not row.get('ev_sahibi') or
                not row.get('deplasman') or
                not isinstance(row.get('tahmin'), dict) or not row['tahmin'] or
                kickoff is None or calculated is None or
                not calculated < kickoff or not now < kickoff or
                calculated > now + timedelta(minutes=5)):
            report['v19_gecersiz'] += 1
            continue
        if key in known:
            report['v19_tekrar'] += 1
            continue
        clean = dict(row)
        clean['model_katmani'] = 'V19'
        clean['model_durumu'] = 'YENI_ONERI_KILITLI_DEGIL'
        output.append(clean)
        known.add(key)
        report['v19_eklenen'] += 1
    result = dict(v18)
    result['tahminler'] = output
    result['v19_entegrasyon_denetimi'] = report
    result['not_v19'] = 'V19 eklemeleri kilitli secim veya dogrulanmis basari degildir.'
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--v18', required=True)
    p.add_argument('--v19', required=True)
    p.add_argument('--izinler', required=True)
    p.add_argument('--cikti', required=True)
    args = p.parse_args()
    dest = Path(args.cikti)
    if dest.exists():
        raise SystemExit('Cikti zaten var; eski kayit korunuyor.')
    v18 = json.loads(Path(args.v18).read_text(encoding='utf-8'))
    v19 = json.loads(Path(args.v19).read_text(encoding='utf-8'))
    permissions = json.loads(Path(args.izinler).read_text(encoding='utf-8'))
    result = combine(v18, v19, permissions)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('V19 DENETIM:', result['v19_entegrasyon_denetimi'])

if __name__ == '__main__':
    main()
