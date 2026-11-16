"""TIPSTER PRO - Sekiz ek lig icin bagimsiz gol tahminleri.

Girdi: gelecek_maclar.json, tipster_ek_lig_gecmis.json
Cikti: tipster_ek_lig_tahminler.json, tipster_ek_lig_eslesmeyenler.json
V2/V4 veya kilitli arsiv dosyalarini degistirmez.
"""
import json
import math
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

LIGLER = {
    'bra.1', 'arg.1', 'den.1', 'swe.1',
    'mex.1', 'usa.1', 'col.1', 'rsa.1',
    'aut.1', 'aus.1', 'chn.1',
    'uefa.europa', 'uefa.europa.conf'
}
    
    
    

GECMIS = Path('tipster_ek_lig_gecmis.json')
FIKSTUR = Path('gelecek_maclar.json')
CIKTI = Path('tipster_ek_lig_tahminler.json')
EKSIK = Path('tipster_ek_lig_eslesmeyenler.json')


def oku(path):
    return json.loads(path.read_text(encoding='utf-8'))


def kaydet(path, veri):
    gecici = path.with_suffix(path.suffix + '.tmp')
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(gecici, path)


def norm(ad):
    s = unicodedata.normalize('NFKD', str(ad).casefold())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s)


def tarih_oku(deger):
    d = datetime.fromisoformat(str(deger).replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Saat dilimi eksik')
    return d.astimezone(timezone.utc)


def ust_yuzde(lam, sinir):
    # >= 2, 3, 4 gol olasiligi (Poisson).
    terim = math.exp(-lam)
    toplam = terim
    for k in range(1, sinir):
        terim *= lam / k
        toplam += terim
    return round(100 * max(0, min(1, 1 - toplam)), 2)


def main():
    gecmis = oku(GECMIS).get('maclar')
    fikstur = oku(FIKSTUR).get('maclar')
    if not isinstance(gecmis, dict) or not isinstance(fikstur, list):
        raise ValueError('Girdi dosyalarinin bicimi beklenenden farkli')

    simdi = datetime.now(timezone.utc)
    tarihli = defaultdict(list)
    adlar = defaultdict(lambda: defaultdict(set))
    for mac in gecmis.values():
        if not isinstance(mac, dict) or mac.get('lig') not in LIGLER:
            continue
        try:
            t = tarih_oku(mac['tarih_utc'])
            ev, dep = norm(mac['ev']), norm(mac['dep'])
            a, b = int(mac['ev_gol']), int(mac['dep_gol'])
            if not ev or not dep or ev == dep or min(a, b) < 0 or t >= simdi:
                continue
            lig = mac['lig']
            tarihli[lig].append((t, ev, dep, a, b))
            adlar[lig][ev].add(str(mac['ev']))
            adlar[lig][dep].add(str(mac['dep']))
        except (KeyError, ValueError, TypeError):
            continue

    sonuc, eksikler = [], []
    for mac in fikstur:
        if not isinstance(mac, dict) or mac.get('lig_kodu') not in LIGLER:
            continue
        lig = mac['lig_kodu']
        kayit = {k: mac.get(k) for k in ('id', 'tarih', 'lig_kodu', 'lig', 'ev_sahibi', 'deplasman')}
        try:
            baslama = tarih_oku(mac['tarih'])
        except (KeyError, ValueError, TypeError):
            eksikler.append({**kayit, 'neden': 'GECERSIZ_TARIH'})
            continue
        if baslama <= simdi:
            continue

        ev = norm(mac.get('ev_sahibi', ''))
        dep = norm(mac.get('deplasman', ''))
        lig_maclari = [x for x in tarihli[lig] if x[0] < baslama]
        # Yalnizca kesin ad eslesmesi; belirsiz benzerlikleri rapora yaz.
        ad_kumesi = {x[1] for x in lig_maclari} | {x[2] for x in lig_maclari}
        bulunmayan = [taraf for taraf, ad in [('ev', ev), ('dep', dep)] if ad not in ad_kumesi]
        if bulunmayan:
            eksikler.append({**kayit, 'neden': 'TAKIM_ESLESMEDI', 'taraflar': bulunmayan})
            continue

        lig_sayisi = len(lig_maclari)
        ev_mac = [(a, b) for _, h, _, a, b in lig_maclari if h == ev]
        dep_mac = [(b, a) for _, _, d, a, b in lig_maclari if d == dep]
        if lig_sayisi < 30 or len(ev_mac) < 5 or len(dep_mac) < 5:
            eksikler.append({**kayit, 'neden': 'YETERSIZ_GECMIS', 'lig_mac': lig_sayisi,
                              'ev_ic_saha': len(ev_mac), 'dep_dis_saha': len(dep_mac)})
            continue

        lig_ev = sum(x[3] for x in lig_maclari) / lig_sayisi
        lig_dep = sum(x[4] for x in lig_maclari) / lig_sayisi
        # 5 maclik onbilgi, kucuk ornekleri lig ortalamasina yaklastirir.
        def ortalama(maclar, sutun, prior):
            return (sum(x[sutun] for x in maclar) + 5 * prior) / (len(maclar) + 5)
        ev_atak = ortalama(ev_mac, 0, lig_ev)
        ev_yeme = ortalama(ev_mac, 1, lig_dep)
        dep_atak = ortalama(dep_mac, 0, lig_dep)
        dep_yeme = ortalama(dep_mac, 1, lig_ev)
        lam_ev = max(0.05, min(4.0, ev_atak * dep_yeme / max(lig_ev, 0.2)))
        lam_dep = max(0.05, min(4.0, dep_atak * ev_yeme / max(lig_dep, 0.2)))
        lam = lam_ev + lam_dep
        p15, p25, p35 = (ust_yuzde(lam, k) for k in (2, 3, 4))
        karar = ('3.5 UST' if p35 >= 65 else '2.5 UST' if p25 >= 65
                 else '1.5 UST' if p15 >= 75 else 'RISKLI')
        sonuc.append({**kayit, 'model': 'EK_LIG_DENEYSEL', 'hesaplama_zamani_utc': simdi.isoformat(),
                      'tahmin': karar, 'olasiliklar': {'1.5_ust': p15, '2.5_ust': p25, '3.5_ust': p35},
                      'beklenen_gol': round(lam, 3), 'lig_gecmis_mac': lig_sayisi,
                      'ev_ic_saha_mac': len(ev_mac), 'dep_dis_saha_mac': len(dep_mac),
                      'kilitli': False})

    kaydet(CIKTI, {'olusturulma_utc': simdi.isoformat(), 'tahminler': sonuc})
    kaydet(EKSIK, {'olusturulma_utc': simdi.isoformat(), 'kayitlar': eksikler})
    print('EK LIG TAHMIN:', len(sonuc), '| ESLESMEYEN/YETERSIZ:', len(eksikler))
    for neden in sorted({x['neden'] for x in eksikler}):
        print(neden, sum(x['neden'] == neden for x in eksikler))
    print('NOT: Deneysel tahmin; mevcut kilitli arÅive dokunulmadi.')


if __name__ == '__main__':
    main()
