
from collections import defaultdict
from gol_modeli import bos_takim, mac_analizi
from model_karsilastirma import (
    LIGLER, maclari_al, istatistik_ekle
)

ESIKLER = [65, 70, 75, 80]


def test(lig):
    gunler = defaultdict(list)
    for mac in maclari_al(lig):
        gunler[mac[0]].append(mac)

    takimlar = defaultdict(bos_takim)
    sonuclar = {
        esik: {"dogru": 0, "yanlis": 0}
        for esik in ESIKLER
    }

    for gun in sorted(gunler):
        for _, _, ev, dep, eg, dg in gunler[gun]:
            if min(takimlar[ev]["mac"], takimlar[dep]["mac"]) < 5:
                continue

            olasilik = mac_analizi(
                ev, dep, takimlar
            )["2.5_ust"]

            for esik in ESIKLER:
                if olasilik >= esik:
                    alan = "dogru" if eg + dg >= 3 else "yanlis"
                    sonuclar[esik][alan] += 1

        for _, _, ev, dep, eg, dg in gunler[gun]:
            istatistik_ekle(takimlar, ev, dep, eg, dg)

    return sonuclar


genel = {
    esik: {"dogru": 0, "yanlis": 0}
    for esik in ESIKLER
}

for lig in LIGLER:
    try:
        sonuc = test(lig)
        for esik in ESIKLER:
            for alan in ("dogru", "yanlis"):
                genel[esik][alan] += sonuc[esik][alan]
    except Exception as hata:
        print("LIG HATASI:", lig, hata)

print("TIPSTER PRO - 2.5 UST ESIK TESTI")

for esik in ESIKLER:
    dogru = genel[esik]["dogru"]
    yanlis = genel[esik]["yanlis"]
    toplam = dogru + yanlis
    oran = 100 * dogru / toplam if toplam else 0

    print(
        f"Esik %{esik}:",
        f"Dogru {dogru}",
        f"Yanlis {yanlis}",
        f"Toplam {toplam}",
        f"Basari %{oran:.2f}"
    )
