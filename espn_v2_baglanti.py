
import json
from datetime import datetime, timezone
from pathlib import Path

from fikstur_yeni import getir
from espn_gecmis_motoru_v2 import verileri_yukle, mac_analiz

GIRIS = "gelecek_maclar.json"
CIKIS = "espn_v2_tahminler.json"


def main():
    kaynak = json.loads(
        Path(GIRIS).read_text(encoding="utf-8")
    )
    gecmis = verileri_yukle()
    simdi = datetime.now(timezone.utc)

    tahminler = []
    durumlar = {}

    for mac in kaynak.get("maclar", []):
        lig = mac.get("lig_kodu")
        tarih = mac.get("tarih", "")

        try:
            baslama = datetime.fromisoformat(
                tarih.replace("Z", "+00:00")
            )
            if baslama <= simdi:
                continue

            olaylar, hatalar = getir(
                lig, baslama, baslama
            )

            olay_id = str(mac["id"]).split("|")[-1]
            olay = next(
                (
                    o for o in olaylar
                    if str(o.get("id")) == olay_id
                ),
                None
            )

            if olay is None:
                durum = "ESPN_MAC_BULUNAMADI"
                sonuc = {"durum": durum}
            else:
                takimlar = olay["competitions"][0]["competitors"]
                ev = next(
                    t for t in takimlar
                    if t.get("homeAway") == "home"
                )
                dep = next(
                    t for t in takimlar
                    if t.get("homeAway") == "away"
                )

                ev_id = str(ev["team"]["id"])
                dep_id = str(dep["team"]["id"])

                sonuc = mac_analiz(
                    gecmis, lig, ev_id, dep_id
                )
                durum = sonuc.get("durum", "BILINMIYOR")

            durumlar[durum] = durumlar.get(durum, 0) + 1

            tahminler.append({
                "id": mac.get("id"),
                "tarih": tarih,
                "lig": lig,
                "ev": mac.get("ev_sahibi"),
                "dep": mac.get("deplasman"),
                "analiz": sonuc
            })

        except (KeyError, ValueError, TypeError, StopIteration) as hata:
            durumlar["HATA"] = durumlar.get("HATA", 0) + 1
            print("Mac hatasi:", mac.get("id"), str(hata))

    rapor = {
        "olusturulma_utc": simdi.isoformat(),
        "gecmis_mac_sayisi": len(gecmis),
        "toplam_fikstur": len(kaynak.get("maclar", [])),
        "islenen_mac": len(tahminler),
        "durumlar": durumlar,
        "tahminler": tahminler
    }

    Path(CIKIS).write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("ESPN V2 BAGLANTI TESTI")
    print("Gecmis mac:", len(gecmis))
    print("Islenen mac:", len(tahminler))
    print("Durumlar:", durumlar)
    print("Dosya:", CIKIS)


if __name__ == "__main__":
    main()
