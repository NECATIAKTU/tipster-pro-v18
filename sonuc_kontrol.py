
import csv
import io
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ARSIV = "tahmin_arsivi.json"
CIKTI = "dogrulanan_sonuclar.json"

SEZON = "2627"
ESIK = 70.0

LIGLER = [
    "E0", "E1", "E2", "E3", "EC",
    "SC0", "D1", "D2", "SP1", "SP2",
    "I1", "I2", "F1", "F2", "N1",
    "B1", "P1", "T1", "G1"
]


def tarih_cevir(deger):
    return datetime.strptime(
        deger.strip(), "%d/%m/%Y"
    ).date()


def sonuclari_al():
    sonuclar = {}

    for lig in LIGLER:
        adres = (
            "https://www.football-data.co.uk/"
            f"mmz4281/{SEZON}/{lig}.csv"
        )

        try:
            istek = Request(
                adres,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urlopen(istek, timeout=30) as cevap:
                metin = cevap.read().decode(
                    "utf-8-sig", errors="replace"
                )

            for mac in csv.DictReader(io.StringIO(metin)):
                try:
                    tarih = tarih_cevir(mac["Date"])
                    ev = mac["HomeTeam"].strip()
                    dep = mac["AwayTeam"].strip()
                    ev_gol = int(mac["FTHG"])
                    dep_gol = int(mac["FTAG"])
                except (KeyError, ValueError, TypeError, AttributeError):
                    continue

                kimlik = (
                    lig, tarih.isoformat(), ev, dep
                )

                sonuclar[kimlik] = {
                    "ev_gol": ev_gol,
                    "dep_gol": dep_gol,
                    "toplam_gol": ev_gol + dep_gol
                }

        except Exception as hata:
            print("Lig okunamadi:", lig, hata)
    print("LIG SONUC KONTROLU")
    for lig_kodu in LIGLER:
        lig_tarihleri = [
            kimlik[1]
            for kimlik in sonuclar
            if kimlik[0] == lig_kodu
        ]
        if lig_tarihleri:
            print(
                lig_kodu,
                "| Mac:", len(lig_tarihleri),
                "| Son tarih:", max(lig_tarihleri)
            )
        else:
            print(lig_kodu, "| Sonuc bulunamadi")
    if sonuclar:
        son_tarih = max(kimlik[1] for kimlik in sonuclar)
        print("SONUC VERISI SON TARIH:", son_tarih)
    else:
        print("UYARI: Hicbir mac sonucu alinamadi.")

    return sonuclar


def kontrol_et():
    with open(ARSIV, "r", encoding="utf-8") as f:
        tahminler = json.load(f)

    sonuclar = sonuclari_al()
    rapor = []
    sayac = {
        "bekleyen": 0,
        "eslesmeyen": 0,
        "dogrulanan": 0,
        "zaman_belirsiz": 0,
        "zaman_sonrasi": 0
    }

    for tahmin in tahminler:
        yeni = dict(tahmin)

        try:
            tarih = tarih_cevir(tahmin["tarih"])
            kimlik = (
                tahmin["lig"],
                tarih.isoformat(),
                tahmin["ev"],
                tahmin["dep"]
            )
        except (KeyError, ValueError, TypeError):
            yeni["durum"] = "ESLESMEYEN"
            sayac["eslesmeyen"] += 1
            rapor.append(yeni)
            continue

        sonuc = sonuclar.get(kimlik)

        if sonuc is None:
            yeni["durum"] = "BEKLIYOR"
            sayac["bekleyen"] += 1
            rapor.append(yeni)
            continue

        yeni.update(sonuc)
        yeni["durum"] = "DOGRULANDI"
        sayac["dogrulanan"] += 1

        
        # Tahminin mac baslamadan once yapildigini kontrol et
        hesaplama = tahmin.get("hesaplama_zamani_utc")
        baslangic = tahmin.get("mac_baslangic_utc")

        def utc_cevir(deger):
            if not isinstance(deger, str) or not deger.strip():
                return None
            try:
                dt = datetime.fromisoformat(
                    deger.strip().replace("Z", "+00:00")
                )
                if dt.tzinfo is None:
                    return None
                return dt.astimezone(timezone.utc)
            except ValueError:
                return None

        hesaplama_dt = utc_cevir(hesaplama)
        baslangic_dt = utc_cevir(baslangic)

        if hesaplama_dt is None or baslangic_dt is None:
            yeni["mac_oncesi_dogrulama"] = "BELIRSIZ"
            sayac["zaman_belirsiz"] += 1
        elif hesaplama_dt >= baslangic_dt:
            yeni["mac_oncesi_dogrulama"] = "GEC_TAHMIN"
            sayac["zaman_sonrasi"] += 1
        else:
            yeni["mac_oncesi_dogrulama"] = "DOGRULANDI"


        for sinir in (1.5, 2.5, 3.5):
            alan = f"{sinir}_ust"
            yuzde = tahmin.get(alan)

            if not isinstance(yuzde, (int, float)):
                yeni[f"{alan}_karar"] = "VERI_YOK"
                continue

            karar = "UST" if yuzde >= ESIK else "PAS"
            gercek = sonuc["toplam_gol"] > sinir

            yeni[f"{alan}_karar"] = karar
            yeni[f"{alan}_gerceklesti"] = gercek

            if karar == "UST":
                yeni[f"{alan}_sonuc"] = (
                    "DOGRU" if gercek else "YANLIS"
                )
            else:
                yeni[f"{alan}_sonuc"] = "PAS"

        rapor.append(yeni)

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(
            rapor, f,
            ensure_ascii=False,
            indent=2
        )

    print("TIPSTER PRO - SONUC KONTROL")
    print("Toplam arsiv:", len(tahminler))

    for alan, adet in sayac.items():
        print(alan, ":", adet)

    for alan in ("1.5_ust", "2.5_ust", "3.5_ust"):
        dogru = sum(
            1 for x in rapor
            if x.get(f"{alan}_sonuc") == "DOGRU"
        )
        yanlis = sum(
            1 for x in rapor
            if x.get(f"{alan}_sonuc") == "YANLIS"
        )
        toplam = dogru + yanlis

        print(
            alan,
            "| DOGRU:", dogru,
            "| YANLIS:", yanlis,
            "| ORAN:",
            round(dogru / toplam * 100, 1)
            if toplam else "HENUZ YOK"
        )

    print(
        "UYARI: Bu oranlar mac oncesi "
        "dogrulanmis resmi basari orani degildir."
    )


if __name__ == "__main__":
    kontrol_et()
