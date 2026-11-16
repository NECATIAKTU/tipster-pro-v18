
import csv
import io
from urllib.request import Request, urlopen

SEZON = "2627"
LIG = "D1"

adres = (
    f"https://www.football-data.co.uk/"
    f"mmz4281/{SEZON}/{LIG}.csv"
)

print("TIPSTER PRO - VERI KONTROL")
print("Kaynak:", adres)

istek = Request(
    adres,
    headers={"User-Agent": "Mozilla/5.0"}
)

with urlopen(istek, timeout=30) as cevap:
    metin = cevap.read().decode(
        "utf-8-sig", errors="replace"
    )

satirlar = list(csv.DictReader(io.StringIO(metin)))

print("Toplam satir:", len(satirlar))

tamamlanan = 0
for mac in satirlar:
    if mac.get("FTHG") and mac.get("FTAG"):
        tamamlanan += 1

    ev = (mac.get("HomeTeam") or "").lower()
    dep = (mac.get("AwayTeam") or "").lower()

    if "frankfurt" in ev and (
        "koln" in dep or "cologne" in dep
    ):
        print("FRANKFURT MACI BULUNDU")
        print("Tarih:", mac.get("Date"))
        print("Ev:", mac.get("HomeTeam"))
        print("Dep:", mac.get("AwayTeam"))
        print("Skor:", mac.get("FTHG"), "-", mac.get("FTAG"))

print("Tamamlanan mac:", tamamlanan)
print("KONTROL BITTI")
print("\nSON 5 KAYIT:")
for mac in satirlar[-5:]:
    print(
        mac.get("Date"),
        mac.get("HomeTeam"),
        "-",
        mac.get("AwayTeam"),
        "Skor:",
        mac.get("FTHG"),
        "-",
        mac.get("FTAG")
    )
