
"""TIPSTER PRO - ESPN V3 29 lig gecmis veri testi.

Son 30 gunu gunluk sorgularla tarar.
Mevcut arsiv dosyalarina dokunmaz.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LIGLER = [
    "eng.1", "eng.2", "eng.3", "eng.4",
    "esp.1", "ger.1", "ita.1", "fra.1",
    "ned.1", "por.1", "sui.1", "nor.1",
    "tur.1", "tur.2", "sco.1", "bel.1",
    "aut.1", "den.1", "swe.1", "irl.1",
    "usa.1", "mex.1", "bra.1", "arg.1",
    "col.1", "jpn.1", "chn.1", "aus.1",
    "rsa.1",
]

BASE = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/soccer/{lig}/scoreboard"
)


def sorgula(lig, tarih):
    params = urlencode({
        "dates": tarih.strftime("%Y%m%d"),
        "limit": 500,
    })
    url = BASE.format(lig=lig) + "?" + params

    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urlopen(req, timeout=25) as cevap:
            veri = json.load(cevap)
        return veri.get("events", []), None

    except (
        HTTPError, URLError, TimeoutError,
        ValueError, OSError
    ) as hata:
        return [], str(hata)


def main():
    bitis = (
        datetime.now(timezone.utc)
        - timedelta(days=1)
    ).date()
    baslangic = bitis - timedelta(days=29)

    print("TIPSTER PRO - ESPN V3 29 LIG TESTI")
    print("Lig sayisi:", len(LIGLER))
    print("Tarih araligi:", baslangic, bitis)

    toplam = 0
    toplam_hata = 0

    for lig in LIGLER:
        maclar = {}
        hatalar = 0
        ilk_hata = None

        for fark in range(30):
            tarih = baslangic + timedelta(days=fark)
            olaylar, hata = sorgula(lig, tarih)

            if hata:
                hatalar += 1
                if ilk_hata is None:
                    ilk_hata = hata

            for olay in olaylar:
                mac_id = olay.get("id")
                if mac_id:
                    maclar[str(mac_id)] = olay

            time.sleep(0.1)

        tamamlanan = sum(
            1 for olay in maclar.values()
            if olay.get("status", {})
            .get("type", {})
            .get("completed", False)
        )

        toplam += tamamlanan
        toplam_hata += hatalar

        print(json.dumps({
            "lig": lig,
            "benzersiz_mac": len(maclar),
            "tamamlanan_mac": tamamlanan,
            "hatali_gun": hatalar,
            "ilk_hata": ilk_hata,
        }, ensure_ascii=False), flush=True)

    print("TOPLAM TAMAMLANAN MAC:", toplam)
    print("TOPLAM HATALI GUN:", toplam_hata)
    print("TEST TAMAMLANDI")
    print("Arsiv dosyalari degistirilmedi.")


if __name__ == "__main__":
    main()
