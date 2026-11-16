
from collections import defaultdict
from math import exp, factorial

from gol_modeli import bos_takim, form_ortalamasi
from model_karsilastirma import istatistik_ekle
from model_karsilastirma import LIGLER, maclari_al


AGIRLIKLAR = [0.0, 0.25, 0.50, 0.75, 1.0]


def ortalama(toplam, adet, yedek):
    return toplam / adet if adet >= 3 else yedek


def ust_25(lam):
    return 1 - exp(-lam) * sum(
        lam ** k / factorial(k) for k in range(3)
    )


def tahmin(ev, dep, takimlar, form_agirligi):
    a, b = takimlar[ev], takimlar[dep]

    if min(a["mac"], b["mac"]) < 5:
        return None

    ev_atak = ortalama(
        a.get("ev_attigi", 0), a.get("ev_mac", 0),
        a["attigi"] / a["mac"]
    )
    ev_savunma = ortalama(
        a.get("ev_yedigi", 0), a.get("ev_mac", 0),
        a["yedigi"] / a["mac"]
    )
    dep_atak = ortalama(
        b.get("dep_attigi", 0), b.get("dep_mac", 0),
        b["attigi"] / b["mac"]
    )
    dep_savunma = ortalama(
        b.get("dep_yedigi", 0), b.get("dep_mac", 0),
        b["yedigi"] / b["mac"]
    )

    beklenen_ev = (ev_atak + dep_savunma) / 2
    beklenen_dep = (dep_atak + ev_savunma) / 2

    a_form = a.get("son_maclar", [])
    b_form = b.get("son_maclar", [])

    if len(a_form) >= 3 and len(b_form) >= 3:
        form_ev = (
            form_ortalamasi(a_form, 0)
            + form_ortalamasi(b_form, 1)
        ) / 2
        form_dep = (
            form_ortalamasi(b_form, 0)
            + form_ortalamasi(a_form, 1)
        ) / 2

        beklenen_ev = (
            (1 - form_agirligi) * beklenen_ev
            + form_agirligi * form_ev
        )
        beklenen_dep = (
            (1 - form_agirligi) * beklenen_dep
            + form_agirligi * form_dep
        )

    return ust_25(max(0, beklenen_ev + beklenen_dep))


sonuclar = {
    w: {"mac": 0, "brier": 0.0, "dogru": 0, "secim": 0}
    for w in AGIRLIKLAR
}

for lig in LIGLER:
    try:
        gunler = defaultdict(list)

        for mac in maclari_al(lig):
            gunler[mac[0]].append(mac)

        takimlar = defaultdict(bos_takim)

        for gun in sorted(gunler):
            # Aynı günün maçları, sonuçları modele eklenmeden test edilir.
            for _, _, ev, dep, eg, dg in gunler[gun]:
                gercek = int(eg + dg >= 3)

                for w in AGIRLIKLAR:
                    p = tahmin(ev, dep, takimlar, w)
                    if p is None:
                        continue

                    s = sonuclar[w]
                    s["mac"] += 1
                    s["brier"] += (p - gercek) ** 2

                    if p >= 0.60:
                        s["secim"] += 1
                        s["dogru"] += gercek

            for _, _, ev, dep, eg, dg in gunler[gun]:
                istatistik_ekle(takimlar, ev, dep, eg, dg)

    except Exception as hata:
        print("VERI HATASI:", lig, hata)

print("\nTIPSTER PRO - AGIRLIK TESTI")
print("Form | Mac | Brier | %60+ Secim | Basari")

for w, s in sonuclar.items():
    n = s["mac"]
    secim = s["secim"]
    print(
        f"%{w*100:.0f} | {n} | "
        f"{s['brier']/n:.4f} | " if n else f"%{w*100:.0f} | 0 | - | ",
        secim,
        f"| %{100*s['dogru']/secim:.1f}" if secim else "| -"
    )
