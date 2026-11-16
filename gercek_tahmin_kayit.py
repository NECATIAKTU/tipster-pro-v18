
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

KAYIT_DOSYASI = Path("gercek_tahmin_arsivi.json")


def simdi():
    return datetime.now(timezone.utc).isoformat()


def arsivi_oku():
    if not KAYIT_DOSYASI.exists():
        return []

    veri = json.loads(KAYIT_DOSYASI.read_text(encoding="utf-8"))

    if not isinstance(veri, list):
        raise ValueError("Arsiv formati gecersiz")

    return veri


def tahmin_kaydet(mac, tahmin, kaynak="TIPSTER_PRO"):
    gerekli = ("tarih", "lig", "ev_sahibi", "deplasman")

    for alan in gerekli:
        if not mac.get(alan):
            raise ValueError(f"Eksik mac bilgisi: {alan}")

    if not isinstance(tahmin, dict) or not tahmin:
        raise ValueError("Tahmin verisi gecersiz")

    kimlik_verisi = {
        "tarih": mac["tarih"],
        "lig": mac["lig"],
        "ev_sahibi": mac["ev_sahibi"],
        "deplasman": mac["deplasman"],
        "kaynak": kaynak,
    }

    kimlik = hashlib.sha256(
        json.dumps(
            kimlik_verisi,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    arsiv = arsivi_oku()

    if any(kayit.get("id") == kimlik for kayit in arsiv):
        return "ZATEN_KAYITLI"

    yeni_kayit = {
        "id": kimlik,
        "kayit_zamani_utc": simdi(),
        "mac": dict(mac),
        "tahmin": dict(tahmin),
        "kaynak": kaynak,
        "durum": "KILITLI",
        "sonuc": None,
    }

    arsiv.append(yeni_kayit)

    gecici = KAYIT_DOSYASI.with_suffix(".tmp")
    gecici.write_text(
        json.dumps(arsiv, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    gecici.replace(KAYIT_DOSYASI)

    return "KAYDEDILDI"


if __name__ == "__main__":
    print("TIPSTER PRO - Gercek Tahmin Kayit Modulu")
    print("Modul hazir. Entegrasyon bekleniyor.")
