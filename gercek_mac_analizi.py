import csv
import io
import json
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen

from coklu_lig_motoru import tum_ligleri_al, mac_analizi

FIKSTUR_URL = "https://www.football-data.co.uk/fixtures.csv"
CIKTI = "gercek_mac_tahminleri.json"
LONDRA = ZoneInfo("Europe/London")


def fiksturu_al():
    istek = Request(FIKSTUR_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(istek, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(metin)))


def baslangici_oku(mac):
    tarih = (mac.get("Date") or "").strip()
    saat = (mac.get("Time") or "").strip()
    for bicim in ("%d/%m/%Y %H:%M", "%d/%m/%y %H:%M"):
        try:
            return datetime.strptime(f"{tarih} {saat}", bicim).replace(tzinfo=LONDRA)
        except ValueError:
            pass
    return None


def analiz_et():
    print("TIPSTER PRO - GERCEK MAC ANALIZI")
    print("Fikstur kaynagi:", FIKSTUR_URL)

    lig_verileri = tum_ligleri_al()
    fikstur = fiksturu_al()
    tahminler = []
    nedenler = Counter()
    simdi_utc = datetime.now(timezone.utc)
    tarihler = []

    for mac in fikstur:
        kod = (mac.get("Div") or "").strip()
        ev = (mac.get("HomeTeam") or "").strip()
        dep = (mac.get("AwayTeam") or "").strip()
        tarih = (mac.get("Date") or "").strip()
        baslangic = baslangici_oku(mac)

        if baslangic is None:
            nedenler["gecersiz_tarih_saat"] += 1
            continue
        tarihler.append(baslangic.date())

        if not kod or not ev or not dep or not tarih:
            nedenler["eksik_bilgi"] += 1
            continue
        if (mac.get("FTHG") or "").strip():
            nedenler["tamamlanmis"] += 1
            continue
        if baslangic.astimezone(timezone.utc) <= simdi_utc:
            nedenler["baslamis_mac"] += 1
            continue
        if kod not in lig_verileri:
            nedenler["desteklenmeyen_lig"] += 1
            continue

        try:
            sonuc = mac_analizi(kod, ev, dep, lig_verileri)
        except ValueError as hata:
            nedenler[f"analiz_hatasi: {hata}"] += 1
            continue

        tahminler.append({
            "tarih": tarih,
            "lig": kod,
            "ev": ev,
            "dep": dep,
            "model": "TIPSTER_PRO_COKLU_V1",
            "hesaplama_zamani_utc": simdi_utc.isoformat(),
            "mac_baslangic_utc": baslangic.astimezone(timezone.utc).isoformat(),
            "beklenen_gol": sonuc["beklenen_gol"],
            "1.5_ust": sonuc["1.5_ust"],
            "2.5_ust": sonuc["2.5_ust"],
            "3.5_ust": sonuc["3.5_ust"],
        })

    # Dosya her calismada yalnizca guncel, baslamamis maclari icerir.
    # Kalici arsiv ayri dosyadadir ve burada degistirilmez.
    with open(CIKTI + ".tmp", "w", encoding="utf-8") as dosya:
        json.dump(tahminler, dosya, ensure_ascii=False, indent=2)
    import os
    os.replace(CIKTI + ".tmp", CIKTI)

    print("Fiksturdeki toplam mac:", len(fikstur))
    print("Analiz edilen mac:", len(tahminler))
    print("Analiz edilemeyenler:", dict(nedenler))
    if tarihler:
        print("Kaynaktaki ilk mac tarihi:", min(tarihler).isoformat())
        print("Kaynaktaki son mac tarihi:", max(tarihler).isoformat())
    else:
        print("UYARI: Kaynaktan gecerli tarihli mac okunamadi.")
    if tahminler:
        print("Tahminlerdeki son mac tarihi:", max(
            mac["mac_baslangic_utc"] for mac in tahminler
        ))
    else:
        print("UYARI: Yeni analiz edilebilir mac yok.")

    for mac in tahminler:
        print(
            mac["tarih"], mac["lig"], mac["ev"], "-", mac["dep"],
            "| 1.5 UST:", mac["1.5_ust"],
            "| 2.5 UST:", mac["2.5_ust"],
            "| 3.5 UST:", mac["3.5_ust"],
        )


if __name__ == "__main__":
    analiz_et()
