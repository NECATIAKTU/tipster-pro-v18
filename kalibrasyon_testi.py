
from collections import defaultdict
from gol_modeli import bos_takim, mac_analizi
from model_karsilastirma import (
    LIGLER, maclari_al, istatistik_ekle
)

ARALIKLAR = [(0, 50), (50, 60), (60, 65),
             (65, 70), (70, 75), (75, 80), (80, 101)]

gruplar = {
    (alt, ust): {"adet": 0, "dogru": 0, "beklenen": 0.0}
    for alt, ust in ARALIKLAR
}

toplam_mac = 0
beklenen_gol_toplami = 0.0
gercek_gol_toplami = 0
veri_hatalari = []

for lig in LIGLER:
    try:
        gunler = defaultdict(list)
        for mac in maclari_al(lig):
            gunler[mac[0]].append(mac)

        takimlar = defaultdict(bos_takim)

        for gun in sorted(gunler):
            for _, _, ev, dep, eg, dg in gunler[gun]:
                if min(takimlar[ev]["mac"], takimlar[dep]["mac"]) < 5:
                    continue

                sonuc = mac_analizi(ev, dep, takimlar)
                olasilik = sonuc["2.5_ust"]
                toplam_mac += 1
                beklenen_gol_toplami += sonuc["beklenen_gol"]
                gercek_gol_toplami += eg + dg

                for alt, ust in ARALIKLAR:
                    if alt <= olasilik < ust:
                        grup = gruplar[(alt, ust)]
                        grup["adet"] += 1
                        grup["beklenen"] += olasilik
                        if eg + dg >= 3:
                            grup["dogru"] += 1
                        break

            for _, _, ev, dep, eg, dg in gunler[gun]:
                istatistik_ekle(takimlar, ev, dep, eg, dg)

    except Exception as hata:
        veri_hatalari.append((lig, str(hata)))

print("TIPSTER PRO - KALIBRASYON TESTI")
print("Incelenen mac:", toplam_mac)

if toplam_mac:
    print("Ortalama beklenen gol:",
          round(beklenen_gol_toplami / toplam_mac, 2))
    print("Ortalama gercek gol:",
          round(gercek_gol_toplami / toplam_mac, 2))

for (alt, ust), grup in gruplar.items():
    adet = grup["adet"]
    if adet == 0:
        continue

    ort_tahmin = grup["beklenen"] / adet
    gercek_oran = 100 * grup["dogru"] / adet

    print(
        f"%{alt}-%{ust}:",
        "Mac:", adet,
        "Model ortalamasi:", round(ort_tahmin, 1),
        "Gercek 2.5 UST:", round(gercek_oran, 1)
    )

for lig, hata in veri_hatalari:
    print("VERI HATASI:", lig, hata)
