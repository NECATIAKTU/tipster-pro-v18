#!/usr/bin/env python3
"""Build panel data exclusively from the committed V18 archive."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from v18_sonuc_takip import kimlik, utc

LINES = tuple(f'{i}.5_ust' for i in range(1, 7))
CHOICES = {'RISKLI', *(f'{i}.5 UST' for i in range(1, 7))}


def convert(archive, now):
    if not isinstance(archive, list):
        raise ValueError('Arşiv liste olmalı')
    seen, clean = set(), []
    for record in archive:
        if not isinstance(record, dict):
            raise ValueError('Geçersiz arşiv kaydı')
        key, match = record.get('kimlik'), record.get('mac')
        if not key or key in seen or kimlik(match) != key:
            raise ValueError(f'Geçersiz veya tekrarlı kimlik: {key}')
        seen.add(key)
        start = utc(match.get('tarih'))
        if start is None:
            raise ValueError(f'Geçersiz maç tarihi: {key}')
        if start <= now or record.get('durum') != 'BEKLIYOR':
            continue
        made, locked = utc(match.get('hesaplama_zamani_utc')), utc(record.get('kilit_zamani_utc'))
        choice = record.get('kilitli_secim')
        if choice is None:
            continue
        if choice not in CHOICES or not made or not locked or not (made <= locked <= now < start):
            raise ValueError(f'Geçersiz kilit: {key}')
        probs = record.get('olasiliklar')
        if not isinstance(probs, dict) or any(type(probs.get(k)) not in (int, float) or not 0 <= probs[k] <= 100 for k in LINES):
            raise ValueError(f'Geçersiz olasılıklar: {key}')
        prediction = dict(match.get('tahmin') or {})
        prediction.update(probs)
        clean.append({**match, 'id': key, 'tahmin': prediction,
                      'olasiliklar': dict(probs), 'kilitli_secim': choice,
                      'kilit_zamani_utc': record['kilit_zamani_utc']})
    return {'model': 'TIPSTER PRO V18', 'olusturulma_utc': now.isoformat(),
            'not': 'Kilitli arşiv olasılıkları; başarı yüzdesi değildir.',
            'tahminler': clean, 'toplam_arsiv': len(archive)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('kaynak', help='Kalıcı V18 tahmin arşivi')
    p.add_argument('--sonuclar', default='v18_dogrulanan_sonuclar.json')
    p.add_argument('--cikti', default='panel_tahminler.json')
    a = p.parse_args()
    archive = json.loads(Path(a.kaynak).read_text(encoding='utf-8'))
    results = json.loads(Path(a.sonuclar).read_text(encoding='utf-8'))
    if results.get('kayitlar') != archive:
        raise ValueError('Arşiv ve sonuç dosyası farklı; yayın durduruldu')
    result = convert(archive, datetime.now(timezone.utc))
    out = Path(a.cikti)
    tmp = out.with_suffix(out.suffix + '.tmp')
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tmp.replace(out)
    print('Panel için kilitli V18 kayıtları:', len(result['tahminler']))

if __name__ == '__main__':
    main()
