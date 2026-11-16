
"""TIPSTER PRO - Ek ligler icin ESPN gecmis mac motoru.

Her calismada 14 gun geriye gider.
Eski tahmin ve kilitli arsivlere dokunmaz.

Ciktilar:
tipster_ek_lig_gecmis.json
tipster_ek_lig_durum.json
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LIGLER = (
    "bra.1", "arg.1", "den.1", "swe.1",
    "mex.1", "usa.1", "col.1", "rsa.1",
    "aut.1", "aus.1", "chn.1",
    "uefa.europa", "uefa.europa.conf"
)
    
    
    

    

VERI = Path("tipster_ek_lig_gecmis.json")
DURUM = Path("tipster_ek_lig_durum.json")

GUNLUK_PENCERE = 30
MAX_GECMIS_GUN = 400


def oku(path, default):
    if not path.exists():
        return default

    obj = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(obj, dict):
        raise ValueError(
            f"{path} dict olmali. Dosya korunuyor."
        )

    return obj


def yaz(path, obj):
    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            obj, ensure_ascii=False, indent=2
        ) + "\n",
        encoding="utf-8"
    )

    os.replace(tmp, path)


def cek(lig, gun):
    url = (
        "https://site.api.espn.com/apis/site/v2/"
        f"sports/soccer/{lig}/scoreboard"
        f"?dates={gun.strftime('%Y%m%d')}&limit=500"
    )

    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(req, timeout=20) as response:
        payload = json.load(response)

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("events"), list)
    ):
        raise ValueError("Gecersiz ESPN yaniti")

    return payload["events"]


def sonuc(event, lig, simdi):
    if not event.get(
        "status", {}
    ).get("type", {}).get("completed", False):
        return None

    tarih = datetime.fromisoformat(
        event["date"].replace("Z", "+00:00")
    )

    if tarih.tzinfo is None or tarih >= simdi:
        return None

    rakipler = event[
        "competitions"
    ][0]["competitors"]

    taraf = {
        t.get("homeAway"): t
        for t in rakipler
    }

    ev = taraf["home"]
    dep = taraf["away"]

    ev_id = str(ev["team"]["id"])
    dep_id = str(dep["team"]["id"])

    if ev_id == dep_id:
        return None

    ev_gol = int(ev["score"])
    dep_gol = int(dep["score"])

    if min(ev_gol, dep_gol) < 0:
        return None

    event_id = str(event["id"])

    return {
        "id": f"{lig}|{event_id}",
        "lig": lig,
        "tarih_utc": tarih.astimezone(
            timezone.utc
        ).isoformat(),
        "ev_id": ev_id,
        "dep_id": dep_id,
        "ev": ev["team"].get("displayName", ""),
        "dep": dep["team"].get("displayName", ""),
        "ev_gol": ev_gol,
        "dep_gol": dep_gol,
        "kaynak": "ESPN",
        "sonuc": "FT"
    }


def main():
    simdi = datetime.now(timezone.utc)
    bugun = simdi.date()

    en_eski = bugun - timedelta(
        days=MAX_GECMIS_GUN
    )

    gecmis = oku(
        VERI,
        {
            "schema_version": 1,
            "maclar": {}
        }
    )

    maclar = gecmis.get("maclar")

    if not isinstance(maclar, dict):
        raise ValueError(
            "Gecmis arsiv bicimi bozuk"
        )

    durum = oku(
        DURUM,
        {"sonraki_gun": {}}
    )

    cursor = durum.get("sonraki_gun", {})

    if not isinstance(cursor, dict):
        raise ValueError(
            "Cursor bicimi bozuk"
        )

    for lig in LIGLER:
        try:
            son_gun = (
                date.fromisoformat(cursor[lig])
                if lig in cursor
                else bugun - timedelta(days=1)
            )
        except ValueError:
            raise ValueError(
                f"{lig} cursor tarihi gecersiz"
            )

        ilk_gun = max(
            en_eski,
            son_gun - timedelta(
                days=GUNLUK_PENCERE - 1
            )
        )

        if son_gun < en_eski:
            print(
                lig,
                "| 400 gunluk tarama tamamlandi"
            )
            continue

        yeni = 0
        hatali_gun = None
        gun = son_gun

        while gun >= ilk_gun:
            try:
                olaylar = cek(lig, gun)

                for olay in olaylar:
                    try:
                        mac = sonuc(
                            olay, lig, simdi
                        )
                    except (
                        KeyError, IndexError,
                        TypeError, ValueError
                    ):
                        continue

                    if mac and mac["id"] not in maclar:
                        maclar[mac["id"]] = mac
                        yeni += 1

                cursor[lig] = (
                    gun - timedelta(days=1)
                ).isoformat()

            except (
                HTTPError, URLError,
                TimeoutError, ValueError, OSError
            ) as exc:
                hatali_gun = (
                    gun.isoformat(), str(exc)
                )
                break

            gun -= timedelta(days=1)
            time.sleep(0.05)

        gecmis["updated_at_utc"] = (
            simdi.isoformat()
        )

        yaz(VERI, gecmis)

        durum["sonraki_gun"] = cursor
        durum["updated_at_utc"] = (
            simdi.isoformat()
        )

        yaz(DURUM, durum)

        toplam = sum(
            m.get("lig") == lig
            for m in maclar.values()
        )

        print(
            lig,
            "| Yeni:", yeni,
            "| Toplam:", toplam,
            "| Sonraki tarama tarihi:", cursor.get(lig, "BILINMIYOR"),
            "| Hata:", hatali_gun or "yok"
        )
        
            
            
        
        

    print(
        "TUM LIGLER TOPLAM FT MAC:",
        len(maclar)
    )

    print(
        "UYARI: Henuz tahmin motoruna bagli degil."
    )


if __name__ == "__main__":
    main()
