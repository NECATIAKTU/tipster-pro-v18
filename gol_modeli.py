
import csv
import io
import math
from collections import defaultdict
from datetime import datetime
from urllib.request import Request, urlopen

KAYNAK = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"


def bos_takim():
    return {
        "mac": 0,
        "attigi": 0,
        "yedigi": 0,
        "ev_mac": 0,
        "ev_attigi": 0,
        "ev_yedigi": 0,
        "dep_mac": 0,
        "dep_attigi": 0,
        "dep_yedigi": 0,
        "son_maclar": [],
    }


def verileri_al():
    istek = Request(
        KAYNAK,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(istek, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig")

    takimlar = defaultdict(bos_takim)
    maclar = []

    for sira, mac in enumerate(
        csv.DictReader(io.StringIO(metin))
    ):
        try:
            ev = mac["HomeTeam"].strip()
            dep = mac["AwayTeam"].strip()
            ev_gol = int(mac["FTHG"])
            dep_gol = int(mac["FTAG"])

            if not ev or not dep:
                continue
            if ev_gol < 0 or dep_gol < 0:
                continue

            tarih = datetime.strptime(
                mac["Date"].strip(), "%d/%m/%Y"
            )
        except (KeyError, ValueError, TypeError):
            continue

        maclar.append(
            (tarih, sira, ev, dep, ev_gol, dep_gol)
        )

    maclar.sort(key=lambda x: (x[0], x[1]))

    for _, _, ev, dep, ev_gol, dep_gol in maclar:
        a = takimlar[ev]
        b = takimlar[dep]

        a["mac"] += 1
        a["attigi"] += ev_gol
        a["yedigi"] += dep_gol
        a["ev_mac"] += 1
        a["ev_attigi"] += ev_gol
        a["ev_yedigi"] += dep_gol
        a["son_maclar"].append((ev_gol, dep_gol))

        b["mac"] += 1
        b["attigi"] += dep_gol
        b["yedigi"] += ev_gol
        b["dep_mac"] += 1
        b["dep_attigi"] += dep_gol
        b["dep_yedigi"] += ev_gol
        b["son_maclar"].append((dep_gol, ev_gol))

    return takimlar


def poisson_ust(lam, gol_siniri):
    if not math.isfinite(lam) or lam < 0:
        raise ValueError("Gecersiz beklenen gol")

    alt = sum(
        math.exp(-lam) * lam**k / math.factorial(k)
        for k in range(gol_siniri + 1)
    )
    return max(0.0, min(1.0, 1.0 - alt))


def ortalama(toplam, adet, yedek):
    return toplam / adet if adet >= 3 else yedek


def form_ortalamasi(maclar, alan):
    son = maclar[-5:]
    if len(son) < 3:
        return None

    agirliklar = range(1, len(son) + 1)
    return sum(
        mac[alan] * agirlik
        for mac, agirlik in zip(son, agirliklar)
    ) / sum(range(1, len(son) + 1))


def mac_analizi(ev, dep, takimlar):
    a = takimlar[ev]
    b = takimlar[dep]

    if min(a["mac"], b["mac"]) < 5:
        raise ValueError("Yetersiz mac verisi")

    ev_atak_genel = a["attigi"] / a["mac"]
    ev_savunma_genel = a["yedigi"] / a["mac"]
    dep_atak_genel = b["attigi"] / b["mac"]
    dep_savunma_genel = b["yedigi"] / b["mac"]

    ev_atak = ortalama(
        a.get("ev_attigi", 0),
        a.get("ev_mac", 0),
        ev_atak_genel
    )
    ev_savunma = ortalama(
        a.get("ev_yedigi", 0),
        a.get("ev_mac", 0),
        ev_savunma_genel
    )
    dep_atak = ortalama(
        b.get("dep_attigi", 0),
        b.get("dep_mac", 0),
        dep_atak_genel
    )
    dep_savunma = ortalama(
        b.get("dep_yedigi", 0),
        b.get("dep_mac", 0),
        dep_savunma_genel
    )

    beklenen_ev = (ev_atak + dep_savunma) / 2
    beklenen_dep = (dep_atak + ev_savunma) / 2

    a_form = a.get("son_maclar", [])
    b_form = b.get("son_maclar", [])

    if len(a_form) >= 3 and len(b_form) >= 3:
        form_ev_atak = form_ortalamasi(a_form, 0)
        form_ev_yedigi = form_ortalamasi(a_form, 1)
        form_dep_atak = form_ortalamasi(b_form, 0)
        form_dep_yedigi = form_ortalamasi(b_form, 1)

        form_ev = (
            form_ev_atak + form_dep_yedigi
        ) / 2
        form_dep = (
            form_dep_atak + form_ev_yedigi
        ) / 2

        beklenen_ev = (
            0.75 * beklenen_ev + 0.25 * form_ev
        )
        beklenen_dep = (
            0.75 * beklenen_dep + 0.25 * form_dep
        )

    toplam = max(0.0, beklenen_ev + beklenen_dep)

    return {
        "beklenen_gol": round(toplam, 2),
        "1.5_ust": round(poisson_ust(toplam, 1) * 100, 1),
        "2.5_ust": round(poisson_ust(toplam, 2) * 100, 1),
        "3.5_ust": round(poisson_ust(toplam, 3) * 100, 1),
        "4.5_ust": round(poisson_ust(toplam, 4) * 100, 1),
        "5.5_ust": round(poisson_ust(toplam, 5) * 100, 1),
        "6.5_ust": round(poisson_ust(toplam, 6) * 100, 1),
    }


if __name__ == "__main__":
    takimlar = verileri_al()

    print("TIPSTER PRO - GOL MODELI V2.1")
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

