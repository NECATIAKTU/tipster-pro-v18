
import json
import math
from collections import defaultdict
from pathlib import Path

VERI_DOSYASI = "espn_gecmis_maclar.json"


def verileri_yukle():
    yol = Path(VERI_DOSYASI)
    if not yol.exists():
        raise FileNotFoundError(f"Dosya bulunamadi: {VERI_DOSYASI}")

    with yol.open("r", encoding="utf-8") as f:
        veri = json.load(f)

    return veri.get("matches", [])


def takim_istatistikleri(maclar, lig_kodu):
    takimlar = defaultdict(
        lambda: {
            "mac": 0,
            "atilan": 0,
            "yenilen": 0,
            "ev_mac": 0,
            "ev_atilan": 0,
            "ev_yenilen": 0,
            "dep_mac": 0,
            "dep_atilan": 0,
            "dep_yenilen": 0,
        }
    )

    for mac in maclar:
        if mac.get("lig") != lig_kodu:
            continue

        ev = mac.get("ev_id")
        dep = mac.get("dep_id")

        try:
            ev_gol = int(mac["ev_gol"])
            dep_gol = int(mac["dep_gol"])
        except (KeyError, ValueError, TypeError):
            continue

        if not ev or not dep or ev == dep:
            continue

        e = takimlar[str(ev)]
        d = takimlar[str(dep)]

        e["mac"] += 1
        e["atilan"] += ev_gol
        e["yenilen"] += dep_gol
        e["ev_mac"] += 1
        e["ev_atilan"] += ev_gol
        e["ev_yenilen"] += dep_gol

        d["mac"] += 1
        d["atilan"] += dep_gol
        d["yenilen"] += ev_gol
        d["dep_mac"] += 1
        d["dep_atilan"] += dep_gol
        d["dep_yenilen"] += ev_gol

    return dict(takimlar)


def poisson_ust(lam, esik):
    if not math.isfinite(lam) or lam < 0:
        return None

    k = int(esik)
    toplam = sum(
        math.exp(-lam) * lam**i / math.factorial(i)
        for i in range(k + 1)
    )
    return max(0.0, min(1.0, 1.0 - toplam))


def mac_analiz(maclar, lig_kodu, ev_id, dep_id):
    ist = takim_istatistikleri(maclar, lig_kodu)
    ev = ist.get(str(ev_id))
    dep = ist.get(str(dep_id))

    if not ev or not dep:
        return {"durum": "VERI_YOK"}

    if ev["mac"] < 5 or dep["mac"] < 5:
        return {"durum": "YETERSIZ_VERI"}

    ev_hucum = ev["ev_atilan"] / ev["ev_mac"] if ev["ev_mac"] else ev["atilan"] / ev["mac"]
    ev_savunma = ev["ev_yenilen"] / ev["ev_mac"] if ev["ev_mac"] else ev["yenilen"] / ev["mac"]
    dep_hucum = dep["dep_atilan"] / dep["dep_mac"] if dep["dep_mac"] else dep["atilan"] / dep["mac"]
    dep_savunma = dep["dep_yenilen"] / dep["dep_mac"] if dep["dep_mac"] else dep["yenilen"] / dep["mac"]

    beklenen_ev = max(0.1, (ev_hucum + dep_savunma) / 2)
    beklenen_dep = max(0.1, (dep_hucum + ev_savunma) / 2)
    toplam = beklenen_ev + beklenen_dep

    return {
        "durum": "TEST",
        "ev_mac": ev["mac"],
        "dep_mac": dep["mac"],
        "beklenen_ev_gol": round(beklenen_ev, 3),
        "beklenen_dep_gol": round(beklenen_dep, 3),
        "ust_1_5": round(poisson_ust(toplam, 1) * 100, 2),
        "ust_2_5": round(poisson_ust(toplam, 2) * 100, 2),
        "ust_3_5": round(poisson_ust(toplam, 3) * 100, 2),
        "ust_4_5": round(poisson_ust(toplam, 4) * 100, 2),
    }


if __name__ == "__main__":
    maclar = verileri_yukle()
    ligler = sorted({m.get("lig") for m in maclar if m.get("lig")})

    print("ESPN GECMIS MOTORU TEST")
    print("Toplam gecmis mac:", len(maclar))

    for lig in ligler:
        ist = takim_istatistikleri(maclar, lig)
        yeterli = sum(1 for t in ist.values() if t["mac"] >= 5)
        print(f"{lig}: {len(ist)} takim, {yeterli} takimda en az 5 mac")
