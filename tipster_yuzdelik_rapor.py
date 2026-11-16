"""TIPSTER PRO: Eslesen maclar icin tahmin + UST/ALT model yuzdesi.
Salt okunur giris; arsivleri degistirmez. Model yuzdeleri kalibre edilmemistir.
"""
import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

GIRDI = Path('tipster_birlesik_rapor.json')
CSV = Path('tipster_yuzdelik_rapor.csv')
TXT = Path('tipster_yuzdelik_rapor.txt')


def yuzde(deger):
    if isinstance(deger, bool):
        return None
    try:
        n = float(deger)
    except (ValueError, TypeError):
        return None
    return round(n, 2) if math.isfinite(n) and 0 <= n <= 100 else None


def sec(ust):
    """2.5 cizgisi temel; digerleri bilgi amacli raporlanir.
    Guven esigi uydurulmaz; yuksek olasilik basari garantisi degildir.
    """
    if ust[1] is None:
        return 'HESAPLANAMADI', None
    if ust[1] >= 50:
        return '2.5 UST', ust[1]
    return '2.5 ALT', round(100 - ust[1], 2)


def rapor():
    obj = json.loads(GIRDI.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or not isinstance(obj.get('maclar'), list):
        raise ValueError('Birlesik raporda maclar listesi bulunamadi')
    satirlar, kimlikler = [], set()
    for g in obj['maclar']:
        if not isinstance(g, dict) or not isinstance(g.get('kayit'), dict):
            continue
        k = g['kayit']
        kimlik = str(k.get('id') or '').strip()
        if not kimlik or kimlik in kimlikler:
            continue
        kimlikler.add(kimlik)
        p = k.get('analiz', {}) if g.get('kaynak') == 'V2' else k.get('olasiliklar', {})
        if not isinstance(p, dict):
            p = {}
        ust = [yuzde(p.get(f'{s}_ust')) for s in ('1.5', '2.5', '3.5')]
        alt = [round(100 - x, 2) if x is not None else None for x in ust]
        tercih, oran = sec(ust)
        ev = k.get('ev') or k.get('ev_sahibi') or ''
        dep = k.get('dep') or k.get('deplasman') or ''
        satirlar.append({
            'id': kimlik, 'tarih_utc': k.get('tarih', ''), 'kaynak': g.get('kaynak', ''),
            'mac': f'{ev} - {dep}', 'hesaplama_zamani': k.get('hesaplama_zamani') or k.get('hesaplama_zamani_utc') or k.get('created_at') or '', 'tahmin': tercih, 'model_yuzdesi': oran,
            '1.5_ust': ust[0], '1.5_alt': alt[0],
            '2.5_ust': ust[1], '2.5_alt': alt[1],
            '3.5_ust': ust[2], '3.5_alt': alt[2],
        })
    satirlar.sort(key=lambda x: (x['tarih_utc'], x['mac']))
    alanlar = ['id', 'tarih_utc', 'kaynak', 'mac', 'hesaplama_zamani', 'tahmin', 'model_yuzdesi',
               '1.5_ust', '1.5_alt', '2.5_ust', '2.5_alt', '3.5_ust', '3.5_alt']
    tmp_csv = CSV.with_suffix('.csv.tmp')
    with tmp_csv.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        w.writerows(satirlar)
    os.replace(tmp_csv, CSV)
    lines = ['TIPSTER PRO - TAHMIN VE MODEL YUZDESI',
             f'Olusturulma UTC: {datetime.now(timezone.utc).isoformat()}',
             f'Model ciktisi: {len(satirlar)}',
             'NOT: Yuzdeler kalibre edilmis guven veya garanti degildir.',
             'NOT: Tercih 2.5 gol cizgisinde yuksek olasilikli taraftir; 1.5/3.5 ayrica gosterilir.', '']
    for r in satirlar:
        fmt = lambda v: f'%{v:.2f}' if v is not None else 'YOK'
        lines.append(f"{r['tarih_utc']} | {r['mac']} | {r['tahmin']} {fmt(r['model_yuzdesi'])}")
        lines.append(f"  1.5 UST {fmt(r['1.5_ust'])} / ALT {fmt(r['1.5_alt'])} | 2.5 UST {fmt(r['2.5_ust'])} / ALT {fmt(r['2.5_alt'])} | 3.5 UST {fmt(r['3.5_ust'])} / ALT {fmt(r['3.5_alt'])}")
    tmp_txt = TXT.with_suffix('.txt.tmp')
    tmp_txt.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.replace(tmp_txt, TXT)
    print('Tahmin ve yuzdelik:', len(satirlar), '| CSV:', CSV, '| TXT:', TXT)


if __name__ == '__main__':
    rapor()
