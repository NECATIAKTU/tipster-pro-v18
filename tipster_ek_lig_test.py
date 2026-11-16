
import json
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from pathlib import Path

LIGLER = [
    "bra.1", "arg.1", "den.1", "swe.1",
    "aut.1", "mex.1", "usa.1", "col.1",
    "irl.1", "aus.1", "chn.1", "rsa.1",
    "sui.1", "tur.2",
]

BASE = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/soccer/{}/scoreboard?dates={}"
)

def kontrol_et(lig):
    bugun = datetime.now(timezone.utc).date()
    sonuclar = []
    hatalar = []

    for gun_farki in (1, 7, 14, 21, 28):
        gun = bugun - timedelta(days=gun_farki)
        url = BASE.format(lig, gun.strftime("%Y%m%d"))

        try:
            req = Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urlopen(req, timeout=12) as cevap:
                veri = json.load(cevap)

            for mac in veri.get("events", []):
                if not mac.get("status", {}).get(
                    "type", {}
                ).get("completed", False):
                    continue

                takimlar = mac["competitions"][0][
                    "competitors"
                ]

                if len(takimlar) != 2:
                    continue

                skorlar = [
                    int(t["score"]) for t in takimlar
                ]
                sonuclar.append({
                    "id": mac.get("id"),
                    "skorlar": skorlar
                })

        except Exception as hata:
            hatalar.append(str(hata))

    return {
        "lig": lig,
        "ornek_sonuc": len({
            m["id"] for m in sonuclar
        }),
        "hata_sayisi": len(hatalar),
        "hata_ornekleri": hatalar[:2],
    }

def main():
    rapor = [kontrol_et(lig) for lig in LIGLER]

    Path("tipster_ek_lig_test.json").write_text(
        json.dumps(
            rapor, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    for satir in rapor:
        print(
            satir["lig"],
            "| Sonuc:", satir["ornek_sonuc"],
            "| Hata:", satir["hata_sayisi"]
        )

if __name__ == "__main__":
    main()
