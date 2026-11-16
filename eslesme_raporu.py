
import json
from collections import Counter

DOSYA = "eslesmeyen_maclar.json"

def main():
    with open(DOSYA, encoding="utf-8") as f:
        maclar = json.load(f)

    sayac = Counter()
    ornekler = {}

    for mac in maclar:
        lig = mac.get("lig", "?")

        for taraf, alan in (
            ("EV", "ev_sahibi"),
            ("DEP", "deplasman"),
        ):
            eslesen = mac.get(
                "eslesen_ev" if taraf == "EV"
                else "eslesen_dep"
            )

            if eslesen:
                continue

            ad = mac.get(alan, "")
            anahtar = (lig, ad)
            sayac[anahtar] += 1
            ornekler[anahtar] = mac

    print("ESLESMEYEN MAC:", len(maclar))
    print("ESLESMEYEN FARKLI TAKIM:", len(sayac))

    for (lig, ad), adet in sayac.most_common():
        print(f"{lig} | {ad} | {adet} mac")

    with open(
        "eslesme_raporu.json", "w", encoding="utf-8"
    ) as f:
        json.dump(
            [
                {
                    "lig": lig,
                    "takim": ad,
                    "mac_sayisi": adet,
                }
                for (lig, ad), adet
                in sayac.most_common()
            ],
            f,
            ensure_ascii=False,
            indent=2,
        )

if __name__ == "__main__":
    main()
