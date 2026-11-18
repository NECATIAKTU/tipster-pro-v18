
#!/usr/bin/env python3
"""TIPSTER PRO V18 - Tahmin arsivi ve ESPN sonuc takibi."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from gercek_tahmin_v18 import get_json

ARSIV = Path("v18_tahmin_arsivi.json")
SONUCLAR = Path("v18_dogrulanan_sonuclar.json")
CIZGILER = ("1.5", "2.5", "3.5", "4.5", "5.5", "6.5")


def utc(deger):
    if not isinstance(deger, str):
        return None
    try:
        dt = datetime.fromisoformat(
            deger.replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def oku(dosya, varsayilan):
    if not dosya.exists():
        return varsayilan
    return json.loads(dosya.read_text(encoding="utf-8"))


def yaz(dosya, veri):
    gecici = dosya.with_suffix(dosya.suffix + ".tmp")
    gecici.write_text(
        json.dumps(veri, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    os.replace(gecici, dosya)


def kimlik(mac):
    lig = str(mac.get("lig_kodu", "")).strip()
    mid = mac.get("id")
    if not lig or mid is None or str(mid).strip() == "":
        return None
    mid = str(mid)
if mid.startswith(lig + "|"):
    return mid
return lig + "|" + mid


def olasiliklar(mac):
    tahmin = mac.get("tahmin")
    if not isinstance(tahmin, dict):
        return {}

    kaynaklar = [tahmin]
    ic = tahmin.get("olasiliklar")
    if isinstance(ic, dict):
        kaynaklar.insert(0, ic)

    sonuc = {}
    for cizgi in CIZGILER:
        alan = cizgi + "_ust"
        for kaynak in kaynaklar:
            deger = kaynak.get(alan)
            try:
                if deger is not None:
                    sayi = float(str(deger).replace("%", ""))
                    if 0 <= sayi <= 100:
                        sonuc[alan] = sayi
                        break
            except (TypeError, ValueError):
                pass
    return sonuc


def arsivle(kaynak):
    veri = oku(Path(kaynak), {})
    if (
        not isinstance(veri, dict)
        or veri.get("model") != "TIPSTER PRO V18"
        or not isinstance(veri.get("tahminler"), list)
    ):
        raise ValueError("Gecersiz V18 tahmin dosyasi")

    arsiv = oku(ARSIV, [])
    if not isinstance(arsiv, list):
        raise ValueError("Arsiv liste olmali")

    mevcut = {
        x.get("kimlik") for x in arsiv
        if isinstance(x, dict)
    }
    simdi = datetime.now(timezone.utc)
    eklenen = 0
    atlanan = 0

    for mac in veri["tahminler"]:
        if not isinstance(mac, dict):
            atlanan += 1
            continue

        mid = kimlik(mac)
        baslangic = utc(mac.get("tarih"))
        hesaplama = utc(mac.get("hesaplama_zamani_utc"))

        if (
            not mid
            or mid in mevcut
            or baslangic is None
            or hesaplama is None
            or not (hesaplama < baslangic and simdi < baslangic)
        ):
            atlanan += 1
            continue

        yeni = {
            "kimlik": mid,
            "mac": dict(mac),
            "kilit_zamani_utc": simdi.isoformat(),
            "durum": "BEKLIYOR",
            "sonuc": None,
            "olasiliklar": olasiliklar(mac)
        }

        arsiv.append(yeni)
        mevcut.add(mid)
        eklenen += 1

    if eklenen:
        yaz(ARSIV, arsiv)

    print("ARSIV TOPLAM:", len(arsiv))
    print("YENI KAYIT:", eklenen)
    print("ATLANAN:", atlanan)


def espn_sonuclari(arsiv):
    gunler = set()

    for kayit in arsiv:
        if not isinstance(kayit, dict):
            continue
        mac = kayit.get("mac", {})
        if not isinstance(mac, dict):
            continue
        tarih = utc(mac.get("tarih"))
        lig = mac.get("lig_kodu")
        if tarih and lig:
            gunler.add((str(lig), tarih.date()))

    sonuclar = {}
    for lig, gun in sorted(gunler):
        try:
            veri = get_json(lig, gun)
            for event in veri.get("events", []):
                if not event.get("status", {}).get(
                    "type", {}
                ).get("completed"):
                    continue

                comps = event["competitions"][0]["competitors"]
                ev = next(
                    c for c in comps if c["homeAway"] == "home"
                )
                dep = next(
                    c for c in comps if c["homeAway"] == "away"
                )
                ev_gol = int(ev["score"])
                dep_gol = int(dep["score"])

                if ev_gol < 0 or dep_gol < 0:
                    continue

                event_id = str(event["id"])
mid = event_id if event_id.startswith(str(lig) + "|") else str(lig) + "|" + event_id
                sonuclar[mid] = {
                    "ev_gol": ev_gol,
                    "dep_gol": dep_gol,
                    "toplam_gol": ev_gol + dep_gol,
                    "skor": f"{ev_gol}-{dep_gol}",
                    "durum": "TAMAMLANDI"
                }

        except (OSError, ValueError, KeyError, TypeError,
                IndexError, StopIteration) as hata:
            print("SONUC ALINAMADI:", lig, gun, hata)

    return sonuclar


def kontrol():
    arsiv = oku(ARSIV, [])
    if not isinstance(arsiv, list):
        raise ValueError("Arsiv liste olmali")

    bulunan = espn_sonuclari(arsiv)
    rapor = []
    dogru = 0
    yanlis = 0

    for kayit in arsiv:
        yeni = dict(kayit)
        mid = yeni.get("kimlik")
        sonuc = bulunan.get(mid)

        if sonuc is None:
            yeni["durum"] = "BEKLIYOR"
            yeni["sonuc"] = None
            rapor.append(yeni)
            continue

        yeni["durum"] = "DOGRULANDI"
        yeni["sonuc"] = sonuc

        kararlar = {}
        for cizgi in CIZGILER:
            alan = cizgi + "_ust"
            yuzde = yeni.get("olasiliklar", {}).get(alan)

            if yuzde is None:
                continue

            gerceklesti = (
                sonuc["toplam_gol"] > float(cizgi)
            )

            # Bunlar gol cizgisi gerceklesme bilgileridir.
            # Tahminin resmi DOGRU/YANLIS karari degildir.
            kararlar[alan] = {
                "model_yuzdesi": yuzde,
                "gerceklesti": gerceklesti
            }

        yeni["cizgi_sonuclari"] = kararlar

        # Kilitli secim yoksa basari sayacina dahil etme.
        secim = yeni.get("kilitli_secim")
        if isinstance(secim, str):
            secim = secim.replace(",", ".").upper().strip()
            for cizgi in CIZGILER:
                if secim == cizgi + " UST":
                    gercek = sonuc["toplam_gol"] > float(cizgi)
                    yeni["tahmin_sonucu"] = (
                        "DOGRU" if gercek else "YANLIS"
                    )
                    if gercek:
                        dogru += 1
                    else:
                        yanlis += 1
                    break

        rapor.append(yeni)

    yaz(SONUCLAR, {
        "model": "TIPSTER PRO V18",
        "olusturulma_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "toplam_arsiv": len(arsiv),
        "dogru": dogru,
        "yanlis": yanlis,
        "basari_yuzdesi": (
            round(dogru / (dogru + yanlis) * 100, 2)
            if dogru + yanlis else None
        ),
        "kayitlar": rapor
    })

    print("DOGRULANAN:", sum(
        x["durum"] == "DOGRULANDI" for x in rapor
    ))
    print("DOGRU:", dogru)
    print("YANLIS:", yanlis)
    print("SONUC DOSYASI:", SONUCLAR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--arsivle",
        metavar="V18_JSON",
        help="Mac oncesi V18 tahminlerini arsivle"
    )
    parser.add_argument(
        "--kontrol",
        action="store_true",
        help="ESPN kesin skorlarini kontrol et"
    )
    args = parser.parse_args()

    if args.arsivle:
        arsivle(args.arsivle)
    if args.kontrol:
        kontrol()
    if not args.arsivle and not args.kontrol:
        parser.print_help()


if __name__ == "__main__":
    main()
