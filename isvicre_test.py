
import csv
import io
from collections import defaultdict
from datetime import datetime, timezone
from urllib.request import Request, urlopen

URL = "https://www.football-data.co.uk/new/SWZ.csv"
SEZON = "2026/2027"


def isvicre_verisi_al():
    istek = Request(URL, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(istek, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig", errors="replace")

    takimlar = defaultdict(
        lambda: {"mac": 0, "attigi": 0, "yedigi": 0}
    )
    sayac = 0
    son_tarih = None
    bugun = datetime.now(timezone.utc).date()

    for satir in csv.DictReader(io.StringIO(metin)):
        if satir.get("Season", "").strip() != SEZON:
            continue

        if satir.get("League", "").strip() != "Super League":
            continue

        try:
            tarih = datetime.strptime(
                satir["Date"].strip(), "%d/%m/%Y"
            ).date()
            ev_gol = int(satir["HG"])
            dep_gol = int(satir["AG"])
        except (ValueError, KeyError, TypeError):
            continue

        if tarih > bugun:
            continue

        ev = satir.get("Home", "").strip()
        dep = satir.get("Away", "").strip()

        if not ev or not dep:
            continue

        takimlar[ev]["mac"] += 1
        takimlar[ev]["attigi"] += ev_gol
        takimlar[ev]["yedigi"] += dep_gol

        takimlar[dep]["mac"] += 1
        takimlar[dep]["attigi"] += dep_gol
        takimlar[dep]["yedigi"] += ev_gol

        sayac += 1
        if son_tarih is None or tarih > son_tarih:
            son_tarih = tarih

    return dict(takimlar), sayac, son_tarih


if __name__ == "__main__":
    takimlar, mac_sayisi, son_tarih = isvicre_verisi_al()

    print("TIPSTER PRO - ISVICRE TAKIM TESTI")
    print("SEZON:", SEZON)
    print("TAMAMLANMIS MAC:", mac_sayisi)
    print("TAKIM:", len(takimlar))
    print("SON MAC TARIHI:", son_tarih)
    print(
        "EN AZ 5 MAC OYNAYAN TAKIM:",
        sum(v["mac"] >= 5 for v in takimlar.values())
    )

    for ad, veri in sorted(takimlar.items()):
        print(ad, veri)
