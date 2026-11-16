
"""TIPSTER PRO - Toplu takim eslesme kontrolu.

Mevcut tahminleri ve arsivleri degistirmez.
Sadece iki yeni rapor dosyasi olusturur.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from coklu_lig_motoru import tum_ligleri_al


MAP = {
    "eng.1": "E0",
    "eng.2": "E1",
    "eng.3": "E2",
    "eng.4": "E3",
    "eng.5": "EC",
    "sco.1": "SC0",
    "sco.2": "SC1",
    "sco.3": "SC2",
    "ger.1": "D1",
    "ger.2": "D2",
    "esp.1": "SP1",
    "esp.2": "SP2",
    "ita.1": "I1",
    "ita.2": "I2",
    "fra.1": "F1",
    "fra.2": "F2",
    "ned.1": "N1",
    "por.1": "P1",
    "tur.1": "T1",
    "bel.1": "B1",
    "gre.1": "G1",
    "nor.1": "NOR1",
    "jpn.1": "J1",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(
        c for c in s
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main():
    dosya = Path("tipster_v2_eksikler.json")

    eksikler = json.loads(
        dosya.read_text(encoding="utf-8")
    )

    veriler = tum_ligleri_al()

    sorunlar = defaultdict(
        lambda: {
            "mac_sayisi": 0,
            "turler": set(),
        }
    )

    for mac in eksikler:
        if mac.get("neden") not in (
            "unmatched_team",
            "fuzzy_requires_review",
        ):
            continue

        for yon, alan in (
            ("home", "ev"),
            ("away", "dep"),
        ):
            if mac.get(yon + "_type") not in (
                "unmatched",
                "fuzzy_review",
            ):
                continue

            lig = mac["lig"]
            takim = mac[alan]

            kayit = sorunlar[(lig, takim)]
            kayit["mac_sayisi"] += 1
            kayit["turler"].add(
                mac.get(yon + "_type")
            )

    satirlar = []

    for (lig, takim), bilgi in sorted(
        sorunlar.items()
    ):
        kod = MAP.get(lig)

        takimlar = (
            veriler.get(kod, {})
            if kod else {}
        )

        n = norm(takim)

        tam = [
            t for t in takimlar
            if norm(t) == n
        ]

        adaylar = sorted(
            [
                {
                    "kaynak_takim": t,
                    "benzerlik": round(
                        SequenceMatcher(
                            None,
                            n,
                            norm(t)
                        ).ratio(),
                        3
                    ),
                }
                for t in takimlar
            ],
            key=lambda x: x["benzerlik"],
            reverse=True
        )[:5]

        if len(tam) == 1:
            karar = "KESIN_AD_ESLESMESI"
        elif not takimlar:
            karar = "LIG_VERISI_YOK"
        else:
            karar = "MANUEL_DOGRULAMA"

        satirlar.append({
            "lig": lig,
            "veri_kodu": kod,
            "espn_takim": takim,
            "mac_sayisi": bilgi["mac_sayisi"],
            "turler": sorted(bilgi["turler"]),
            "karar": karar,
            "kesin_kaynak_takim": (
                tam[0] if len(tam) == 1
                else None
            ),
            "olasi_adaylar": adaylar,
        })

    sayim = Counter(
        x["karar"] for x in satirlar
    )

    rapor = {
        "eslesmeyen_mac": sum(
            x.get("neden") == "unmatched_team"
            for x in eksikler
        ),
        "manuel_kontrol_mac": sum(
            x.get("neden") == "fuzzy_requires_review"
            for x in eksikler
        ),
        "benzersiz_takim": len(satirlar),
        "kararlar": dict(sayim),
        "takimlar": satirlar,
    }

    Path(
        "tipster_toplu_eslesme_kontrol.json"
    ).write_text(
        json.dumps(
            rapor,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    with Path(
        "tipster_toplu_eslesme_kontrol.txt"
    ).open("w", encoding="utf-8") as f:

        f.write(
            f"TAKIM: {len(satirlar)} | "
            f"KESIN: {sayim['KESIN_AD_ESLESMESI']} | "
            f"KONTROL: {sayim['MANUEL_DOGRULAMA']} | "
            f"VERI YOK: {sayim['LIG_VERISI_YOK']}\n\n"
        )

        for x in satirlar:
            ilk_uc = [
                a["kaynak_takim"]
                for a in x["olasi_adaylar"][:3]
            ]

            f.write(
                f"{x['lig']} | "
                f"{x['espn_takim']} | "
                f"{x['karar']} | "
                f"{', '.join(ilk_uc)}\n"
            )

    print(
        "TOPLU ESLESME | TAKIM:",
        len(satirlar),
        "|",
        dict(sayim)
    )

    print(
        "DOSYALAR: "
        "tipster_toplu_eslesme_kontrol.json "
        "tipster_toplu_eslesme_kontrol.txt"
    )

    print(
        "NOT: Tahminler ve arsivler degistirilmedi."
    )


if __name__ == "__main__":
    main()
