"""V19 OpenFootball ücretsiz veri keşfi.
Salt okunur; V18 ve canlı panel değişmez.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
API = "https://api.github.com/repos/openfootball/football.json/contents/2026-27"
CIKTI = "v19_openfootball_rapor.json"


def getir(url):
    req = Request(url, headers={
        "User-Agent": "TIPSTER-V19-Research",
        "Accept": "application/vnd.github+json"
    })
    with urlopen(req, timeout=20) as cevap:
        return json.load(cevap)


def denetle():
    rapor = {
        "kaynak": "OpenFootball football.json",
        "lisans": "CC0",
        "sezon": "2026-27",
        "salt_okunur": True,
        "panele_aktarildi": False,
        "olusturulma_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "ligler": []
    }

    dosyalar = getir(API)
    if not isinstance(dosyalar, list):
        raise ValueError("Lig listesi gecersiz")

    jsonlar = sorted(
        x["name"] for x in dosyalar
        if x.get("type") == "file"
        and x.get("name", "").endswith(".json")
    )
    rapor["bulunan_lig_dosyasi"] = len(jsonlar)

    for ad in jsonlar[:10]:
        kayit = {"dosya": ad}
        try:
            veri = getir(BASE + "/2026-27/" + ad)
            maclar = veri.get("matches", [])
            if not isinstance(maclar, list):
                raise ValueError("Mac listesi gecersiz")

            kayit["lig"] = veri.get("name", ad)
            kayit["toplam_mac"] = len(maclar)
            kayit["skorlu_mac"] = sum(
                isinstance(m.get("score"), dict)
                and isinstance(m["score"].get("ft"), list)
                and len(m["score"]["ft"]) == 2
                for m in maclar if isinstance(m, dict)
            )
            tarihler = sorted(
                m["date"] for m in maclar
                if isinstance(m, dict)
                and isinstance(m.get("date"), str)
            )
            kayit["son_mac_tarihi"] = (
                tarihler[-1] if tarihler else None
            )
        except (OSError, ValueError, KeyError, TypeError) as hata:
            kayit["hata"] = str(hata)[:150]

        rapor["ligler"].append(kayit)

    Path(CIKTI).write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("BULUNAN LIG:", len(jsonlar))
    print("DENETLENEN:", len(rapor["ligler"]))
    print("RAPOR:", CIKTI)


if __name__ == "__main__":
    denetle()
