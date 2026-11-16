
import json
import math
from collections import defaultdict
from pathlib import Path


def yukle(dosya="espn_gecmis_maclar.json"):
    yol = Path(dosya)
    if not yol.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadi: {dosya}"
        )

    with yol.open("r", encoding="utf-8") as f:
        veri = json.load(f)

    if isinstance(veri, dict):
        maclar = veri.get("matches", [])
    elif isinstance(veri, list):
        maclar = veri
    else:
        raise ValueError("Gecersiz veri formati")

    if not isinstance(maclar, list):
        raise ValueError("matches bir liste olmali")

    return maclar


def istatistikler(maclar, lig_kodu):
    takimlar = defaultdict(
        lambda: {
            "mac": 0,
            "atilan": 0,
            "yenilen": 0,
        }
    )

    gorulen = set()

    for m in maclar:
        if m.get("lig") != lig_kodu:
            continue

        mac_id = m.get("id")
        if not mac_id or mac_id in gorulen:
            continue

        ev = str(m.get("ev_id") or "").strip()
        dep = str(m.get("dep_id") or "").strip()

        if not ev or not dep or ev == dep:
            continue

        try:
            eg = int(m["ev_gol"])
            dg = int(m["dep_gol"])
        except (KeyError, TypeError, ValueError):
            continue

        if eg < 0 or dg < 0:
            continue

        gorulen.add(mac_id)

        takimlar[ev]["mac"] += 1
        takimlar[ev]["atilan"] += eg
        takimlar[ev]["yenilen"] += dg

        takimlar[dep]["mac"] += 1
        takimlar[dep]["atilan"] += dg
        takimlar[dep]["yenilen"] += eg

    return dict(takimlar)


def poisson_ust(lam, esik):
    if not math.isfinite(lam) or lam < 0:
        raise ValueError("Gecersiz gol beklentisi")

    toplam = sum(
        math.exp(-lam) * lam**k / math.factorial(k)
        for k in range(esik + 1)
    )
    return max(0.0, min(1.0, 1.0 - toplam))


def mac_analizi(
    maclar, lig_kodu, ev_id, dep_id,
    minimum_mac=5
):
    takimlar = istatistikler(maclar, lig_kodu)

    ev = takimlar.get(str(ev_id))
    dep = takimlar.get(str(dep_id))

    if not ev or not dep:
        return {
            "durum": "VERI_YOK",
            "sebep": "Takim bulunamadi"
        }

    if (
        ev["mac"] < minimum_mac
        or dep["mac"] < minimum_mac
    ):
        return {
            "durum": "YETERSIZ_VERI",
            "ev_mac": ev["mac"],
            "dep_mac": dep["mac"]
        }

    ev_atak = ev["atilan"] / ev["mac"]
    ev_savunma = ev["yenilen"] / ev["mac"]
    dep_atak = dep["atilan"] / dep["mac"]
    dep_savunma = dep["yenilen"] / dep["mac"]

    ev_gol = (ev_atak + dep_savunma) / 2
    dep_gol = (dep_atak + ev_savunma) / 2

    toplam_gol = ev_gol + dep_gol

    return {
        "durum": "TEST",
        "lig": lig_kodu,
        "ev_id": str(ev_id),
        "dep_id": str(dep_id),
        "ev_mac": ev["mac"],
        "dep_mac": dep["mac"],
        "beklenen_ev_gol": round(ev_gol, 3),
        "beklenen_dep_gol": round(dep_gol, 3),
        "beklenen_toplam_gol": round(toplam_gol, 3),
        "ust_1_5": round(
            poisson_ust(toplam_gol, 1) * 100, 2
        ),
        "ust_2_5": round(
            poisson_ust(toplam_gol, 2) * 100, 2
        ),
        "ust_3_5": round(
            poisson_ust(toplam_gol, 3) * 100, 2
        ),
        "ust_4_5": round(
            poisson_ust(toplam_gol, 4) * 100, 2
        ),
    }


if __name__ == "__main__":
    maclar = yukle()
    print("GECMIS MAC:", len(maclar))

    ligler = sorted({
        m.get("lig")
        for m in maclar
        if m.get("lig")
    })

    for lig in ligler:
        takimlar = istatistikler(maclar, lig)
        yeterli = sum(
            1 for t in takimlar.values()
            if t["mac"] >= 5
        )
        print(
            lig,
            "takim:", len(takimlar),
            "yeterli:", yeterli
        )
