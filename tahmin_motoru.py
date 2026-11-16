
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from ek_lig_verileri import gecmis_maclari_al
from isvicre_test import isvicre_verisi_al
from coklu_lig_motoru import lig_verisi_al, tum_ligleri_al
from gol_modeli import mac_analizi
from gercek_tahmin_kayit import tahmin_kaydet
from lig_uyumluluk import ESLESTIRMELER, rapor as lig_uyumluluk_raporu

FIKSTUR = Path("gelecek_maclar.json")
KAYIT_DOSYASI = Path("tahminler.json")
ESLESME_RAPORU = Path("eslesmeyen_takimlar.json")

LIGLER = dict(ESLESTIRMELER)

TAKIM_ESLESTIRME = {
    "E0": {
        "ipswichtown": "Ipswich",
        "nottinghamforest": "Nott'm Forest",
        "manchestercity": "Man City",
        "manchesterunited": "Man United",
        "chelsea": "Chelsea",
        "afcbournemouth": "Bournemouth",
        "hullcity": "Hull",
    },
    "E1": {
        "boltonwanderers": "Bolton",
        "charltonathletic": "Charlton",
        "norwichcity": "Norwich",
        "derbycounty": "Derby",
        "prestonnorthend": "Preston",
    },
    "D1": {
        "vfbstuttgart": "Stuttgart",
        "borussiamonchengladbach": "M'gladbach",
        "fcaugsburg": "Augsburg",
        "1fcunionberlin": "Union Berlin",
        "fccologne": "FC Koln",
        "scpaderborn07": "Paderborn",
        "svelfersberg": "Elversberg",
        "bayerleverkusen": "Leverkusen",
        "werderbremen": "Werder Bremen",
        "tsghoffenheim": "Hoffenheim",
        "scfreiburg": "Freiburg",
    },
    "SP1": {
        "athleticclub": "Ath Bilbao",
        "rayovallecano": "Vallecano",
    },
    "B1": {
        "kvkortrijk": "Kortrijk",
        "kvmechelen": "Mechelen",
    },
    "I1": {
        "acmilan": "Milan",
        "internazionale": "Inter",
    },
    "SC0": {
        "heartofmidlothian": "Hearts",
    },
    "F1": {
        "parissaintgermain": "Paris SG",
        "lehavreac": "Le Havre",
        "staderennais": "Rennes",
        "nice": "Nice",
    },
}

ALTERNATIF_ADLAR = {
    "manchestercity": ("mancity",),
    "manchesterunited": ("manunited", "manutd"),
    "nottinghamforest": ("nottmforest", "nottsforest"),
    "tottenhamhotspur": ("tottenham", "spurs"),
    "wolverhamptonwanderers": ("wolves", "wolverhampton"),
    "brightonandhovealbion": ("brighton",),
    "newcastleunited": ("newcastle",),
    "westhamunited": ("westham",),
    "queensparkrangers": ("qpr",),
    "westbromwichalbion": ("westbrom",),
    "sheffieldwednesday": ("sheffwed",),
    "sheffieldunited": ("sheffunited",),
    "parissaintgermain": ("parissg", "psg"),
    "internazionale": ("inter", "intermilan"),
    "acmilan": ("milan",),
    "borussiamonchengladbach": ("mgladbach", "monchengladbach"),
    "bayer04leverkusen": ("bayerleverkusen", "leverkusen"),
    "bayerleverkusen": ("leverkusen",),
    "fcaugsburg": ("augsburg",),
    "scfreiburg": ("freiburg",),
    "tsghoffenheim": ("hoffenheim",),
    "sv07elversberg": ("elversberg",),
    "sv07elfersberg": ("elversberg",),
    "svelfersberg": ("elversberg",),
    "athleticclub": ("athbilbao", "athleticbilbao"),
    "rayovallecano": ("vallecano",),
    "heartofmidlothian": ("hearts",),
    "staderennais": ("rennes",),
    "lehavreac": ("lehavre",),
    "kvmechelen": ("mechelen",),
    "kvkortrijk": ("kortrijk",),
    "caykurrizespor": ("rizespor",),
    "exetercity": ("exeter",),
    "cheltenhamtown": ("cheltenham",),
    "burtonalbion": ("burton",),
    "sheffieldwednesday": ("sheffwed", "sheffieldwed"),
    "plymouthargyle": ("plymouth",),
    "stockportcounty": ("stockport",),
    "wiganathletic": ("wigan",),
    "bristolrovers": ("bristolroversfc",),
    "colchesterunited": ("colchester",),
    "crewealexandra": ("crewe",),
    "accringtonstanley": ("accrington",),
    "yorkcity": ("york",),
    "salfordcity": ("salford",),
    "northamptontown": ("northampton",),
    "shrewsburytown": ("shrewsbury",),
    "oldhamathletic": ("oldham",),
    "swindontown": ("swindon",),
    "grimsbytown": ("grimsby",),
    "tranmererovers": ("tranmere",),
}


