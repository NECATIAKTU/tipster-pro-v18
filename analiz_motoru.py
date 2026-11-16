
import csv
import io
from collections import defaultdict
from urllib.request import Request, urlopen

KAYNAK = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"


def takim_istatistikleri():
    istek = Request(
        KAYNAK,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(istek, timeout=30) as cevap:
        veri = cevap.read().decode("utf-8-sig")

    maclar = csv.DictReader(io.StringIO(veri))
    takimlar = defaultdict(
        lambda: {"mac": 0, "attigi": 0, "yedigi": 0}
    )

    for mac in maclar:
        try:
            ev = mac["HomeTeam"]
            dep = mac["AwayTeam"]
            ev_gol = int(mac["FTHG"])
            dep_gol = int(mac["FTAG"])
        except (KeyError, ValueError, TypeError):
            continue

        takimlar[ev]["mac"] += 1
        takimlar[ev]["attigi"] += ev_gol
        takimlar[ev]["yedigi"] += dep_gol

        takimlar[dep]["mac"] += 1
        takimlar[dep]["attigi"] += dep_gol
        takimlar[dep]["yedigi"] += ev_gol

    print("TIPSTER PRO - TAKIM ANALIZI")

    for isim, veri in sorted(takimlar.items()):
        sayi = veri["mac"]
        if sayi == 0:
            continue

        print(
            isim,
            "| Mac:", sayi,
            "| Gol ort:", round(veri["attigi"] / sayi, 2),
            "| Yedigi ort:", round(veri["yedigi"] / sayi, 2)
        )


if __name__ == "__main__":
    takim_istatistikleri()
