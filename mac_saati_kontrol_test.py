
import json
from datetime import datetime, timezone

ARSIV = "tahmin_arsivi.json"
FIKSTUR = "gelecek_maclar.json"
CIKTI = "mac_saati_kontrol_raporu.json"


def utc(t):
    try:
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, TypeError, AttributeError):
        return None


def yukle(dosya):
    with open(dosya, encoding="utf-8") as f:
        return json.load(f)


def main():
    tahminler = yukle(ARSIV)
    veri = yukle(FIKSTUR)
    maclar = veri["maclar"] if isinstance(veri, dict) else veri

    indeks = {}
    for m in maclar:
        ev = m.get("ev_sahibi", m.get("ev"))
        dep = m.get("deplasman", m.get("dep"))
        tarih = utc(m.get("tarih"))
        if ev and dep and tarih:
            anahtar = (ev.casefold(), dep.casefold(), tarih.date())
            indeks.setdefault(anahtar, []).append(tarih)

    rapor = []
    for t in tahminler:
        hesap = utc(t.get("hesaplama_zamani_utc"))
        try:
            gun = datetime.strptime(t["tarih"], "%d/%m/%Y").date()
            anahtar = (
                t["ev"].casefold(),
                t["dep"].casefold(),
                gun
            )
            saatler = indeks.get(anahtar, [])
        except (KeyError, ValueError, AttributeError):
            saatler = []

        if len(saatler) != 1 or hesap is None:
            durum = "BELIRSIZ"
        elif hesap < saatler[0]:
            durum = "MAC_ONCESI"
        else:
            durum = "MAC_SONRASI"

        rapor.append({
            "tarih": t.get("tarih"),
            "ev": t.get("ev"),
            "dep": t.get("dep"),
            "durum": durum,
            "mac_baslangic_utc": (
                saatler[0].isoformat() if len(saatler) == 1 else None
            )
        })

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    for durum in ("MAC_ONCESI", "MAC_SONRASI", "BELIRSIZ"):
        print(durum, sum(r["durum"] == durum for r in rapor))


if __name__ == "__main__":
    main()
