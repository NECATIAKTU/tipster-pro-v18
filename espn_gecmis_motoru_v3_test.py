import json
import math
from collections import defaultdict

VERI_DOSYASI = "espn_gecmis_v3_genisletilmis_test.json"


def verileri_yukle():
    with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f).get("matches", [])


def poisson_ust(lam, esik):
    alt = sum(
        math.exp(-lam) * lam**k / math.factorial(k)
        for k in range(esik + 1)
    )
    return round(100 * (1 - alt), 2)


def mac_analiz(maclar, lig_kodu, ev_id, dep_id):
    lig_maclari = [
        m for m in maclar
        if m.get("lig") == lig_kodu
    ]

    ev = [
        m for m in lig_maclari
        if str(m.get("ev_id")) == str(ev_id)
    ]
    dep = [
        m for m in lig_maclari
        if str(m.get("dep_id")) == str(dep_id)
    ]

    if len(ev) < 5 or len(dep) < 5:
        return {
            "durum": "YETERSIZ_VERI",
            "ev_mac": len(ev),
            "dep_mac": len(dep)
        }

    ev_atak = sum(m["ev_gol"] for m in ev) / len(ev)
    dep_savunma = sum(m["ev_gol"] for m in dep) / len(dep)

    dep_atak = sum(m["dep_gol"] for m in dep) / len(dep)
    ev_savunma = sum(m["dep_gol"] for m in ev) / len(ev)

    beklenen_ev = max(0.1, (ev_atak + dep_savunma) / 2)
    beklenen_dep = max(0.1, (dep_atak + ev_savunma) / 2)

    toplam = beklenen_ev + beklenen_dep

    return {
        "durum": "TEST",
        "ev_mac": len(ev),
        "dep_mac": len(dep),
        "beklenen_ev_gol": round(beklenen_ev, 2),
        "beklenen_dep_gol": round(beklenen_dep, 2),
        "ust_1_5": poisson_ust(toplam, 1),
        "ust_2_5": poisson_ust(toplam, 2),
        "ust_3_5": poisson_ust(toplam, 3),
        "ust_4_5": poisson_ust(toplam, 4)
    }


if __name__ == "__main__":
    maclar = verileri_yukle()
    print("ESPN V3 MOTOR TESTI")
    print("Gecmis mac sayisi:", len(maclar))
