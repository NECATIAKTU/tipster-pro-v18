import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from collections import Counter

from coklu_lig_motoru import tum_ligleri_al
from gercek_mac_analizi import fiksturu_al
from coklu_pazar_analizi import tarih_oku, beklenen_goller
from pazar_secici import pazar_sec

def oranlari_al(mac):
    eslesme = {
        "MS 1": "B365H",
        "MS X": "B365D",
        "MS 2": "B365A",
        "2.5 UST": "B365>2.5",
        "2.5 ALT": "B365<2.5",
    }

    oranlar = {}
    for pazar, sutun in eslesme.items():
        try:
            oran = float(mac.get(sutun) or 0)
            if oran > 1:
                oranlar[pazar] = oran
        except (ValueError, TypeError):
            continue

    return oranlar
  
CIKTI = Path("coklu_pazar_v2_sonuclar.json")

def calistir():
    simdi = datetime.now(timezone.utc)
    bugun = simdi.date()
    ligler = tum_ligleri_al()
    fikstur = fiksturu_al()
    sonuclar = []
    atlanan = Counter()

    for mac in fikstur:
        lig = (mac.get("Div") or "").strip()
        ev = (mac.get("HomeTeam") or "").strip()
        dep = (mac.get("AwayTeam") or "").strip()
        tarih = tarih_oku((mac.get("Date") or "").strip())

        if (mac.get("FTHG") or "").strip():
            atlanan["Tamamlanmis mac"] += 1
            continue
        
        if tarih is None:
            atlanan["Tarih okunamadi"] += 1
            continue

        if tarih < bugun:
            atlanan["Gecmis tarihli mac"] += 1
            continue

            
            
        saat = (mac.get("Time") or "").strip()

        try:
            baslangic = datetime.combine(
                tarih, datetime.strptime(saat, "%H:%M").time()
            ).replace(tzinfo=ZoneInfo("Europe/London"))
        except ValueError:
            atlanan["Baslama saati belirsiz"] += 1
            continue

        if baslangic <= simdi:
            atlanan["Baslamis mac"] += 1
            continue
        if lig not in ligler:
            atlanan["Desteklenmeyen lig"] += 1
            continue

        takimlar = ligler[lig]
        if ev not in takimlar or dep not in takimlar:
            atlanan["Takim bulunamadi"] += 1
            continue

        try:
            ev_gol, dep_gol = beklenen_goller(ev, dep, takimlar)
            karar = pazar_sec(
                ev_gol, dep_gol,
                takimlar[ev]["mac"],
                takimlar[dep]["mac"],
                oranlar=oranlari_al(mac)
            )
        except (ValueError, KeyError, ZeroDivisionError):
            atlanan["Yetersiz veri"] += 1
            continue

        sonuclar.append({
            "tarih": tarih.isoformat(),
            "lig": lig,
            "ev": ev,
            "dep": dep,
            "model": "TIPSTER_PRO_PAZAR_V2",
            "hesaplama_zamani_utc": simdi.isoformat(),
            "baslama_saati_dogrulandi": True,
            "karar": karar["karar"],
            "adaylar": (
    [karar["secim"]] + karar.get("alternatifler", [])
    if karar.get("secim")
    else karar.get("adaylar", karar.get("en_yuksek_olasiliklar", []))
),
            "neden": karar.get("neden", ""),
            "oran_kaynagi": "Football-Data / Bet365" if oranlari_al(mac) else None
        })

    CIKTI.write_text(
        json.dumps(sonuclar, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("TIPSTER PRO COKLU PAZAR V2")
    print("Fikstur:", len(fikstur))
    print("Incelenen:", len(sonuclar))
    print("Atlanan:", dict(atlanan))

    for mac in sonuclar[:20]:
        print(
            mac["tarih"], mac["ev"], "-", mac["dep"],
            "|", mac["karar"],
            "|", mac["adaylar"][:2]
        )

if __name__ == "__main__":
    calistir()
