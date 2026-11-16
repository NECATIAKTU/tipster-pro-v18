import json
from datetime import datetime, timezone
from pathlib import Path

from coklu_lig_motoru import tum_ligleri_al
from gercek_mac_analizi import fiksturu_al
from pazar_motoru import pazar_analizi

CIKTI = Path("coklu_pazar_tahminleri.json")


def tarih_oku(metin):
    for bicim in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(metin, bicim).date()
        except ValueError:
            pass
    return None


def beklenen_goller(ev, dep, takimlar):
    a = takimlar[ev]
    b = takimlar[dep]

    if min(a["mac"], b["mac"]) < 5:
        raise ValueError("Yetersiz mac verisi")

    ev_atak = a["attigi"] / a["mac"]
    ev_savunma = a["yedigi"] / a["mac"]
    dep_atak = b["attigi"] / b["mac"]
    dep_savunma = b["yedigi"] / b["mac"]

    ev_gol = (ev_atak + dep_savunma) / 2
    dep_gol = (dep_atak + ev_savunma) / 2

    return ev_gol, dep_gol


def calistir():
    simdi = datetime.now(ZoneInfo("Europe/London"))
    bugun = simdi.date()

    ligler = tum_ligleri_al()
    fikstur = fiksturu_al()

    tahminler = []
    atlanan = {}

    for mac in fikstur:
        kod = (mac.get("Div") or "").strip()
        ev = (mac.get("HomeTeam") or "").strip()
        dep = (mac.get("AwayTeam") or "").strip()
        tarih = tarih_oku((mac.get("Date") or "").strip())

        neden = None

        if tarih is None or tarih < bugun:
            neden = "Tarih veya saat belirsiz"
        elif (mac.get("FTHG") or "").strip():
            neden = "Tamamlanmis mac"
        elif kod not in ligler:
            neden = "Lig desteklenmiyor"
        elif ev not in ligler[kod] or dep not in ligler[kod]:
            neden = "Takim verisi eksik"

        if neden:
            atlanan[neden] = atlanan.get(neden, 0) + 1
            continue

        try:
            ev_gol, dep_gol = beklenen_goller(
                ev, dep, ligler[kod]
            )
            pazarlar = pazar_analizi(ev_gol, dep_gol)
        except (ValueError, KeyError, ZeroDivisionError) as hata:
            neden = str(hata)
            atlanan[neden] = atlanan.get(neden, 0) + 1
            continue

        adaylar = {
            ad: yuzde for ad, yuzde in pazarlar.items()
            if ad in (
                "MS 1", "MS X", "MS 2",
                "1X", "X2", "12",
                "KG VAR", "KG YOK",
                "1.5 UST", "1.5 ALT",
                "2.5 UST", "2.5 ALT",
                "3.5 UST", "3.5 ALT",
                "Ev -1.5 handikap",
                "Dep -1.5 handikap"
            )
        }

        en_yuksek = max(adaylar, key=adaylar.get)

        tahminler.append({
            "tarih": tarih.isoformat(),
            "lig": kod,
            "ev": ev,
            "dep": dep,
            "model": "TIPSTER_PRO_PAZAR_V1",
            "hesaplama_zamani_utc": simdi.isoformat(),
            "baslama_saati_dogrulandi": False,
            "ev_beklenen_gol": round(ev_gol, 2),
            "dep_beklenen_gol": round(dep_gol, 2),
            "en_yuksek_olasilik_pazari": en_yuksek,
            "en_yuksek_olasilik": adaylar[en_yuksek],
            "oran_degerlendirmesi": "YAPILMADI",
            "pazarlar": pazarlar
        })

    CIKTI.write_text(
        json.dumps(
            tahminler, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    print("TIPSTER PRO - COKLU PAZAR")
    print("Fikstur maclari:", len(fikstur))
    print("Analiz edilen:", len(tahminler))
    print("Atlanan:", atlanan)

    for mac in tahminler[:20]:
        print(
            mac["tarih"],
            mac["ev"], "-", mac["dep"],
            "|", mac["en_yuksek_olasilik_pazari"],
            "|", mac["en_yuksek_olasilik"]
        )


if __name__ == "__main__":
    calistir()
