import argparse
import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

from v18_lig_kapsam_denetimi import (
    read_league_registry,
    CANDIDATES
)


SURUM = "DUNYA LIGLERI MERKEZI V1"

BOLGELER = {
    "AVRUPA": {
        "eng", "sco", "ger", "esp", "ita",
        "fra", "tur", "pol", "ned", "por",
        "bel", "sui", "aut", "den", "nor",
        "swe", "irl", "gre", "cze", "rou",
        "cro", "fin", "isl", "hun", "ser"
    },
    "ASYA": {
        "jpn", "chn", "kor", "ksa"
    },
    "AFRIKA": {
        "rsa", "egy"
    },
    "KUZEY_AMERIKA": {
        "usa", "mex"
    },
    "GUNEY_AMERIKA": {
        "bra", "arg", "col", "uru",
        "chi", "ecu", "per"
    },
    "OKYANUSYA": {
        "aus", "nzl"
    },
    "ULUSLARARASI": {
        "uefa", "fifa", "afc", "caf",
        "concacaf", "conmebol"
    }
}


def bolge_bul(code):

    prefix = code.split(".")[0]

    for region, countries in BOLGELER.items():

        if prefix in countries:
            return region

    return "DIGER"


def build(registry, archive):

    counts = Counter()
    completed = Counter()
    seen = set()

    for r in archive:

        if not isinstance(r, dict):
            continue

        m = r.get("mac")

        if not isinstance(m, dict):
            continue

        code = m.get("lig_kodu")
        key = r.get("kimlik")

        if not isinstance(code, str):
            continue

        if not isinstance(key, str):
            continue

        if key in seen:
            continue

        seen.add(key)
        counts[code] += 1

        if r.get("durum") == "DOGRULANDI":
            completed[code] += 1

    catalog = dict(registry)

    for code, names in CANDIDATES.items():

        catalog.setdefault(
            code,
            " - ".join(names)
        )

    regions = {}

    for code, name in sorted(catalog.items()):

        region = bolge_bul(code)

        active = (
            code in registry
            and not code.startswith("uefa.")
        )

        item = {
            "kod": code,
            "lig": name,
            "bolge": region,
            "motor_tanimli": code in registry,
            "varsayilan_aktif": active,
            "arsiv_mac": counts[code],
            "sonuclanmis_mac": completed[code],
            "durum": (
                "ARSIV_KAYDI_VAR"
                if counts[code]
                else "KAYNAK_INCELEMESI_GEREKLI"
            )
        }

        regions.setdefault(
            region, []
        ).append(item)

    summary = []

    for region, leagues in sorted(
        regions.items()
    ):

        summary.append({
            "bolge": region,
            "toplam_lig": len(leagues),
            "aktif_lig": sum(
                x["varsayilan_aktif"]
                for x in leagues
            ),
            "arsiv_mac": sum(
                x["arsiv_mac"]
                for x in leagues
            ),
            "ligler": leagues
        })

    return {
        "surum": SURUM,
        "tarih_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "toplam_katalog": len(catalog),
        "motor_tanimli": len(registry),
        "aday_lig": len(catalog) - len(registry),
        "bolgeler": summary,
        "uyari": (
            "Katalog raporudur. "
            "Yeni ligler otomatik etkinlestirilmez. "
            "Canli kaynak testi yapilmamistir."
        )
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--arsiv",
        default="v18_tahmin_arsivi.json"
    )

    parser.add_argument(
        "--cikti",
        default="dunya_ligleri_raporu.json"
    )

    args = parser.parse_args()

    registry = read_league_registry(
        "fikstur_yeni.py"
    )

    data = json.loads(
        Path(args.arsiv).read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, list):
        raise ValueError("Gecersiz arsiv")

    report = build(registry, data)

    with Path(args.cikti).open(
        "x", encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        "TOPLAM LIG:",
        report["toplam_katalog"]
    )


if __name__ == "__main__":
    main()
