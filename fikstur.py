
import csv
import io
import json
from pathlib import Path
from datetime import datetime, date
from urllib.request import Request, urlopen

URL = "https://www.football-data.co.uk/fixtures.csv"

def fiksturu_tara():
    istek = Request(URL, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(istek, timeout=30) as cevap:
        veri = cevap.read().decode("utf-8-sig")

    maclar = list(csv.DictReader(io.StringIO(veri)))
    gelecek = []
    print("Kaynak kayit sayisi:", len(maclar))
    print("Ilk 3 macin tarihleri:", [m.get("Date") for m in maclar[:3]])

    print("En son mac tarihi:", max((m.get("Date", "") for m in maclar), default="YOK"))
    print("Bugunun tarihi:", date.today().strftime("%d/%m/%Y"))
  
    



    for mac in maclar:
        try:
            tarih = datetime.strptime(
                mac["Date"], "%d/%m/%Y"
            ).date()
        except (ValueError, KeyError, TypeError):
            continue

        if tarih >= date.today():
            gelecek.append(mac)

    print("Gelecek mac sayisi:", len(gelecek))

    dosya = Path("kayitlar.json")
    kayitlar = json.loads(dosya.read_text(encoding="utf-8"))

    eski_maclar = kayitlar["maclar"]
    mevcut = {
        (m["Date"], m["Div"], m["HomeTeam"], m["AwayTeam"])
        for m in eski_maclar
    }

    yeni = 0
    for mac in gelecek:
        anahtar = (
            mac.get("Date", ""),
            mac.get("Div", ""),
            mac.get("HomeTeam", ""),
            mac.get("AwayTeam", "")
        )
        if anahtar not in mevcut:
            eski_maclar.append({
                "Date": anahtar[0],
                "Time": mac.get("Time", ""),
                "Div": anahtar[1],
                "HomeTeam": anahtar[2],
                "AwayTeam": anahtar[3]
            })
            mevcut.add(anahtar)
            yeni += 1

    dosya.write_text(
        json.dumps(kayitlar, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("Yeni kaydedilen mac:", yeni)

    
    for mac in gelecek[:20]:
        print(
            mac.get("Date", ""),
            mac.get("Time", ""),
            mac.get("Div", ""),
            mac.get("HomeTeam", ""),
            "-",
            mac.get("AwayTeam", "")
        )

        
            
            
            
            
        

if __name__ == "__main__":
    fiksturu_tara()
