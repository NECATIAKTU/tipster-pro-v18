from pazar_motoru import pazar_analizi

MIN_MAC = 5
MIN_AVANTAJ = 0.05


def pazar_sec(ev_gol, dep_gol, ev_mac, dep_mac, oranlar=None):
    if min(ev_mac, dep_mac) < MIN_MAC:
        return {
            "karar": "PAS",
            "neden": "Yetersiz mac verisi"
        }

    pazarlar = pazar_analizi(ev_gol, dep_gol)
    oranlar = oranlar or {}

    adaylar = sorted(
        pazarlar.items(),
        key=lambda x: x[1],
        reverse=True
    )

    if not oranlar:
        return {
            "karar": "ORAN BEKLENIYOR",
            "neden": "Gercek bahis oranlari yok",
            "en_yuksek_olasiliklar": [
                {"pazar": ad, "olasilik": yuzde}
                for ad, yuzde in adaylar[:5]
            ]
        }

    secenekler = []

    for ad, yuzde in pazarlar.items():
        oran = oranlar.get(ad)

        if oran is None:
            continue

        try:
            oran = float(oran)
        except (ValueError, TypeError):
            continue

        if oran <= 1:
            continue

        p = yuzde / 100
        avantaj = p * oran - 1

        secenekler.append({
            "pazar": ad,
            "olasilik": yuzde,
            "oran": oran,
            "model_avantaji": round(avantaj * 100, 2)
        })

    secenekler.sort(
        key=lambda x: x["model_avantaji"],
        reverse=True
    )

    if not secenekler:
        return {
            "karar": "PAS",
            "neden": "Gecerli oran bulunamadi"
        }

    en_iyi = secenekler[0]

    if en_iyi["model_avantaji"] < MIN_AVANTAJ * 100:

        return {
            "karar": "PAS",
            "neden": "Yeterli model avantaji yok",
            "adaylar": secenekler[:3]
        }

    return {
        "karar": "INCELEME ADAYI",
        "secim": en_iyi,
        "alternatifler": secenekler[1:3],
        "uyari": "Model henuz kalibre edilmedi"
    }


if __name__ == "__main__":
    sonuc = pazar_sec(1.6, 1.2, 10, 10)
    print("TIPSTER PRO - PAZAR SECICI V2")
    print(sonuc)
