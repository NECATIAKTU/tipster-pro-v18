
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

KAYNAK = Path("tahminler.json")
CIKTI = Path("gercek_sonuc_raporu.json")
ESLESMEYEN = Path("eslesmeyen_sonuclar.json")

LIGLER = {
    "Turkiye Super Lig": "tur.1",
    "Ingiltere Premier League": "eng.1",
    "Ingiltere Championship": "eng.2",
    "Ingiltere League One": "eng.3",
    "Ingiltere League Two": "eng.4",
    "Iskocya Premier": "sco.1",
    "Iskocya Premiership": "sco.1",
    "Almanya Bundesliga": "ger.1",
    "Almanya Bundesliga 2": "ger.2",
    "Ispanya La Liga": "esp.1",
    "Italya Serie A": "ita.1",
    "Fransa Ligue 1": "fra.1",
    "Hollanda Eredivisie": "ned.1",
    "Belcika Pro League": "bel.1",
    "Norvec Eliteserien": "nor.1",
    "Portekiz Primeira Liga": "por.1",
    "Isvicre Super League": "sui.1",
}

TAKIM_ADLARI = {
    "manchestercity": "mancity",
    "manchesterunited": "manunited",
    "brightonandhovealbion": "brighton",
    "brightonhovealbion": "brighton",
    "tottenhamhotspur": "tottenham",
    "wolverhamptonwanderers": "wolves",
    "afcbournemouth": "bournemouth",
    "nottinghamforest": "nottmforest",
    "ipswichtown": "ipswich",
    "newcastleunited": "newcastle",
    "westhamunited": "westham",
    "leedsunited": "leeds",
    "leicestercity": "leicester",
    "coventrycity": "coventry",
    "swanseacity": "swansea",
    "blackburnrovers": "blackburn",
    "bradfordcity": "bradford",
    "huddersfieldtown": "huddersfield",
    "cambridgeunited": "cambridge",
    "plymouthargyle": "plymouth",
    "oxfordunited": "oxford",
    "atleticomadrid": "atletico",
    "atleticodemadrid": "atletico",
    "athleticclub": "athleticbilbao",
    "borussiamonchengladbach": "monchengladbach",
    "borussiamgladbach": "monchengladbach",
    "vfbstuttgart": "stuttgart",
    "bayer04leverkusen": "leverkusen",
    "parissaintgermain": "psg",
    "parissg": "psg",
    "kvmechelen": "mechelen",
    "kvkortrijk": "kortrijk",
    "racinggenk": "genk",
    "krcgenk": "genk",
    "bodo/glimt": "bodoglimt",
    "bodoeglimt": "bodoglimt",
    "valerenga": "valerenga",
    "vikingfk": "viking",
    "tromso": "tromso",
    "stjohnstone": "stjohnstone",
    "saintjohnstone": "stjohnstone",
    "stm irren": "stmirren",
    "saintmirren": "stmirren",
    "dundeeunitedfc": "dundeeunited",
    "hibernianfc": "hibernian",
    "celticfc": "celtic",
    "rangersfc": "rangers",
    "aberdeenfc": "aberdeen",
    "falkirkfc": "falkirk",
    "kilmarnockfc": "kilmarnock",
    "motherwellfc": "motherwell",
}

def temizle(metin):
    metin = unicodedata.normalize(
        "NFKD", str(metin).casefold()
    )
    metin = "".join(
        h for h in metin
        if not unicodedata.combining(h)
    )
    metin = re.sub(r"[^a-z0-9]", "", metin)
    return metin

TAKIM_ADLARI = {
    temizle(k): temizle(v)
    for k, v in TAKIM_ADLARI.items()
}

def takim_anahtari(ad):
    ad = temizle(ad)
    return TAKIM_ADLARI.get(ad, ad)

def isim_eslesiyor(a, b):
    a = takim_anahtari(a)
    b = takim_anahtari(b)

    if not a or not b:
        return False

    if a == b:
        return True

    # Yalnizca cok yuksek benzerlikte eslestir.
    if min(len(a), len(b)) < 8:
        return False

    return (
        SequenceMatcher(None, a, b).ratio()
        >= 0.96
    )

