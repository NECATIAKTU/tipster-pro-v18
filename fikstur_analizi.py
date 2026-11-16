
import csv
import io
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from gol_modeli import verileri_al, mac_analizi

KAYNAK = "https://www.football-data.co.uk/fixtures.csv"
CIKTI = "fikstur_tahminleri.json"


def fiksturu_al():
    istek = Request(
        KAYNAK,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(istek, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig")

    maclar = []

    for mac in csv.DictReader(io.StringIO(metin)):
        # Sonucu olmayan, henuz oynanmamis maclar
        if (mac.get("FTHG") or "").strip():
            continue

        ev = (mac.get("HomeTeam") or "").strip()
        dep = (mac.get("AwayTeam") or "").strip()
        tarih = (mac.get("Date") or "").strip()

        if ev and dep and tarih:
            maclar.append({
                "tarih": tarih,
                "ev": ev,
                "dep": dep
            })

    return maclar


def calistir():
    takimlar = verileri_al()
    fikstur = fiksturu_al()
    sonuclar = []

    for mac in fikstur:
        try:
            analiz = mac_analizi(
                mac["ev"], mac["dep"], takimlar
            )
        except (ValueError, KeyError):
            continue

        sonuclar.append({
            **mac,
            **analiz,
            "hesaplama_zamani": datetime.now(
                timezone.utc
            ).isoformat()
        })

    with open(CIKTI, "w", encoding="utf-8") as dosya:
        json.dump(
            sonuclar,
            dosya,
            ensure_ascii=False,
            indent=2
        )

    print("TIPSTER PRO - FIKSTUR ANALIZI")
    print("Fiksturdeki mac:", len(fikstur))
    print("Analiz edilen mac:", len(sonuclar))

    for mac in sonuclar[:20]:
        print(
            mac["tarih"],
            mac["ev"], "-", mac["dep"],
            "| 1.5 UST:", mac["1.5_ust"],
            "| 2.5 UST:", mac["2.5_ust"],
            "| 3.5 UST:", mac["3.5_ust"]
        )


if __name__ == "__main__":
    calistir()
