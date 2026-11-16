
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

KAYNAK = Path("gercek_sonuc_raporu.json")
CIKTI = Path("gunluk_sonuc_raporu.txt")
JSON_CIKTI = Path("gunluk_sonuc_raporu.json")

DURUMLAR = [
    "DOGRU",
    "YANLIS",
    "RISKLI",
    "ESLESMEDI",
    "KAYNAK_HATASI",
    "BEKLIYOR",
]

def tarih_oku(deger):
    if not deger:
        return None
    try:
        tarih = datetime.fromisoformat(
            str(deger).replace("Z", "+00:00")
        )
        if tarih.tzinfo is None:
            tarih = tarih.replace(tzinfo=timezone.utc)
        return tarih.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def ozet(kayitlar):
    sayac = Counter(
        k.get("durum", "BILINMIYOR")
        for k in kayitlar
    )
    dogru = sayac["DOGRU"]
    yanlis = sayac["YANLIS"]
    tamamlanan = dogru + yanlis

    return {
        "toplam": len(kayitlar),
        "dogru": dogru,
        "yanlis": yanlis,
        "riskli": sayac["RISKLI"],
        "eslesmeyen": sayac["ESLESMEDI"],
        "kaynak_hatasi": sayac["KAYNAK_HATASI"],
        "bekleyen": sayac["BEKLIYOR"],
        "basari_yuzdesi": (
            round(100 * dogru / tamamlanan, 2)
            if tamamlanan else None
        ),
    }

def main():
    if not KAYNAK.exists():
        raise FileNotFoundError(
            "Once gercek_sonuc_kontrol_v1.py calismali"
        )

    kayitlar = json.loads(
        KAYNAK.read_text(encoding="utf-8")
    )

    if not isinstance(kayitlar, list):
        raise ValueError("Rapor liste olmali")

    simdi = datetime.now(timezone.utc)
    bugun = simdi.date().isoformat()

    gunler = defaultdict(list)

    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            continue

        tarih = tarih_oku(kayit.get("tarih"))
        if tarih is None:
            continue

        gunler[tarih.date().isoformat()].append(
            kayit
        )

    genel = ozet(kayitlar)

    gunluk = {
        gun: ozet(maclar)
        for gun, maclar in sorted(gunler.items())
    }

    bugunku = gunluk.get(bugun, ozet([]))

    sorunlar = [
        {
            "tarih": k.get("tarih"),
            "lig": k.get("lig"),
            "ev_sahibi": k.get("ev_sahibi"),
            "deplasman": k.get("deplasman"),
            "durum": k.get("durum"),
            "neden": k.get("neden", ""),
        }
        for k in kayitlar
        if isinstance(k, dict)
        and k.get("durum") in (
            "ESLESMEDI", "KAYNAK_HATASI"
        )
    ]

    veri = {
        "olusturulma_utc": simdi.isoformat(),
        "bugun_utc": bugun,
        "bugun": bugunku,
        "genel": genel,
        "gunluk": gunluk,
        "cozulemeyenler": sorunlar,
    }

    JSON_CIKTI.write_text(
        json.dumps(
            veri, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    satirlar = [
        "TIPSTER PRO - GUNLUK SONUC RAPORU",
        f"Olusturulma UTC: {simdi.isoformat()}",
        "",
        f"BUGUN: {bugun}",
        f"TOPLAM: {bugunku['toplam']}",
        f"DOGRU: {bugunku['dogru']}",
        f"YANLIS: {bugunku['yanlis']}",
        f"RISKLI: {bugunku['riskli']}",
        f"ESLESMEYEN: {bugunku['eslesmeyen']}",
        f"BEKLEYEN: {bugunku['bekleyen']}",
        f"BASARI: {bugunku['basari_yuzdesi']}",
        "",
        "GENEL TOPLAM",
        f"TOPLAM: {genel['toplam']}",
        f"DOGRU: {genel['dogru']}",
        f"YANLIS: {genel['yanlis']}",
        f"RISKLI: {genel['riskli']}",
        f"ESLESMEYEN: {genel['eslesmeyen']}",
        f"KAYNAK_HATASI: {genel['kaynak_hatasi']}",
        f"BEKLEYEN: {genel['bekleyen']}",
        f"BASARI: {genel['basari_yuzdesi']}",
        "",
        "GUNLUK GECMIS",
    ]

    for gun, bilgi in sorted(
        gunluk.items(), reverse=True
    ):
        satirlar.append(
            f"{gun} | "
            f"D:{bilgi['dogru']} "
            f"Y:{bilgi['yanlis']} "
            f"R:{bilgi['riskli']} "
            f"E:{bilgi['eslesmeyen']} "
            f"B:{bilgi['bekleyen']} "
            f"Basari:{bilgi['basari_yuzdesi']}"
        )

    satirlar.extend([
        "",
        "COZULEMEYEN MACLAR",
    ])

    for k in sorunlar:
        satirlar.append(
            f"{k['tarih']} | {k['lig']} | "
            f"{k['ev_sahibi']} - "
            f"{k['deplasman']} | "
            f"{k['durum']} | {k['neden']}"
        )

    CIKTI.write_text(
        "\n".join(satirlar) + "\n",
        encoding="utf-8"
    )

    print("GUNLUK RAPOR:", CIKTI)
    print("JSON RAPOR:", JSON_CIKTI)
    print("BUGUN:", bugun)
    print("BUGUN DOGRU:", bugunku["dogru"])
    print("BUGUN YANLIS:", bugunku["yanlis"])
    print("GENEL DOGRU:", genel["dogru"])
    print("GENEL YANLIS:", genel["yanlis"])
    print("ESLESMEYEN:", genel["eslesmeyen"])

if __name__ == "__main__":
    main()
