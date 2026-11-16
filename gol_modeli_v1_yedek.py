
import csv
import io
import math
from collections import defaultdict
from urllib.request import Request, urlopen

KAYNAK = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"

def verileri_al():
    istek = Request(
        KAYNAK,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(istek, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig")

    takimlar = defaultdict(
        lambda: {"mac": 0, "attigi": 0, "yedigi": 0}
    )

    for mac in csv.DictReader(io.StringIO(metin)):
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

    return takimlar

def poisson_ust(lam, gol_siniri):
    alt_olasilik = sum(
        math.exp(-lam) * lam**k / math.factorial(k)
        for k in range(gol_siniri + 1)
    )
    return max(0.0, min(1.0, 1.0 - alt_olasilik))

def mac_analizi(ev, dep, takimlar):
    a = takimlar[ev]
    b = takimlar[dep]

    if min(a["mac"], b["mac"]) < 5:
        raise ValueError("Yetersiz maç verisi")

    ev_atak = a["attigi"] / a["mac"]
    ev_savunma = a["yedigi"] / a["mac"]

    dep_atak = b["attigi"] / b["mac"]
    dep_savunma = b["yedigi"] / b["mac"]

    beklenen_ev = (ev_atak + dep_savunma) / 2
    beklenen_dep = (dep_atak + ev_savunma) / 2

    toplam = beklenen_ev + beklenen_dep

    return {
        "beklenen_gol": round(toplam, 2),
        "1.5_ust": round(poisson_ust(toplam, 1) * 100, 1),
        "2.5_ust": round(poisson_ust(toplam, 2) * 100, 1),
        "3.5_ust": round(poisson_ust(toplam, 3) * 100, 1),
    }

if __name__ == "__main__":
    takimlar = verileri_al()

    print("TIPSTER PRO - GOL OLASILIK MODELI")
    print("Takim sayisi:", len(takimlar))

    isimler = sorted(
        isim for isim, veri in takimlar.items()
        if veri["mac"] >= 5
    )

    if len(isimler) < 2:
        print("Yeterli veri bulunamadi.")
    else:
        ev, dep = isimler[:2]
        sonuc = mac_analizi(ev, dep, takimlar)

        print("ORNEK HESAPLAMA:", ev, "-", dep)
        for alan, deger in sonuc.items():
            print(alan, ":", deger)