def normalize(isim):
    isim = str(isim or "").casefold()
    isim = isim.replace("ı", "i")
    isim = isim.replace("ø", "o").replace("æ", "ae")
    isim = unicodedata.normalize("NFKD", isim)
    isim = "".join(
        c for c in isim
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]", "", isim)


def varyantlar(isim):
    anahtar = normalize(isim)
    sonuc = {anahtar} if anahtar else set()

    on_ekler = (
        "footballclub",
        "futbolkulubu",
        "associationfootballclub",
    )
    son_ekler = ("footballclub", "futbolkulubu")

    for ek in on_ekler:
        if anahtar.startswith(ek) and len(anahtar) > len(ek) + 4:
            sonuc.add(anahtar[len(ek):])

    for ek in son_ekler:
        if anahtar.endswith(ek) and len(anahtar) > len(ek) + 4:
            sonuc.add(anahtar[:-len(ek)])

    for asil, digerleri in ALTERNATIF_ADLAR.items():
        grup = {asil, *digerleri}
        if anahtar in grup:
            sonuc.update(grup)

    return sonuc


def indeks_olustur(takimlar):
    indeks = {}
    for ad in takimlar:
        for varyant in varyantlar(ad):
            indeks.setdefault(varyant, set()).add(ad)
    return indeks


def otomatik_eslestir(isim, takimlar, indeks=None):
    if not isim:
        return None

    if indeks is None:
        indeks = indeks_olustur(takimlar)

    adaylar = set()
    for varyant in varyantlar(isim):
        adaylar.update(indeks.get(varyant, set()))

    if len(adaylar) == 1:
        return next(iter(adaylar))

    if len(adaylar) > 1:
        return None

    anahtar = normalize(isim)
    if len(anahtar) < 6:
        return None

    
    def benzerlik(ad):
        kaynak = varyantlar(isim)
        hedef = varyantlar(ad)
        return max(
            (
                SequenceMatcher(None, a, b).ratio()
                for a in kaynak
                for b in hedef
                if len(a) >= 4 and len(b) >= 4
            ),
            default=0.0
        )

    puanlar = sorted(
        ((benzerlik(ad), ad) for ad in takimlar),
        reverse=True
    )

    

    if not puanlar:
        return None

    en_iyi, ad = puanlar[0]
    ikinci = puanlar[1][0] if len(puanlar) > 1 else 0.0

    if en_iyi >= 0.90 and en_iyi - ikinci >= 0.10:
        return ad

    return None


def takim_bul(isim, lig, takimlar, indeks):
    anahtar = normalize(isim)
    manuel = TAKIM_ESLESTIRME.get(lig, {}).get(anahtar)

    if manuel:
        aday = otomatik_eslestir(
            manuel, takimlar, indeks
        )
        if aday:
            return aday

    return otomatik_eslestir(
        isim, takimlar, indeks
    )


def tarih_utc(deger):
    if not deger:
        return None

    try:
        tarih = datetime.fromisoformat(
            str(deger).replace("Z", "+00:00")
        )
        if tarih.tzinfo is None:
            return None
        return tarih.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def mevcut_kayitlari_oku():
    if not KAYIT_DOSYASI.exists():
        return []

    veri = json.loads(
        KAYIT_DOSYASI.read_text(encoding="utf-8")
    )

    if not isinstance(veri, list):
        raise ValueError(
            "tahminler.json liste degil; dosya korunuyor"
        )

    return veri


