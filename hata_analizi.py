
from collections import defaultdict

from gol_modeli import bos_takim, mac_analizi
from model_karsilastirma import (
    LIGLER, maclari_al, istatistik_ekle
)

ESIK = 65
yanlislar = []
dogrular = []
hatalar = []

for lig in LIGLER:
    try:
        gunler = defaultdict(list)

        for mac in maclari_al(lig):
            gunler[mac[0]].append(mac)

        takimlar = defaultdict(bos_takim)

        for gun in sorted(gunler):
            for _, _, ev, dep, eg, dg in gunler[gun]:
                a = takimlar[ev]
                b = takimlar[dep]

                if min(a["mac"], b["mac"]) < 5:
                    continue

                sonuc = mac_analizi(ev, dep, takimlar)
                olasilik = sonuc["2.5_ust"]

                if olasilik < ESIK:
                    continue

                kayit = {
                    "lig": lig,
                    "tarih": gun.strftime("%Y-%m-%d"),
                    "mac": f"{ev} - {dep}",
                    "skor": f"{eg}-{dg}",
                    "olasilik": olasilik,
                    "beklenen_gol": sonuc["beklenen_gol"],
                    "ev_attigi": round(a["attigi"] / a["mac"], 2),
                    "ev_yedigi": round(a["yedigi"] / a["mac"], 2),
                    "dep_attigi": round(b["attigi"] / b["mac"], 2),
                    "dep_yedigi": round(b["yedigi"] / b["mac"], 2),
                }

                if eg + dg >= 3:
                    dogrular.append(kayit)
                else:
                    yanlislar.append(kayit)

            # Ayni gundeki sonuclar sonraki gun kullanilir.
            for _, _, ev, dep, eg, dg in gunler[gun]:
                istatistik_ekle(takimlar, ev, dep, eg, dg)

    except Exception as hata:
        hatalar.append((lig, str(hata)))

print("TIPSTER PRO - 2.5 UST HATA ANALIZI")
print("Dogru:", len(dogrular))
print("Yanlis:", len(yanlislar))

for kayit in yanlislar:
    print(
        "YANLIS:",
        kayit["lig"],
        kayit["tarih"],
        kayit["mac"],
        "Skor:", kayit["skor"],
        "Olasilik:", kayit["olasilik"],
        "Beklenen gol:", kayit["beklenen_gol"],
        "Ev atilan/yenen:",
        kayit["ev_attigi"], kayit["ev_yedigi"],
        "Dep atilan/yenen:",
        kayit["dep_attigi"], kayit["dep_yedigi"]
    )

for lig, hata in hatalar:
    print("VERI HATASI:", lig, hata)
