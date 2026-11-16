
import json
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from collections import defaultdict

LIGLER = {
    "nor.1": "Norvec Eliteserien",
    "sui.1": "Isvicre Super League",
}

BASE = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/soccer/{lig}/scoreboard?dates={tarih}"
)


def veri_al(lig, tarih):
    url = BASE.format(lig=lig, tarih=tarih)
    istek = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urlopen(istek, timeout=20) as cevap:
        return json.load(cevap)


def gecmis_maclari_al(lig, gun=120):
    bugun = datetime.now(timezone.utc).date()
    maclar = {}
    hatalar = 0

    for fark in range(gun):
        tarih = (bugun - timedelta(days=fark)).strftime("%Y%m%d")

        try:
            veri = veri_al(lig, tarih)
        except Exception as hata:
            hatalar += 1
            if hatalar <= 3:
                print("ISTEK HATASI:", lig, tarih, str(hata))
            continue

        for olay in veri.get("events", []):
            durum = olay.get("status", {}).get("type", {})
            if not durum.get("completed", False):
                continue

            yarismalar = olay.get("competitions", [])
            if not yarismalar:
                continue

            ev = dep = None
            for takim in yarismalar[0].get("competitors", []):
                bilgi = takim.get("team", {})
                ad = bilgi.get("displayName", "").strip()
                try:
                    gol = int(takim.get("score"))
                except (TypeError, ValueError):
                    continue

                if takim.get("homeAway") == "home":
                    ev = (ad, gol)
                elif takim.get("homeAway") == "away":
                    dep = (ad, gol)

            if ev and dep:
                maclar[str(olay.get("id"))] = (ev, dep)

    takimlar = defaultdict(
        lambda: {"mac": 0, "attigi": 0, "yedigi": 0}
    )

    for (ev_ad, ev_gol), (dep_ad, dep_gol) in maclar.values():
        takimlar[ev_ad]["mac"] += 1
        takimlar[ev_ad]["attigi"] += ev_gol
        takimlar[ev_ad]["yedigi"] += dep_gol

        takimlar[dep_ad]["mac"] += 1
        takimlar[dep_ad]["attigi"] += dep_gol
        takimlar[dep_ad]["yedigi"] += ev_gol

    return dict(takimlar), len(maclar), hatalar


if __name__ == "__main__":
    for lig, ad in LIGLER.items():
        takimlar, mac_sayisi, hatalar = gecmis_maclari_al(
            lig, gun=120
        )
        print(
            ad,
            "| Tamamlanmis mac:", mac_sayisi,
            "| Takim:", len(takimlar),
            "| Istek hatasi:", hatalar
        )
        print("En az 5 mac oynayan takim:",
              sum(v["mac"] >= 5 for v in takimlar.values()))
