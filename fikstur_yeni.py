"""TIPSTER PRO - ESPN'den gelecek 30 gunluk fikstur.

Cikti: gelecek_maclar.json. Arsiv dosyalarina dokunmaz.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen

LIGLER = {
    "eng.1": "Ingiltere Premier League", "eng.2": "Ingiltere Championship",
    "eng.3": "Ingiltere League One", "eng.4": "Ingiltere League Two",
    "esp.1": "Ispanya La Liga", "ger.1": "Almanya Bundesliga",
    "ita.1": "Italya Serie A", "fra.1": "Fransa Ligue 1",
    "ned.1": "Hollanda Eredivisie", "por.1": "Portekiz Primeira Liga",
    "sui.1": "Isvicre Super League", "nor.1": "Norvec Eliteserien",
    "tur.1": "Turkiye Super Lig", "tur.2": "Turkiye 1. Lig",
    "sco.1": "Iskocya Premiership", "bel.1": "Belcika Pro League",
    "aut.1": "Avusturya Bundesliga", "den.1": "Danimarka Superliga",
    "swe.1": "Isvec Allsvenskan", "irl.1": "Irlanda Premier Division",
    "usa.1": "ABD MLS", "mex.1": "Meksika Liga MX",
    "bra.1": "Brezilya Serie A", "arg.1": "Arjantin Primera Division",
    "col.1": "Kolombiya Primera A", "jpn.1": "Japonya J1 League",
    "chn.1": "Cin Super League", "aus.1": "Avustralya A-League",
    "rsa.1": "Guney Afrika Premiership",
    "eng.5": "Ingiltere National League",
    "ger.2": "Almanya Bundesliga 2",
    "esp.2": "Ispanya La Liga 2",
    "ita.2": "Italya Serie B",
    "fra.2": "Fransa Ligue 2",
    "sco.2": "Iskocya Championship",
    "sco.3": "Iskocya League One",
    "gre.1": "Yunanistan Super Lig",
    "pol.1": "Polonya Ekstraklasa",
    "pol.2": "Polonya I Liga",
    "uefa.champions": "UEFA Şampiyonlar Ligi",
    "uefa.europa": "UEFA Avrupa Ligi",
    "uefa.europa.conf": "UEFA Konferans Ligi",
}
# Avrupa ust lig adaylarini varsayilan taramaya ekleme: kodlar canli dogrulanana kadar
# mevcut tarama/Actions is yukunu degistirmemek icin opt-in tutulur.
if os.environ.get("TIPSTER_AVRUPA_ADAYLARI", "0") == "1":
    from avrupa_lig_kapsam import eksik_fikstur_ligleri
    for kayit in eksik_fikstur_ligleri():
        LIGLER.setdefault(kayit["espn_adayi"], kayit["ulke"] + " " + kayit["ust_lig"])

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
OUTPUT = "gelecek_maclar.json"
GUN_SAYISI = 30  # Maximum look-ahead; actual scan window configurable below


def getir(league, start, end):
    """GÃ¼nlÃ¼k sorgularla maÃ§larÄ± getir; bir gÃ¼n hata verirse ligi tÃ¼mden dÃ¼ÅÃ¼rme."""
    events = []
    errors = []
    gun = start.date()
    while gun <= end.date():
        params = urlencode({"dates": gun.strftime("%Y%m%d"), "limit": 500})
        req = Request(BASE.format(league=league) + "?" + params,
                      headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(req, timeout=25) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
                raise ValueError("ESPN yaniti beklenen events listesini icermiyor")
            events.extend(payload["events"])
        except Exception as exc:
            errors.append({"lig": league, "gun": gun.isoformat(), "hata": str(exc)})
        gun += timedelta(days=1)
    return events, errors


def main():
    now = datetime.now(timezone.utc)
    london = now.astimezone(ZoneInfo("Europe/London"))
    # Default 7 days, configurable up to 30; do not silently stop next Monday.
    gun = int(os.environ.get("TIPSTER_FIKSTUR_GUN", "7"))
    if not 1 <= gun <= GUN_SAYISI:
        raise ValueError("TIPSTER_FIKSTUR_GUN 1..30 araliginda olmali")
    end = now + timedelta(days=gun)
    
    
    matches = {}
    failed = []
    elenen = {
    "tarih": 0,
    "durum": 0,
    "takim_bilgisi": 0
}
    counts = {}
    for league, label in LIGLER.items():
        events, errors = getir(league, now, end)
        failed.extend(errors)
        added = 0
        for event in events:
            try:
                kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                if not (now < kickoff < end):
                    elenen["tarih"] += 1
                    continue
                    
                status = event.get("status", {}).get("type", {})
                if status.get("completed") or status.get("state") != "pre":
                    elenen["durum"] += 1
                    continue
                competitors = event["competitions"][0]["competitors"]
                home = next(x for x in competitors if x.get("homeAway") == "home")
                away = next(x for x in competitors if x.get("homeAway") == "away")
                home_name = home["team"].get("displayName", "").strip()
                away_name = away["team"].get("displayName", "").strip()
                if not home_name or not away_name:
                    elenen["takim_bilgisi"] += 1
                    continue
                key = f"{league}|{event['id']}"
                if key in matches:
                    continue
                matches[key] = {
                    "id": key, "tarih": kickoff.isoformat(), "lig_kodu": league,
                    "lig": label, "ev_sahibi": home_name, "deplasman": away_name,
                    "kaynak": "ESPN", "durum": "SCHEDULED",
                }
                added += 1
            except (KeyError, IndexError, StopIteration, ValueError, TypeError):
                continue
        counts[league] = added
        print(f"{league}: {added} gelecek mac (API olay sayisi: {len(events)})")
    records = sorted(matches.values(), key=lambda m: (m["tarih"], m["lig_kodu"]))
    output = {
        "olusturulma_utc": now.isoformat(), "aralik_bitis_utc": end.isoformat(),
        "mac_sayisi": len(records), "lig_sayilari": counts,
        "hatalar": failed, "elenen": elenen, "maclar": records,
    }
    tmp = OUTPUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT)
    print(f"TOPLAM GELECEK MAC: {len(records)} | HATALI GUN: {len(failed)}")
    print("ELENEN MACLAR:", elenen)
    if not records:
        print("UYARI: 0 gelecek mac. Veri kaynagi/lig kodlari kontrol edilmeli.")
    print(f"Dosya: {OUTPUT}")


if __name__ == "__main__":
    main()

