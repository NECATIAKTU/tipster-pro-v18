
import csv
import io
from urllib.request import Request, urlopen

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
    "G1": "Yunanistan"
}

SEZON = "2627"

for kod, lig in LIGLER.items():
    adres = (
        "https://www.football-data.co.uk/"
        f"mmz4281/{SEZON}/{kod}.csv"
    )

    try:
        istek = Request(
            adres,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urlopen(istek, timeout=20) as cevap:
            ham = cevap.read()

        metin = ham.decode("utf-8-sig", errors="replace")
        maclar = list(csv.DictReader(io.StringIO(metin)))

        tamamlanan = sum(
            1 for mac in maclar
            if (mac.get("FTHG") or "").strip()
            and (mac.get("FTAG") or "").strip()
        )

        print(
            kod, lig,
            "| Gecmis mac:", tamamlanan
        )

    except Exception as hata:
        print(kod, lig, "| VERI ALINAMADI:", hata)

from japonya_veri import japonya_verisi_al
print("Japonya veri modülü hazır:", callable(japonya_verisi_al))
