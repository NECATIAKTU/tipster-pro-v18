import csv
import hashlib
from datetime import datetime, timezone
import io
import time
from collections import defaultdict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from gol_modeli import poisson_ust


SOURCE_TRACE = {}

SEZON = "2627"
ONCEKI_SEZON = "2526"

MIN_MAC = 5
ESKI_SEZON_ESDEGER_MAC = 8

LIGLER = {
    "E0": "Ingiltere Premier League",
    "E1": "Ingiltere Championship",
    "E2": "Ingiltere League One",
    "E3": "Ingiltere League Two",
    "EC": "Ingiltere National League",
    "SC0": "Iskocya Premiership",
    "D1": "Almanya Bundesliga",
    "D2": "Almanya Bundesliga 2",
    "SP1": "Ispanya La Liga",
    "SP2": "Ispanya La Liga 2",
    "I1": "Italya Serie A",
    "I2": "Italya Serie B",
    "F1": "Fransa Ligue 1",
    "F2": "Fransa Ligue 2",
    "N1": "Hollanda Eredivisie",
    "B1": "Belcika",
    "P1": "Portekiz",
    "T1": "Turkiye Super Lig",
    "G1": "Yunanistan",
    "SC1": "İskoçya Championship",
    "SC2": "İskoçya League One",
    "J1": "Japonya J1 League",
    "NOR1": "Norvec Eliteserien",
}


