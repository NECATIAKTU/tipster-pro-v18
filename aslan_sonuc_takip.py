
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ASLAN MODU V1 - BAGIMSIZ SONUC TAKIP SISTEMI

V18 motorunu veya arsivini degistirmez.

Kullanim:
  python aslan_sonuc_takip.py --kilitle
  python aslan_sonuc_takip.py --kontrol

Girdi:
  aslan_modu_rapor.json
  v18_dogrulanan_sonuclar.json

Cikti:
  aslan_tahmin_arsivi.json
  aslan_dogrulanan_sonuclar.json
"""

import argparse
import json
import math
import os
import re

from datetime import datetime, timezone
from pathlib import Path


RAPOR = Path("aslan_modu_rapor.json")
V18_SONUCLAR = Path("v18_dogrulanan_sonuclar.json")

ARSIV = Path("aslan_tahmin_arsivi.json")
SONUCLAR = Path("aslan_dogrulanan_sonuclar.json")

CIZGILER = (
    "1.5", "2.5", "3.5",
    "4.5", "5.5", "6.5"
)


def simdi():
    return datetime.now(timezone.utc)


def tarih_oku(value):
    if not isinstance(value, str):
        return None

    try:
        value = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            return None

        return dt.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None


def oku(path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def yaz(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(path.name + ".tmp")

    try:
        temporary.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ) + "\n",
            encoding="utf-8"
        )

        os.replace(temporary, path)

    finally:
        if temporary.exists():
            temporary.unlink()


def model_yuzdesi(value):
    if isinstance(value, bool):
        return None

    try:
        result = float(value)
    except (ValueError, TypeError):
        return None

    if not math.isfinite(result):
        return None

    if not 0 <= result <= 100:
        return None

    return result


def guven_sinifi(yuzde):
    if yuzde >= 80:
        return "YESIL"

    if yuzde >= 70:
        return "SARI"

    return "NORMAL"


def secim_oku(match):
    analiz = match.get("analiz")

    if not isinstance(analiz, dict):
        return None

    if analiz.get("durum") != "KESIF_ADAYI":
        return None

    secim = analiz.get("en_yuksek_uygun_cizgi")

    if not isinstance(secim, dict):
        return None

    cizgi = str(secim.get("cizgi") or "").upper()

    eslesme = re.fullmatch(
        r"(1\.5|2\.5|3\.5|4\.5|5\.5|6\.5)\s+UST",
        cizgi.strip()
    )

    if not eslesme:
        return None

    yuzde = model_yuzdesi(
        secim.get("model_yuzdesi")
    )

    if yuzde is None or yuzde < 50:
        return None

    return {
        "gol_cizgisi": eslesme.group(1),
        "tahmin": eslesme.group(1) + " UST",
        "model_yuzdesi": yuzde,
        "guven_sinifi": guven_sinifi(yuzde)
    }


def kilitle():
    now = simdi()

    rapor = oku(RAPOR, {})

    if not isinstance(rapor, dict):
        raise ValueError("ASLAN raporu gecersiz")

    maclar = rapor.get("maclar")

    if not isinstance(maclar, list):
        raise ValueError("ASLAN mac listesi bulunamadi")

    rapor_zamani = tarih_oku(
        rapor.get("olusturulma_utc")
    )

    if rapor_zamani is None or rapor_zamani > now:
        raise ValueError(
            "ASLAN raporunun olusturulma zamani gecersiz"
        )

    arsiv = oku(ARSIV, [])

    if not isinstance(arsiv, list):
        raise ValueError("ASLAN arsivi liste olmali")

    mevcut = {
        str(x.get("id"))
        for x in arsiv
        if isinstance(x, dict) and x.get("id")
    }

    yeni = 0
    atlanan = 0

    for mac in maclar:
        if not isinstance(mac, dict):
            atlanan += 1
            continue

        mac_id = str(mac.get("id") or "").strip()

        if not mac_id or mac_id in mevcut:
            atlanan += 1
            continue

        baslangic = tarih_oku(mac.get("tarih"))

        # Mac baslamadan once uretilen raporlar
        # ve mac baslamadan once kilitlenen
        # secimler kabul edilir.
        if (
            baslangic is None
            or rapor_zamani >= baslangic
            or now >= baslangic
        ):
            atlanan += 1
            continue

        secim = secim_oku(mac)

        if secim is None:
            atlanan += 1
            continue

        kayit = {
            "id": mac_id,
            "tarih": mac.get("tarih"),
            "lig": mac.get("lig"),
            "ev_sahibi": mac.get("ev_sahibi"),
            "deplasman": mac.get("deplasman"),

            "tahmin": secim["tahmin"],
            "gol_cizgisi": secim["gol_cizgisi"],

            "model_yuzdesi": secim["model_yuzdesi"],
            "guven_sinifi": secim["guven_sinifi"],

            "rapor_zamani_utc": rapor_zamani.isoformat(),
            "kilit_zamani_utc": now.isoformat(),

            "durum": "BEKLIYOR",
            "skor": None,
            "toplam_gol": None,
            "tahmin_sonucu": None
        }

        arsiv.append(kayit)
        mevcut.add(mac_id)
        yeni += 1

    if yeni:
        yaz(ARSIV, arsiv)

    print("ASLAN KILITLEME TAMAMLANDI")
    print("Yeni:", yeni)
    print("Atlanan:", atlanan)
    print("Toplam arsiv:", len(arsiv))

    return arsiv


def v18_skor_haritasi():
    veri = oku(V18_SONUCLAR, {})

    if not isinstance(veri, dict):
        raise ValueError("V18 sonuc raporu gecersiz")

    kayitlar = veri.get("kayitlar", [])

    if not isinstance(kayitlar, list):
        raise ValueError("V18 sonuc kayitlari gecersiz")

    harita = {}

    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            continue

        if kayit.get("durum") != "DOGRULANDI":
            continue

        mac = kayit.get("mac") or {}
        sonuc = kayit.get("sonuc") or {}

        if not isinstance(mac, dict):
            continue

        if not isinstance(sonuc, dict):
            continue

        mac_id = str(
            mac.get("id") or kayit.get("kimlik") or ""
        ).strip()

        if not mac_id:
            continue

        if sonuc.get("kaynak") != "ESPN":
            continue

        if sonuc.get("durum") != "TAMAMLANDI":
            continue

        ev = sonuc.get("ev_gol")
        dep = sonuc.get("dep_gol")

        if type(ev) is not int or type(dep) is not int:
            continue

        if ev < 0 or dep < 0:
            continue

        harita[mac_id] = {
            "skor": str(ev) + "-" + str(dep),
            "toplam_gol": ev + dep,
            "kaynak": "ESPN"
        }

    return harita


def kontrol():
    arsiv = oku(ARSIV, [])

    if not isinstance(arsiv, list):
        raise ValueError("ASLAN arsivi gecersiz")

    skorlar = v18_skor_haritasi()

    now = simdi()

    dogru = 0
    yanlis = 0
    bekleyen = 0

    guven_raporu = {
        "YESIL": {"dogru": 0, "yanlis": 0},
        "SARI": {"dogru": 0, "yanlis": 0},
        "NORMAL": {"dogru": 0, "yanlis": 0}
    }

    for kayit in arsiv:
        if not isinstance(kayit, dict):
            raise ValueError("Gecersiz ASLAN arsiv kaydi")

        mac_id = str(kayit.get("id") or "").strip()
        baslangic = tarih_oku(kayit.get("tarih"))

        rapor_zamani = tarih_oku(
            kayit.get("rapor_zamani_utc")
        )

        kilit_zamani = tarih_oku(
            kayit.get("kilit_zamani_utc")
        )

        # Sonradan tahmin eklenmesini engelle.
        if not (
            baslangic
            and rapor_zamani
            and kilit_zamani
            and rapor_zamani < baslangic
            and kilit_zamani < baslangic
        ):
            kayit["durum"] = "INCELEME"
            kayit["tahmin_sonucu"] = None
            continue

        skor = skorlar.get(mac_id)

        if skor is None:
            if kayit.get("durum") != "DOGRULANDI":
                kayit["durum"] = "BEKLIYOR"
                kayit["tahmin_sonucu"] = None
                bekleyen += 1
                continue

            # Onceden dogrulanmis sonucu
            # gecici API eksikligi yuzunden silme.
            if (
                kayit.get("tahmin_sonucu")
                in ("DOGRU", "YANLIS")
                and type(kayit.get("toplam_gol")) is int
            ):
                skor = {
                    "skor": kayit.get("skor"),
                    "toplam_gol": kayit["toplam_gol"]
                }
            else:
                kayit["durum"] = "BEKLIYOR"
                kayit["tahmin_sonucu"] = None
                bekleyen += 1
                continue

        try:
            cizgi = float(kayit["gol_cizgisi"])
        except (ValueError, TypeError, KeyError):
            kayit["durum"] = "INCELEME"
            kayit["tahmin_sonucu"] = None
            continue

        if str(kayit.get("gol_cizgisi")) not in CIZGILER:
            kayit["durum"] = "INCELEME"
            kayit["tahmin_sonucu"] = None
            continue

        toplam = skor["toplam_gol"]

        sonuc = "DOGRU" if toplam > cizgi else "YANLIS"

        # Onceki dogrulama varsa celiskiyi
        # sessizce degistirme.
        eski = kayit.get("tahmin_sonucu")

        if eski in ("DOGRU", "YANLIS") and eski != sonuc:
            kayit["skor_uyarisi"] = (
                "ONCEKI_SONUC_ILE_CELISKI"
            )
            sonuc = eski

        kayit["durum"] = "DOGRULANDI"
        kayit["tahmin_sonucu"] = sonuc

        if eski not in ("DOGRU", "YANLIS"):
            kayit["skor"] = skor["skor"]
            kayit["toplam_gol"] = toplam
            kayit["dogrulama_zamani_utc"] = now.isoformat()

        sinif = kayit.get("guven_sinifi")

        if sonuc == "DOGRU":
            dogru += 1
        else:
            yanlis += 1

        if sinif in guven_raporu:
            guven_raporu[sinif][
                "dogru" if sonuc == "DOGRU" else "yanlis"
            ] += 1

    toplam = dogru + yanlis

    for sinif, sayilar in guven_raporu.items():
        adet = sayilar["dogru"] + sayilar["yanlis"]

        sayilar["degerlendirilen"] = adet
        sayilar["basari_yuzdesi"] = (
            round(100 * sayilar["dogru"] / adet, 2)
            if adet else None
        )

    rapor = {
        "modul": "ASLAN MODU V1 SONUC TAKIP",
        "olusturulma_utc": now.isoformat(),

        "toplam_kilitli_tahmin": len(arsiv),
        "degerlendirilen": toplam,

        "dogru": dogru,
        "yanlis": yanlis,
        "bekleyen": bekleyen,

        "basari_yuzdesi": (
            round(100 * dogru / toplam, 2)
            if toplam else None
        ),

        "guven_siniflari": guven_raporu,

        "not": (
            "Yalnizca mac baslamadan once "
            "kilitlenmis ASLAN secimleri "
            "basari hesabina girer. "
            "Model yuzdeleri gercek basari "
            "oranlari degildir."
        ),

        "kayitlar": arsiv
    }

    yaz(ARSIV, arsiv)
    yaz(SONUCLAR, rapor)

    print("ASLAN SONUC RAPORU")
    print("Toplam:", len(arsiv))
    print("Dogru:", dogru)
    print("Yanlis:", yanlis)
    print("Bekleyen:", bekleyen)
    print("Basari:", rapor["basari_yuzdesi"])

    return rapor


def main():
    parser = argparse.ArgumentParser(
        description="ASLAN MODU bagimsiz sonuc takibi"
    )

    parser.add_argument(
        "--kilitle",
        action="store_true"
    )

    parser.add_argument(
        "--kontrol",
        action="store_true"
    )

    args = parser.parse_args()

    if not args.kilitle and not args.kontrol:
        parser.print_help()
        return

    if args.kilitle:
        kilitle()

    if args.kontrol:
        kontrol()


if __name__ == "__main__":
    main()
