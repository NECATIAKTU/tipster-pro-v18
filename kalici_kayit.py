import json
import os
from datetime import datetime, timezone

KAYNAK = "gercek_mac_tahminleri.json"
ARSIV = "tahmin_arsivi.json"


def oku(dosya, varsayilan):
    if not os.path.exists(dosya):
        return varsayilan
    with open(dosya, "r", encoding="utf-8") as f:
        return json.load(f)


def zaman_coz(deger):
    if not isinstance(deger, str) or not deger.strip():
        return None
    try:
        zaman = datetime.fromisoformat(deger.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if zaman.tzinfo is None or zaman.utcoffset() is None:
        return None
    return zaman.astimezone(timezone.utc)


def kimlik_al(kayit):
    return tuple(kayit[alan] for alan in ("tarih", "lig", "ev", "dep", "model"))


def kaydet():
    tahminler = oku(KAYNAK, [])
    arsiv = oku(ARSIV, [])

    if not isinstance(tahminler, list):
        raise ValueError("Tahmin dosyasi liste olmali")
    if not isinstance(arsiv, list):
        raise ValueError("Arsiv dosyasi liste olmali")

    mevcut = {kimlik_al(kayit) for kayit in arsiv}
    eklenen = 0
    zaten_var = 0
    eksik_zaman = 0
    gec_tahmin = 0
    simdi = datetime.now(timezone.utc)

    for tahmin in tahminler:
        kimlik = kimlik_al(tahmin)
        if kimlik in mevcut:
            zaten_var += 1
            continue

        hesaplama = zaman_coz(tahmin.get("hesaplama_zamani_utc"))
        baslangic = zaman_coz(tahmin.get("mac_baslangic_utc"))
        if hesaplama is None or baslangic is None:
            eksik_zaman += 1
            print(f"UYARI: Gecerli UTC zaman bilgisi eksik: {tahmin.get('ev')} - {tahmin.get('dep')}")
            continue
        if hesaplama >= baslangic or simdi >= baslangic:
            gec_tahmin += 1
            print(f"UYARI: Mac baslamis veya tahmin gec hesaplanmis: {tahmin.get('ev')} - {tahmin.get('dep')}")
            continue

        yeni = dict(tahmin)
        yeni["kayit_zamani_utc"] = datetime.now(timezone.utc).isoformat()
        yeni["kayit_tipi"] = "ILK_TAHMIN"
        arsiv.append(yeni)
        mevcut.add(kimlik)
        eklenen += 1

    if eklenen:
        gecici = ARSIV + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(arsiv, f, ensure_ascii=False, indent=2)
        os.replace(gecici, ARSIV)

    print("TIPSTER PRO - KALICI KAYIT")
    print("Kaynak tahmin:", len(tahminler))
    print("Zaten arsivde:", zaten_var)
    print("Gecersiz/eksik zaman:", eksik_zaman)
    print("Baslamis mac/gec tahmin:", gec_tahmin)
    print("Yeni kayit:", eklenen)
    print("Toplam arsiv:", len(arsiv))


if __name__ == "__main__":
    kaydet()