def lig_verisi_al(kod, sezon=SEZON):
    if kod == "NOR1":
        return norvec_verisi_al(sezon)
    adres = (
        f"https://www.football-data.co.uk/"
        f"mmz4281/{sezon}/{kod}.csv"
    )

    istek = Request(
        adres,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    for deneme in range(3):
        try:
            with urlopen(istek, timeout=30) as cevap:
                raw = cevap.read()
                metin = raw.decode(
                    "utf-8-sig",
                    errors="replace"
                )
                SOURCE_TRACE[(kod, sezon)] = {
                    "url": adres,
                    "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                }
            break

        except (TimeoutError, URLError):
            if deneme == 2:
                raise

            time.sleep(3 * (deneme + 1))

    takimlar = defaultdict(
        lambda: {
            "mac": 0,
            "attigi": 0,
            "yedigi": 0,
        }
    )

    for mac in csv.DictReader(io.StringIO(metin)):
        ev = (mac.get("HomeTeam") or "").strip()
        dep = (mac.get("AwayTeam") or "").strip()

        try:
            ev_gol = int(mac["FTHG"])
            dep_gol = int(mac["FTAG"])

        except (KeyError, ValueError, TypeError):
            continue

        if not ev or not dep:
            continue

        takimlar[ev]["mac"] += 1
        takimlar[ev]["attigi"] += ev_gol
        takimlar[ev]["yedigi"] += dep_gol

        takimlar[dep]["mac"] += 1
        takimlar[dep]["attigi"] += dep_gol
        takimlar[dep]["yedigi"] += ev_gol

    return dict(takimlar)


def tum_ligleri_al():
    """
    Her lig icin takim istatistiklerini toplar.

    Gecmis sezon verisi sadece takim mevcut
    sezonda ayni ligde bulunuyorsa eklenir.

    Eski sezon agirligi en fazla 8 mac olur.
    """

    lig_verileri = {}

    for kod, ad in LIGLER.items():
        try:
            guncel = lig_verisi_al(kod, SEZON)

            if not guncel:
                print(
                    kod,
                    "| GUNCEL VERI BOS, LIG ATLANDI"
                )
                continue

            try:
                # Norvec kaynagi yalnizca 2026 sezonunu destekliyor.
                # Ayni maclarin gecmis sezon olarak ikinci kez sayilmasini engelle.
                onceki = {} if kod == "NOR1" else lig_verisi_al(
                    kod,
                    ONCEKI_SEZON
                )

            except (
                HTTPError,
                URLError,
                TimeoutError,
                ValueError,
            ) as hata:
                print(
                    kod,
                    "| ONCEKI SEZON ALINAMADI:",
                    str(hata)
                )
                onceki = {}

            desteklenen = 0

            for takim, veri in guncel.items():
                veri["kaynak_sezon"] = SEZON

                eski = onceki.get(takim)

                if eski is None:
                    for eski_ad, eski_veri in onceki.items():
                        if (
                            eski_ad.casefold().strip()
                            == takim.casefold().strip()
                        ):
                            eski = eski_veri
                            break

                if not eski or eski["mac"] < MIN_MAC:
                    continue

                agirlik = min(
                    ESKI_SEZON_ESDEGER_MAC,
                    eski["mac"]
                )

                veri["eski_mac_esdeger"] = agirlik

                veri["eski_attigi_esdeger"] = (
                    eski["attigi"] / eski["mac"]
                ) * agirlik

                veri["eski_yedigi_esdeger"] = (
                    eski["yedigi"] / eski["mac"]
                ) * agirlik

                veri["kaynak_sezon"] = (
                    SEZON + "+" + ONCEKI_SEZON
                )

                desteklenen += 1

            lig_verileri[kod] = guncel

            print(
                kod,
                ad,
                "| Takim:",
                len(guncel),
                "| Gecmis sezon destekli:",
                desteklenen
            )

        except Exception as hata:
            print(
                kod,
                "| VERI HATASI:",
                str(hata)
            )

    return lig_verileri


def _ortalamalar(veri):
    guncel_mac = veri["mac"]

    eski_mac = veri.get(
        "eski_mac_esdeger",
        0
    )

    toplam_mac = guncel_mac + eski_mac

    if guncel_mac < 0 or toplam_mac < MIN_MAC:
        raise ValueError(
            "Yetersiz mac verisi"
        )

    atilan = (
        veri["attigi"]
        + veri.get("eski_attigi_esdeger", 0)
    )

    yenilen = (
        veri["yedigi"]
        + veri.get("eski_yedigi_esdeger", 0)
    )

    return (
        atilan / toplam_mac,
        yenilen / toplam_mac
    )


def mac_analizi(kod, ev, dep, lig_verileri):
    if kod not in lig_verileri:
        raise ValueError(
            "Lig verisi bulunamadi"
        )

    takimlar = lig_verileri[kod]

    if ev not in takimlar or dep not in takimlar:
        raise ValueError(
            "Takim bulunamadi"
        )

    a = takimlar[ev]
    b = takimlar[dep]

    ev_atak, ev_savunma = _ortalamalar(a)
    dep_atak, dep_savunma = _ortalamalar(b)

    toplam = (
        ev_atak
        + dep_savunma
        + dep_atak
        + ev_savunma
    ) / 2

    return {
        "lig": kod,
        "ev": ev,
        "dep": dep,
        "beklenen_gol": round(toplam, 2),
        "1.5_ust": round(
            poisson_ust(toplam, 1) * 100,
            1
        ),
        "2.5_ust": round(
            poisson_ust(toplam, 2) * 100,
            1
        ),
        "3.5_ust": round(
            poisson_ust(toplam, 3) * 100,
            1
        ),
        "veri_kaynagi_ev": a.get(
            "kaynak_sezon",
            SEZON
        ),
        "veri_kaynagi_dep": b.get(
            "kaynak_sezon",
            SEZON
        ),
    }


if __name__ == "__main__":
    print(
        "TIPSTER PRO - COKLU LIG MOTORU"
    )

    veriler = tum_ligleri_al()

    print(
        "Veri alinan lig:",
        len(veriler)
    )

    for kod, takimlar in veriler.items():
        uygun = sorted(
            ad
            for ad, veri in takimlar.items()
            if (
                veri["mac"]
                + veri.get("eski_mac_esdeger", 0)
            ) >= MIN_MAC
        )

        if len(uygun) < 2:
            continue

        ev, dep = uygun[:2]

        sonuc = mac_analizi(
            kod,
            ev,
            dep,
            veriler
        )

        print(
            kod,
            ev,
            "-",
            dep,
            "| 1.5 UST:",
            sonuc["1.5_ust"],
            "| 2.5 UST:",
            sonuc["2.5_ust"],
            "| 3.5 UST:",
            sonuc["3.5_ust"]
            )
        
def norvec_verisi_al(sezon=None):
    # Bu URL 2026 sezonuna sabittir. Baska sezonu 2026 diye dondurme.
    if sezon not in (None, "2627", "2026"):
        raise ValueError("Norvec icin istenen sezon desteklenmiyor: " + str(sezon))
    adres = (
        "https://raw.githubusercontent.com/TopMarx/"
        "eliteserien/refs/heads/main/"
        "data/2026/csv/fixtures.csv"
    )

    istek = Request(
        adres,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(istek, timeout=30) as cevap:
        raw = cevap.read()

    SOURCE_TRACE[("NOR1", "2026")] = {
        "url": adres,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw)
    }

    metin = raw.decode("utf-8-sig")
    takimlar = defaultdict(
        lambda: {"mac": 0, "attigi": 0, "yedigi": 0}
    )

    for mac in csv.DictReader(io.StringIO(metin)):
        if mac.get("finished", "").strip().lower() != "true":
            continue

        tarih = mac.get("kickoff_time", "")
        try:
            baslama = datetime.fromisoformat(
                tarih.replace("Z", "+00:00")
            )
            if baslama.timestamp() > time.time():
                continue

            ev_gol = int(mac["team_h_score"])
            dep_gol = int(mac["team_a_score"])
        except (ValueError, TypeError, KeyError):
            continue

        ev = (mac.get("team_h_name") or "").strip()
        dep = (mac.get("team_a_name") or "").strip()

        if not ev or not dep or ev == dep:
            continue

        takimlar[ev]["mac"] += 1
        takimlar[ev]["attigi"] += ev_gol
        takimlar[ev]["yedigi"] += dep_gol

        takimlar[dep]["mac"] += 1
        takimlar[dep]["attigi"] += dep_gol
        takimlar[dep]["yedigi"] += ev_gol

    return dict(takimlar)
