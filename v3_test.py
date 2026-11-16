
import csv
import io
from collections import defaultdict
from datetime import datetime
from urllib.request import Request, urlopen

from gol_modeli import bos_takim
from gol_modeli import mac_analizi as v2
from gol_modeli_v3 import mac_analizi as v3

URL = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"

istek = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(istek, timeout=30) as cevap:
    metin = cevap.read().decode("utf-8-sig")

maclar = []

for sira, satir in enumerate(csv.DictReader(io.StringIO(metin))):
    try:
        tarih = datetime.strptime(satir["Date"], "%d/%m/%Y")
        ev = satir["HomeTeam"].strip()
        dep = satir["AwayTeam"].strip()
        eg = int(satir["FTHG"])
        dg = int(satir["FTAG"])
        if not ev or not dep or min(eg, dg) < 0:
            continue
        maclar.append((tarih, sira, ev, dep, eg, dg))
    except (ValueError, KeyError, TypeError, AttributeError):
        continue

maclar.sort(key=lambda m: (m[0], m[1]))
takimlar = defaultdict(bos_takim)

sonuclar = {
    "V2": {"dogru": 0, "yanlis": 0},
    "V3": {"dogru": 0, "yanlis": 0},
}
esikler = {"1.5_ust": 75, "2.5_ust": 65, "3.5_ust": 65}
test_edilen = 0

for tarih, sira, ev, dep, eg, dg in maclar:
    # Ayni gundeki maclar birbirine veri olmasin.
    pass

gunler = defaultdict(list)
for mac in maclar:
    gunler[mac[0]].append(mac)

for gun in sorted(gunler):
    bugun = gunler[gun]

    for _, _, ev, dep, eg, dg in bugun:
        if min(takimlar[ev]["mac"], takimlar[dep]["mac"]) < 5:
            continue

        tahminler = {
            "V2": v2(ev, dep, takimlar),
            "V3": v3(ev, dep, takimlar),
        }
        test_edilen += 1

        for model, sonuc in tahminler.items():
            secimler = [
                (sinir, olasilik)
                for sinir, olasilik in esikler.items()
                if sonuc[sinir] >= olasilik
            ]
            if not secimler:
                continue

            # En yuksek gol cizgisini sec.
            secilen = max(secimler, key=lambda x: float(x[0].split("_")[0]))
            gol_siniri = float(secilen[0].split("_")[0])
            basarili = eg + dg > gol_siniri

            alan = "dogru" if basarili else "yanlis"
            sonuclar[model][alan] += 1

    # Gun tamamlandiktan sonra istatistikleri guncelle.
    for _, _, ev, dep, eg, dg in bugun:
        a = takimlar[ev]
        b = takimlar[dep]

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

print("TIPSTER PRO - GECMIS MAC TESTI")
print("Toplam gecmis mac:", len(maclar))
print("Yeterli veriyle incelenen:", test_edilen)

for model, sonuc in sonuclar.items():
    dogru = sonuc["dogru"]
    yanlis = sonuc["yanlis"]
    toplam = dogru + yanlis
    oran = 100 * dogru / toplam if toplam else 0

    print(
        model,
        "Dogru:", dogru,
        "Yanlis:", yanlis,
        "Tahmin:", toplam,
        "Basari: %", round(oran, 2)
    )

