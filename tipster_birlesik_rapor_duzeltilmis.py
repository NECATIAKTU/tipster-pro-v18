"""TIPSTER PRO: V2 ve ek lig raporlarini guvenli birlestirir.
Kaynak JSON'lara ve kilitli arsivlere dokunmaz.
Ilk denemede ciktilari _kontrol isimleriyle uretir.
"""
import json
import os
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

V2 = Path('tipster_v2_sonuc.json')
EK = Path('tipster_ek_lig_tahminler.json')
CIKTI = Path('tipster_birlesik_rapor_kontrol.json')
GUNLUK = Path('tipster_gunluk_tahminler_kontrol.txt')
LONDON = ZoneInfo('Europe/London')


def oku(path, alan):
    with path.open('r', encoding='utf-8') as f:
        veri = json.load(f)
    if not isinstance(veri, dict) or not isinstance(veri.get(alan), list):
        raise ValueError(f'{path}: {alan} listesi yok veya gecersiz')
    return veri[alan]


def atomik_yaz(path, metin):
    gecici = path.with_name(path.name + '.tmp')
    with gecici.open('w', encoding='utf-8') as f:
        f.write(metin)
    os.replace(gecici, path)


def zaman(mac):
    deger = mac.get('tarih')
    if not isinstance(deger, str):
        return None
    try:
        dt = datetime.fromisoformat(deger.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return None  # Saat dilimi bilinmiyorsa varsayma.
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def norm(deger):
    s = unicodedata.normalize('NFKD', str(deger or ''))
    return ''.join(c for c in s if not unicodedata.combining(c)).casefold().strip()


def imza(mac):
    lig = norm(mac.get('espn_lig') or mac.get('lig_kodu') or mac.get('lig'))
    ev = norm(mac.get('ev') or mac.get('ev_sahibi'))
    dep = norm(mac.get('dep') or mac.get('deplasman'))
    dt = zaman(mac)
    if not all((lig, ev, dep)) or dt is None:
        return None
    return (lig, dt.isoformat(), ev, dep)


def karar_ver(mac):
    analiz = mac.get('analiz') or mac.get('olasiliklar') or {}
    if not isinstance(analiz, dict):
        return 'RİSKLİ'
    for alan, esik, etiket in (
        ('3.5_ust', 65, '3.5 ÜST'),
        ('2.5_ust', 65, '2.5 ÜST'),
        ('1.5_ust', 75, '1.5 ÜST'),
    ):
        try:
            if float(analiz.get(alan, 0)) >= esik:
                return etiket
        except (TypeError, ValueError):
            continue
    return 'RİSKLİ'


def main():
    v2 = oku(V2, 'predictions')
    ek = oku(EK, 'tahminler')
    birlesik = []
    gorulen_id = set()
    gorulen_imza = set()
    tekrar = gecersiz = 0

    for kaynak, maclar in (('V2', v2), ('EK_LIG', ek)):
        for mac in maclar:
            if not isinstance(mac, dict):
                gecersiz += 1
                continue
            sig = imza(mac)
            if sig is None:
                gecersiz += 1
                continue
            kimlik = str(mac.get('id') or '').strip()
            if (kimlik and kimlik in gorulen_id) or sig in gorulen_imza:
                tekrar += 1
                continue
            if kimlik:
                gorulen_id.add(kimlik)
            gorulen_imza.add(sig)
            birlesik.append({'kaynak': kaynak, 'model': mac.get('model'), 'kayit': mac})

    simdi = datetime.now(LONDON)
    pazartesi = (simdi - timedelta(days=simdi.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    gelecek_pazartesi = pazartesi + timedelta(days=7)
    haftalik = []
    gunluk = []
    for satir in birlesik:
        mac = satir['kayit']
        dt = zaman(mac).astimezone(LONDON)
        if pazartesi <= dt < gelecek_pazartesi:
            haftalik.append(satir)
        if dt.date() == simdi.date():
            ev = mac.get('ev') or mac.get('ev_sahibi') or '?'
            dep = mac.get('dep') or mac.get('deplasman') or '?'
            gunluk.append((dt, f'{dt:%H:%M} | {ev} - {dep} | {karar_ver(mac)}'))

    gunluk.sort(key=lambda x: x[0])
    rapor = {
        'haftalik_toplam': len(haftalik),
        'haftalik_maclar': haftalik,
        'olusturulma_utc': datetime.now(timezone.utc).isoformat(),
        'v2_girdi': len(v2),
        'ek_lig_girdi': len(ek),
        'benzersiz_toplam': len(birlesik),
        'v2_kayit': sum(x['kaynak'] == 'V2' for x in birlesik),
        'ek_lig_kayit': sum(x['kaynak'] == 'EK_LIG' for x in birlesik),
        'tekrar_elenen': tekrar,
        'gecersiz_kayit': gecersiz,
        'not': 'Deneysel model ciktilaridir. Kilitleme veya basari dogrulamasi yapilmaz.',
        'maclar': birlesik,
    }
    atomik_yaz(CIKTI, json.dumps(rapor, ensure_ascii=False, indent=2) + '\n')
    atomik_yaz(GUNLUK, '\n'.join(s for _, s in gunluk) + ('\n' if gunluk else ''))
    print('TIPSTER PRO BIRLESIK RAPOR - KONTROL')
    print('V2:', len(v2), '| EK LIG:', len(ek))
    print('BENZERSIZ:', len(birlesik), '| TEKRAR:', tekrar, '| GECERSIZ:', gecersiz)
    print('HAFTALIK:', len(haftalik), '| GUNLUK:', len(gunluk))
    print('ARSIVLER VE ORIJINAL RAPORLAR DEGISTIRILMEDI')


if __name__ == '__main__':
    main()
