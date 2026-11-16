
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ARSIV = PathARSIV = Path("espn_gecmis_v3_yeni_test.json")
TEST_CIKTISI = Path("espn_gecmis_v3_genisletilmis_test.json")

LIGLER = [
    "eng.1", "eng.2", "eng.3", "eng.4",
    "esp.1", "esp.2", "ger.1", "ger.2",
    "ita.1", "ita.2", "fra.1", "fra.2",
    "ned.1", "por.1", "bel.1", "sco.1",
    "tur.1", "gre.1", "aut.1", "den.1",
    "nor.1", "swe.1", "usa.1", "mex.1",
    "bra.1", "arg.1", "col.1", "jpn.1",
    "chn.1"
]

def oku():
    if not ARSIV.exists():
        raise FileNotFoundError(
            "Mevcut arsiv bulunamadi. Islem durduruldu."
        )
    veri = json.loads(ARSIV.read_text(encoding="utf-8"))
    maclar = veri.get("matches")
    if not isinstance(maclar, list):
        raise ValueError("Arsiv bicimi hatali")
    return maclar

def indir(lig, gun):
    tarih = gun.strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/"
        f"soccer/{lig}/scoreboard?dates={tarih}&limit=500"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as cevap:
        return json.load(cevap)

def ayikla(veri, lig):
    sonuc = []
    for etkinlik in veri.get("events", []):
        if not etkinlik.get("status", {}).get("type", {}).get("completed"):
            continue

        yarismalar = etkinlik.get("competitions", [])
        if not yarismalar:
            continue

        takimlar = yarismalar[0].get("competitors", [])
        ev = next(
            (t for t in takimlar if t.get("homeAway") == "home"),
            None
        )
        dep = next(
            (t for t in takimlar if t.get("homeAway") == "away"),
            None
        )
        if not ev or not dep:
            continue

        try:
            ev_gol = int(ev["score"])
            dep_gol = int(dep["score"])
            ev_id = str(ev["team"]["id"])
            dep_id = str(dep["team"]["id"])
        except (KeyError, TypeError, ValueError):
            continue

        sonuc.append({
            "id": str(etkinlik.get("id", "")),
            "lig": lig,
            "tarih": etkinlik.get("date", ""),
            "ev_id": ev_id,
            "dep_id": dep_id,
            "ev": ev["team"].get("displayName", ""),
            "dep": dep["team"].get("displayName", ""),
            "ev_gol": ev_gol,
            "dep_gol": dep_gol
        })
    return sonuc

def anahtar(mac):
    return (
        str(mac.get("lig", "")),
        str(mac.get("id", ""))
    )

def calistir():
    eski = oku()
    kayitlar = {anahtar(m): m for m in eski}
    eski_sayi = len(kayitlar)
    yeni = 0
    hata = 0

    bitis = datetime.now(timezone.utc).date()
    baslangic = bitis - timedelta(days=119)

    for lig in LIGLER:
        lig_yeni = 0
        gun = baslangic

        while gun <= bitis:
            try:
                veri = indir(lig, gun)
                for mac in ayikla(veri, lig):
                    key = anahtar(mac)
                    if key not in kayitlar:
                        kayitlar[key] = mac
                        yeni += 1
                        lig_yeni += 1
            except Exception as e:
                hata += 1
                print("HATA:", lig, gun, str(e)[:120])

            gun += timedelta(days=1)
            time.sleep(0.15)

        print(lig, "| yeni mac:", lig_yeni, flush=True)

    sonuc = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "matches": list(kayitlar.values())
    }

    TEST_CIKTISI.write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("ESKI ARSIV:", eski_sayi)
    print("YENI BENZERSIZ MAC:", yeni)
    print("TOPLAM:", len(kayitlar))
    print("HATALI ISTEK:", hata)
    print("TEST DOSYASI:", TEST_CIKTISI)
    print("ORIJINAL ARSIV DEGISTIRILMEDI")

if __name__ == "__main__":
    calistir()
