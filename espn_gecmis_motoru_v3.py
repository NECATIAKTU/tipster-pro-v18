
"""TIPSTER PRO - ESPN Gecmis Motoru V3.

Mevcut V2 motorunu ve arsivleri degistirmez.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

VERI_DOSYASI = VERI_DOSYASI = "espn_gecmis_v3_yeni_test.json"


def verileri_yukle():
    veri = json.loads(
        Path(VERI_DOSYASI).read_text(encoding="utf-8")
    )
    maclar = veri.get("matches", [])
    if not isinstance(maclar, list):
        raise ValueError("Gecmis mac listesi gecersiz")
    return maclar


def istatistik_hazirla(maclar):
    ligler = defaultdict(
        lambda: defaultdict(
            lambda: {
                "mac": 0, "ev_mac": 0, "dep_mac": 0,
                "atilan": 0, "yenilen": 0,
                "ev_atilan": 0, "ev_yenilen": 0,
                "dep_atilan": 0, "dep_yenilen": 0,
            }
        )
    )

    gorulen = set()

    for m in maclar:
        lig = m.get("lig")
        ev = str(m.get("ev_id") or "")
        dep = str(m.get("dep_id") or "")
        mid = str(m.get("id") or "")

        if not lig or not ev or not dep or ev == dep:
            continue

        anahtar = (lig, mid) if mid else (
            lig, m.get("tarih"), ev, dep
        )
        if anahtar in gorulen:
            continue

        try:
            eg = int(m["ev_gol"])
            dg = int(m["dep_gol"])
        except (KeyError, TypeError, ValueError):
            continue

        if eg < 0 or dg < 0:
            continue

        gorulen.add(anahtar)
        e = ligler[lig][ev]
        d = ligler[lig][dep]

        e["mac"] += 1
        e["ev_mac"] += 1
        e["atilan"] += eg
        e["yenilen"] += dg
        e["ev_atilan"] += eg
        e["ev_yenilen"] += dg

        d["mac"] += 1
        d["dep_mac"] += 1
        d["atilan"] += dg
        d["yenilen"] += eg
        d["dep_atilan"] += dg
        d["dep_yenilen"] += eg

    return {lig: dict(takimlar)
            for lig, takimlar in ligler.items()}


def poisson_ust(lam, esik):
    if not math.isfinite(lam) or lam < 0:
        return None

    toplam = sum(
        math.exp(-lam) * lam ** i / math.factorial(i)
        for i in range(esik + 1)
    )
    return round(
        max(0.0, min(100.0, (1 - toplam) * 100)), 2
    )


def mac_analiz(istatistikler, lig, ev_id, dep_id):
    takimlar = istatistikler.get(lig)

    if not takimlar:
        return {"durum": "LIG_VERISI_YOK"}

    ev = takimlar.get(str(ev_id))
    dep = takimlar.get(str(dep_id))

    if not ev or not dep:
        return {"durum": "TAKIM_VERISI_YOK"}

    if ev["mac"] < 5 or dep["mac"] < 5:
        return {
            "durum": "YETERSIZ_VERI",
            "ev_mac": ev["mac"],
            "dep_mac": dep["mac"],
        }

    def ort(toplam, adet, yedek, yedek_adet):
        if adet:
            return toplam / adet
        return yedek / yedek_adet

    ev_hucum = ort(
        ev["ev_atilan"], ev["ev_mac"],
        ev["atilan"], ev["mac"]
    )
    ev_savunma = ort(
        ev["ev_yenilen"], ev["ev_mac"],
        ev["yenilen"], ev["mac"]
    )
    dep_hucum = ort(
        dep["dep_atilan"], dep["dep_mac"],
        dep["atilan"], dep["mac"]
    )
    dep_savunma = ort(
        dep["dep_yenilen"], dep["dep_mac"],
        dep["yenilen"], dep["mac"]
    )

    beklenen_ev = max(
        0.1, (ev_hucum + dep_savunma) / 2
    )
    beklenen_dep = max(
        0.1, (dep_hucum + ev_savunma) / 2
    )
    toplam = beklenen_ev + beklenen_dep

    return {
        "durum": "TEST",
        "ev_mac": ev["mac"],
        "dep_mac": dep["mac"],
        "beklenen_ev_gol": round(beklenen_ev, 3),
        "beklenen_dep_gol": round(beklenen_dep, 3),
        "ust_1_5": poisson_ust(toplam, 1),
        "ust_2_5": poisson_ust(toplam, 2),
        "ust_3_5": poisson_ust(toplam, 3),
        "ust_4_5": poisson_ust(toplam, 4),
    }


if __name__ == "__main__":
    maclar = verileri_yukle()
    ist = istatistik_hazirla(maclar)

    print("TIPSTER PRO - ESPN MOTOR V3")
    print("Gecmis mac:", len(maclar))
    print("Veri bulunan lig:", len(ist))

    for lig in sorted(ist):
        takimlar = ist[lig]
        yeterli = sum(
            t["mac"] >= 5 for t in takimlar.values()
        )
        print(
            lig, "| takim:", len(takimlar),
            "| yeterli veri:", yeterli
        )
