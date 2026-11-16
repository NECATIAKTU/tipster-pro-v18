
import csv
import io
from collections import defaultdict
from datetime import datetime
from urllib.request import Request, urlopen

from gol_modeli import bos_takim
from gol_modeli import mac_analizi as v2
from gol_modeli_v3 import mac_analizi as v3

SEZON = "2627"
LIGLER = ["E0", "E1", "E2", "E3"]
ESIKLER = {"2.5_ust": 73, "3.5_ust": 65}


def maclari_al(lig):
    url = f"https://www.football-data.co.uk/mmz4281/{SEZON}/{lig}.csv"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig")

    maclar = []
    for sira, satir in enumerate(csv.DictReader(io.StringIO(metin))):
        try:
            tarih = datetime.strptime(satir["Date"].strip(), "%d/%m/%Y")
            ev = satir["HomeTeam"].strip()
            dep = satir["AwayTeam"].strip()
            eg = int(satir["FTHG"])
            dg = int(satir["FTAG"])
            if ev and dep and min(eg, dg) >= 0:
                maclar.append((tarih, sira, ev, dep, eg, dg))
        except (ValueError, KeyError, TypeError, AttributeError):
            continue

    return sorted(maclar)


def istatistik_ekle(takimlar, ev, dep, eg, dg):
    a, b = takimlar[ev], takimlar[dep]

    a["mac"] += 1
    a["attigi"] += eg
    a["yedigi"] += dg
    a["ev_mac"] += 1
    a["ev_attigi"] += eg
    a["ev_yedigi"] += dg
    a["son_maclar"].append((eg, dg))

    b["mac"] += 1
    b["attigi"] += dg
    b["yedigi"] += eg
    b["dep_mac"] += 1
    b["dep_attigi"] += dg
    b["dep_yedigi"] += eg
    b["son_maclar"].append((dg, eg))


def secim(sonuc):
    uygun = [
        k for k, esik in ESIKLER.items()
        if sonuc[k] >= esik
    ]
    return max(uygun, key=lambda k: float(k.split("_")[0])) if uygun else None


def test(lig):
    maclar = maclari_al(lig)
    gunler = defaultdict(list)

    for mac in maclar:
        gunler[mac[0]].append(mac)

    takimlar = defaultdict(bos_takim)
    kayitlar = []

    for gun in sorted(gunler):
        for _, _, ev, dep, eg, dg in gunler[gun]:
            if min(takimlar[ev]["mac"], takimlar[dep]["mac"]) < 5:
                continue

            eski = secim(v2(ev, dep, takimlar))
            yeni = secim(v3(ev, dep, takimlar))

            kayitlar.append({
                "lig": lig,
                "tarih": gun.strftime("%Y-%m-%d"),
                "mac": f"{ev} - {dep}",
                "skor": f"{eg}-{dg}",
                "V2": eski or "RISKLI",
                "V3": yeni or "RISKLI",
                "V2_dogru": eg + dg > float(eski.split("_")[0]) if eski else None,
                "V3_dogru": eg + dg > float(yeni.split("_")[0]) if yeni else None,
            })

        for _, _, ev, dep, eg, dg in gunler[gun]:
            istatistik_ekle(takimlar, ev, dep, eg, dg)

    return kayitlar


def rapor(kayitlar):
    for model in ("V2", "V3"):
        print("\n", model)
        for cizgi in ESIKLER:
            secilenler = [r for r in kayitlar if r[model] == cizgi]
            dogru = sum(r[f"{model}_dogru"] for r in secilenler)
            toplam = len(secilenler)
            oran = 100 * dogru / toplam if toplam else 0
            print(cizgi, "Dogru:", dogru,
                  "Yanlis:", toplam - dogru,
                  "Basari: %", round(oran, 2))

    ortak = [r for r in kayitlar if r["V2"] != "RISKLI" and r["V3"] != "RISKLI"]
    print("\nHer iki modelin tahmin verdigi mac:", len(ortak))

    for r in ortak:
        if r["V2_dogru"] != r["V3_dogru"]:
            print("FARK:", r["lig"], r["mac"], r["skor"],
                  "V2:", r["V2"], r["V2_dogru"],
                  "V3:", r["V3"], r["V3_dogru"])


tum_kayitlar = []

for lig in LIGLER:
    try:
        kayitlar = test(lig)
        tum_kayitlar.extend(kayitlar)
        print("\nLIG:", lig, "Incelenen:", len(kayitlar))
        rapor(kayitlar)
    except Exception as hata:
        print("LIG HATASI:", lig, str(hata))

print("\nGENEL SONUCLAR")
rapor(tum_kayitlar)