def anahtar(kayit):
    return (
        str(kayit.get("tarih", "")),
        str(kayit.get("ev_sahibi", "")),
        str(kayit.get("deplasman", "")),
    )


def main():
    print("TIPSTER PRO - TOPLU ESLESTIRME")
    simdi = datetime.now(timezone.utc)
    print("Kontrol:", simdi.isoformat())

    if not FIKSTUR.exists():
        raise FileNotFoundError(
            f"Fikstur bulunamadi: {FIKSTUR}"
        )

    veri = json.loads(
        FIKSTUR.read_text(encoding="utf-8")
    )
    maclar = (
        veri if isinstance(veri, list)
        else veri.get("maclar", [])
    )

    if not isinstance(maclar, list):
        raise ValueError("Fikstur listesi gecersiz")

    # Never treat an old fixture snapshot as current predictions.
    olusturulma = tarih_utc(veri.get("olusturulma_utc")) if isinstance(veri, dict) else None
    if olusturulma is None or simdi - olusturulma > timedelta(hours=24) or olusturulma > simdi + timedelta(minutes=5):
        raise ValueError("FIKSTUR_GUNCEL_DEGIL: once guncel fikstur olusturun (24 saat siniri)")

    # Unsupported leagues must remain visible in the audit rather than silently vanish.
    kapsanmayan = Counter(m.get("lig_kodu", "BILINMIYOR") for m in maclar
                          if isinstance(m, dict) and m.get("lig_kodu") not in LIGLER)
    print("LIG_KAPSAM_DISI:", dict(sorted(kapsanmayan.items())))
    print("LIG_UYUMLULUK:", {x["fikstur_kodu"]: x["durum"] for x in lig_uyumluluk_raporu()})

    istatistikler = {}
    indeksler = {}
    tum_veriler = tum_ligleri_al()
    for kod in sorted(set(LIGLER.values())):
        try:
            if kod == "NOR":
                takimlar, _, hatalar = gecmis_maclari_al(
                    "nor.1", gun=120
                )
                if hatalar:
                    raise RuntimeError(
                        f"Norvec veri hatasi: {hatalar}"
                    )
            elif kod == "SWZ":
                takimlar, _, _ = isvicre_verisi_al()
            else:
                takimlar = tum_veriler.get(kod) or lig_verisi_al(kod)

            if not isinstance(takimlar, dict) or not takimlar:
                raise ValueError("Takim verisi gecersiz")

            istatistikler[kod] = takimlar
            indeksler[kod] = indeks_olustur(takimlar)

            print(
                "VERI ALINDI:",
                kod,
                len(takimlar),
                "takim",
            )

        except Exception as hata:
            print("VERI HATASI:", kod, str(hata))

    eski = mevcut_kayitlari_oku()
    mevcut = {
        anahtar(t)
        for t in eski
        if isinstance(t, dict)
    }

    yeni = []
    sayac = Counter()
    ornekler = []
    eslesmeyenler = []
    hesaplama_zamani = datetime.now(
        timezone.utc
    ).isoformat()

    for mac in maclar:
        if not isinstance(mac, dict):
            sayac["GECERSIZ_MAC"] += 1
            continue

        # Check match start before spending time on league/team matching.
        tarih = tarih_utc(mac.get("tarih"))
        if tarih is None:
            sayac["TARIH_BELIRSIZ"] += 1
            continue
        if tarih <= simdi:
            sayac["BASLAMIS_MAC_ATLANDI"] += 1
            continue

        lig_kodu = mac.get("lig_kodu")
        lig = LIGLER.get(lig_kodu)

        if not lig:
            sayac["LIG_KAYNAGI_YOK"] += 1
            continue

        if lig not in istatistikler:
            sayac["LIG_VERISI_ALINAMADI"] += 1
            continue

        takimlar = istatistikler[lig]
        indeks = indeksler[lig]

        ev = takim_bul(
            mac.get("ev_sahibi"),
            lig, takimlar, indeks
        )
        dep = takim_bul(
            mac.get("deplasman"),
            lig, takimlar, indeks
        )

        if not ev or not dep or ev == dep:
            sayac["TAKIM_ESLESMEDI"] += 1

            detay = {
                "lig_kodu": lig_kodu,
                "veri_ligi": lig,
                "ev_sahibi": mac.get("ev_sahibi"),
                "deplasman": mac.get("deplasman"),
                "eslesen_ev": ev,
                "eslesen_deplasman": dep,
            }

            eslesmeyenler.append(detay)

            if len(ornekler) < 20:
                ornekler.append(detay)
            continue

        try:
            if min(
                takimlar[ev]["mac"],
                takimlar[dep]["mac"],
            ) < 5:
                sayac["YETERSIZ_GECMIS"] += 1
                continue
        except (KeyError, TypeError, ValueError):
            sayac["YETERSIZ_GECMIS"] += 1
            continue

        sayac["ANALIZE_HAZIR"] += 1

        kimlik = anahtar(mac)

        if kimlik in mevcut:
            sayac["ZATEN_KAYITLI"] += 1
            continue

        try:
            sonuc = mac_analizi(
                ev, dep, takimlar
            )
        except Exception as hata:
            sayac["ANALIZ_HATASI"] += 1
            print(
                "ANALIZ HATASI:",
                mac.get("ev_sahibi"),
                "-",
                mac.get("deplasman"),
                str(hata),
            )
            continue

        tahmin = {
            "tarih": mac.get("tarih"),
            "lig": mac.get("lig"),
            "ev_sahibi": mac.get("ev_sahibi"),
            "deplasman": mac.get("deplasman"),
            "hesaplama_zamani": hesaplama_zamani,
            "tahmin": sonuc,
        }

        yeni.append(tahmin)
        mevcut.add(kimlik)

        print(
            "TAHMIN:",
            mac.get("ev_sahibi"),
            "-",
            mac.get("deplasman"),
            sonuc,
        )

    if yeni:
        birlesik = eski + yeni
        gecici = KAYIT_DOSYASI.with_suffix(
            ".json.tmp"
        )

        gecici.write_text(
            json.dumps(
                birlesik,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        gecici.replace(KAYIT_DOSYASI)

        for kayit in yeni:
            try:
                durum = tahmin_kaydet(
                    {
                        "tarih": kayit["tarih"],
                        "lig": next(
                            (
                                m.get("lig_kodu")
                                for m in maclar
                                if isinstance(m, dict)
                                and anahtar(m) == anahtar(kayit)
                            ),
                            "",
                        ),
                        "ev_sahibi": kayit["ev_sahibi"],
                        "deplasman": kayit["deplasman"],
                    },
                    kayit["tahmin"],
                )
                print(
                    "GERCEK TAHMIN KAYDI:",
                    durum,
                )
            except Exception as hata:
                print(
                    "IKINCIL KAYIT HATASI:",
                    str(hata),
                )

    ESLESME_RAPORU.write_text(
        json.dumps(
            eslesmeyenler,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("TOPLAM:", len(maclar))

    for durum in (
        "ANALIZE_HAZIR",
        "TAKIM_ESLESMEDI",
        "YETERSIZ_GECMIS",
        "LIG_VERISI_ALINAMADI",
        "LIG_KAYNAGI_YOK",
        "TARIH_BELIRSIZ",
        "BASLAMIS_MAC_ATLANDI",
        "ZATEN_KAYITLI",
        "ANALIZ_HATASI",
    ):
        print(durum + ":", sayac[durum])

    print("ESLESMEYEN TAKIM ORNEKLERI:")
    for ornek in ornekler:
        print(ornek)

    print("YENI KAYIT:", len(yeni))
    print(
        "TOPLAM KAYIT:",
        len(eski) + len(yeni),
    )
    print(
        "ESLESME RAPORU:",
        ESLESME_RAPORU,
    )


if __name__ == "__main__":
    main()
