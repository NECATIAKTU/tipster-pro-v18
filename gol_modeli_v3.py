
import math


def poisson_ust(lam, sinir):
    if not math.isfinite(lam) or lam < 0:
        raise ValueError("Gecersiz gol beklentisi")

    olasilik = math.exp(-lam)
    toplam = olasilik

    for k in range(1, sinir + 1):
        olasilik *= lam / k
        toplam += olasilik

    return max(0.0, min(1.0, 1.0 - toplam))


def oran(toplam, mac, varsayilan):
    return toplam / mac if mac > 0 else varsayilan


def duzeltme(deger, mac, lig_ort, guc=5):
    return (deger * mac + lig_ort * guc) / (mac + guc)


def mac_analizi(ev, dep, takimlar):
    a = takimlar[ev]
    b = takimlar[dep]

    if min(a["mac"], b["mac"]) < 5:
        raise ValueError("Yetersiz mac verisi")

    ev_gol = sum(t["ev_attigi"] for t in takimlar.values())
    dep_gol = sum(t["dep_attigi"] for t in takimlar.values())
    ev_mac = sum(t["ev_mac"] for t in takimlar.values())
    dep_mac = sum(t["dep_mac"] for t in takimlar.values())

    if ev_mac == 0 or dep_mac == 0:
        raise ValueError("Lig verisi yetersiz")

    lig_ev = ev_gol / ev_mac
    lig_dep = dep_gol / dep_mac

    if lig_ev <= 0 or lig_dep <= 0:
        raise ValueError("Lig ortalamasi gecersiz")

    ev_atak = duzeltme(
        oran(a["ev_attigi"], a["ev_mac"], lig_ev),
        a["ev_mac"], lig_ev
    )
    ev_savunma = duzeltme(
        oran(a["ev_yedigi"], a["ev_mac"], lig_dep),
        a["ev_mac"], lig_dep
    )
    dep_atak = duzeltme(
        oran(b["dep_attigi"], b["dep_mac"], lig_dep),
        b["dep_mac"], lig_dep
    )
    dep_savunma = duzeltme(
        oran(b["dep_yedigi"], b["dep_mac"], lig_ev),
        b["dep_mac"], lig_ev
    )

    beklenen_ev = lig_ev * (
        ev_atak / lig_ev
    ) * (
        dep_savunma / lig_ev
    )

    beklenen_dep = lig_dep * (
        dep_atak / lig_dep
    ) * (
        ev_savunma / lig_dep
    )

    toplam = max(0.0, beklenen_ev + beklenen_dep)

    return {
        "beklenen_gol": round(toplam, 2),
        "1.5_ust": round(poisson_ust(toplam, 1) * 100, 1),
        "2.5_ust": round(poisson_ust(toplam, 2) * 100, 1),
        "3.5_ust": round(poisson_ust(toplam, 3) * 100, 1),
        "4.5_ust": round(poisson_ust(toplam, 4) * 100, 1),
    }