def skorlar(lig, tarih):
    adres = (
        "https://site.api.espn.com/apis/site/v2/"
        f"sports/soccer/{lig}/scoreboard?dates={tarih}"
    )
    istek = urllib.request.Request(
        adres,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(
        istek, timeout=20
    ) as cevap:
        veri = json.load(cevap)
    return veri.get("events", [])

def sonuc_bul(kayit, etkinlikler):
    bulunanlar = []

    for etkinlik in etkinlikler:
        durum = etkinlik.get(
            "status", {}
        ).get("type", {})

        if not durum.get("completed", False):
            continue

        maclar = etkinlik.get("competitions", [])
        if not maclar:
            continue

        takimlar = maclar[0].get(
            "competitors", []
        )
        if len(takimlar) != 2:
            continue

        taraflar = {
            t.get("homeAway"): t
            for t in takimlar
        }

        ev = taraflar.get("home")
        dep = taraflar.get("away")

        if not ev or not dep:
            continue

        ev_adi = ev.get(
            "team", {}
        ).get("displayName", "")
        dep_adi = dep.get(
            "team", {}
        ).get("displayName", "")

        if not (
            isim_eslesiyor(
                kayit["ev_sahibi"], ev_adi
            )
            and isim_eslesiyor(
                kayit["deplasman"], dep_adi
            )
        ):
            continue

        try:
            ev_skor = int(ev["score"])
            dep_skor = int(dep["score"])
        except (KeyError, TypeError, ValueError):
            continue

        bulunanlar.append(
            (ev_skor, dep_skor, ev_adi, dep_adi)
        )

    # Birden fazla eslesme varsa otomatik karar verme.
    if len(bulunanlar) == 1:
        return bulunanlar[0]

    return None

def karar(olasiliklar):
    if not isinstance(olasiliklar, dict):
        return "RISKLI", None

    for alan, esik, etiket, gol in [
        ("3.5_ust", 65, "3.5 UST", 4),
        ("2.5_ust", 65, "2.5 UST", 3),
        ("1.5_ust", 75, "1.5 UST", 2),
    ]:
        try:
            if float(olasiliklar.get(alan, 0)) >= esik:
                return etiket, gol
        except (TypeError, ValueError):
            pass

    return "RISKLI", None

def tarih_oku(deger):
    tarih = datetime.fromisoformat(
        str(deger).replace("Z", "+00:00")
    )
    if tarih.tzinfo is None:
        tarih = tarih.replace(tzinfo=timezone.utc)
    return tarih.astimezone(timezone.utc)

def main():
    if not KAYNAK.exists():
        raise FileNotFoundError(
            "tahminler.json bulunamadi"
        )

    kayitlar = json.loads(
        KAYNAK.read_text(encoding="utf-8")
    )

    if not isinstance(kayitlar, list):
        raise ValueError(
            "tahminler.json liste olmali"
        )

    simdi = datetime.now(timezone.utc)
    onbellek = {}
    rapor = []
    sorunlar = []
    sayac = Counter()

    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            continue

        try:
            tarih = tarih_oku(kayit["tarih"])
        except (KeyError, TypeError, ValueError):
            sayac["GECERSIZ_TARIH"] += 1
            sorunlar.append({
                "kayit": kayit,
                "neden": "GECERSIZ_TARIH"
            })
            continue

        secim, gereken = karar(
            kayit.get("tahmin", {})
        )

        satir = {
            "tarih": kayit["tarih"],
            "lig": kayit.get("lig"),
            "ev_sahibi": kayit.get("ev_sahibi"),
            "deplasman": kayit.get("deplasman"),
            "tahmin": secim,
            "hesaplama_zamani": kayit.get(
                "hesaplama_zamani"
            ),
        }

        if tarih > simdi:
            satir["durum"] = "BEKLIYOR"

        elif simdi < tarih + timedelta(hours=3):
            # Mac bitmis olmayabilir.
            satir["durum"] = "BEKLIYOR"

        else:
            lig_kodu = LIGLER.get(
                kayit.get("lig")
            )

            if not lig_kodu:
                satir["durum"] = "ESLESMEDI"
                satir["neden"] = "LIG_KODU_YOK"
            else:
                # UTC gece sinirindaki maclar icin
                # komsu tarihleri de kontrol et.
                etkinlikler = []
                kaynak_hatasi = False

                for fark in (-1, 0, 1):
                    gun = (
                        tarih + timedelta(days=fark)
                    ).strftime("%Y%m%d")
                    anahtar = (lig_kodu, gun)

                    if anahtar not in onbellek:
                        try:
                            onbellek[anahtar] = skorlar(
                                lig_kodu, gun
                            )
                        except Exception as hata:
                            print(
                                "KAYNAK HATASI:",
                                anahtar, hata
                            )
                            onbellek[anahtar] = None

                    veri = onbellek[anahtar]
                    if veri is None:
                        kaynak_hatasi = True
                    else:
                        etkinlikler.extend(veri)

                # ESPN komsu gunlerde ayni maci
                # tekrar verebilir: ID ile tekillestir.
                benzersiz = {}
                for e in etkinlikler:
                    kimlik = e.get("id")
                    if kimlik is not None:
                        benzersiz[str(kimlik)] = e

                skor = sonuc_bul(
                    kayit, list(benzersiz.values())
                )

                if skor is None:
                    if kaynak_hatasi:
                        satir["durum"] = "KAYNAK_HATASI"
                    else:
                        satir["durum"] = "ESLESMEDI"
                        satir["neden"] = (
                            "MAC_ESLESMEDI_VEYA_SONUC_YOK"
                        )
                else:
                    satir["skor"] = (
                        f"{skor[0]}-{skor[1]}"
                    )
                    satir["eslesen_ev"] = skor[2]
                    satir["eslesen_dep"] = skor[3]

                    if gereken is None:
                        satir["durum"] = "RISKLI"
                    elif skor[0] + skor[1] >= gereken:
                        satir["durum"] = "DOGRU"
                    else:
                        satir["durum"] = "YANLIS"

        durum = satir["durum"]
        sayac[durum] += 1
        rapor.append(satir)

        if durum in (
            "ESLESMEDI", "KAYNAK_HATASI"
        ):
            sorunlar.append(satir)

    CIKTI.write_text(
        json.dumps(
            rapor, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    ESLESMEYEN.write_text(
        json.dumps(
            sorunlar, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    dogru = sayac["DOGRU"]
    yanlis = sayac["YANLIS"]

    print("TOPLAM:", len(rapor))
    print("DOGRU:", dogru)
    print("YANLIS:", yanlis)
    print("RISKLI:", sayac["RISKLI"])
    print("ESLESMEYEN:", sayac["ESLESMEDI"])
    print("KAYNAK_HATASI:", sayac["KAYNAK_HATASI"])
    print("BEKLEYEN:", sayac["BEKLIYOR"])
    print(
        "BASARI:",
        round(
            100 * dogru / (dogru + yanlis), 2
        )
        if dogru + yanlis
        else "HENUZ YOK"
    )
    print("RAPOR:", CIKTI)
    print("SORUN RAPORU:", ESLESMEYEN)

if __name__ == "__main__":
    main()
