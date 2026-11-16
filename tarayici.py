

import csv
import io
from datetime import datetime, timezone
from urllib.request import Request, urlopen

KAYNAK = (
    "https://www.football-data.co.uk/"
    "mmz4281/2627/E0.csv"
)

def maclari_tara():
    print("TIPSTER PRO - VERI TARAMA TESTI")
    print("Kontrol:", datetime.now(timezone.utc).isoformat())
    print("Lig: Ingiltere Premier League")

    istek = Request(
        KAYNAK,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(istek, timeout=30) as cevap:
        veri = cevap.read()

    metin = veri.decode("utf-8-sig", errors="replace")
    satirlar = list(csv.DictReader(io.StringIO(metin)))

    maclar = [
        mac for mac in satirlar
        if mac.get("HomeTeam") and mac.get("AwayTeam")
    ]

    oynanan = [
        mac for mac in maclar
        if mac.get("FTHG") and mac.get("FTAG")
    ]

    print("Toplam kayit:", len(maclar))
    print("Sonucu bulunan mac:", len(oynanan))

    for mac in maclar[-5:]:
        print(
            mac.get("Date", ""),
            mac["HomeTeam"],
            "-",
            mac["AwayTeam"],
            mac.get("FTHG", "?"),
            ":",
            mac.get("FTAG", "?")
        )

    gelecek = [
        mac for mac in maclar
        if mac.get("FTHG", "") == ""
        and mac.get("FTAG", "") == ""
    ]

    print("Sonucu bos mac:", len(gelecek))

    for mac in gelecek[:10]:
        print(
            mac.get("Date", ""),
            mac["HomeTeam"],
            "-",
            mac["AwayTeam"]
        )
  
    if not maclar:
        raise RuntimeError("Kaynaktan mac verisi alinamadi.")

if __name__ == "__main__":
    maclari_tara() 
