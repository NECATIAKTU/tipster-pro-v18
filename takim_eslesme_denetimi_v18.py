"""Offline and read-only audit of fixture team-name matching.

No network calls and no changes to predictions or fixtures.
"""
import csv
import json
from collections import Counter
from pathlib import Path
from tahmin_motoru import LIGLER, takim_bul, indeks_olustur

ROOT = Path(__file__).resolve().parent


def denetle(kayitlar, takim_listeleri):
    rapor = []
    sayac = Counter()
    for m in kayitlar:
        lig = m['veri_ligi']
        adlar = takim_listeleri.get(lig)
        if not adlar:
            sayac['VERI_LIGI_LISTESI_YOK'] += 1
            rapor.append({**m, 'durum': 'VERI_LIGI_LISTESI_YOK'})
            continue
        indeks = indeks_olustur(adlar)
        ev = takim_bul(m['ev_sahibi'], lig, adlar, indeks)
        dep = takim_bul(m['deplasman'], lig, adlar, indeks)
        durum = 'ESLESTI' if ev and dep and ev != dep else 'TAKIM_ESLESMEDI'
        sayac[durum] += 1
        rapor.append({**m, 'eslesen_ev_yeni': ev, 'eslesen_deplasman_yeni': dep, 'durum': durum})
    return dict(sayac), rapor


def main():
    kayitlar = json.loads((ROOT / 'eslesmeyen_takimlar.json').read_text(encoding='utf-8'))
    # Historical mismatch log does not include authoritative full league rosters.
    # Never infer that a team exists in a league from its name alone.
    sayac, rapor = denetle(kayitlar, {})
    sonuc = {'aciklama': 'Takim listeleri olmadan eslesme basarisi iddia edilmez.',
             'kayit_sayisi': len(kayitlar), 'sayac': sayac, 'kayitlar': rapor}
    (ROOT / 'takim_eslesme_denetim_v18.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Kayit:', len(kayitlar), 'Durum:', sayac)


if __name__ == '__main__':
    main()
