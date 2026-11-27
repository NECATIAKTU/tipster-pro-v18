import argparse
import json
import os
import tempfile

from pathlib import Path
from gol_analiz_merkezi import audit


SURUM = "KALICI VERI BANKASI V2"

BANKA = "gol_veri_bankasi_v2.json"


def guncelle(archive, existing):

    if not isinstance(archive, list):
        raise ValueError("Gecersiz arsiv")

    if not isinstance(existing, list):
        raise ValueError("Gecersiz veri bankasi")

    bank = {}

    for m in existing:

        key = m["id"]

        if key in bank:
            raise ValueError("Tekrar banka kaydi")

        bank[key] = m

    report = audit(archive)

    added = 0
    duplicate = 0
    conflicts = 0

    for m in report["veri_bankasi"]:

        key = m["id"]

        if key in bank:

            if bank[key] == m:
                duplicate += 1
            else:
                conflicts += 1

            continue

        bank[key] = m
        added += 1

    records = sorted(
        bank.values(),
        key=lambda x: (x["tarih"], x["id"])
    )

    return {
        "surum": SURUM,
        "toplam_mac": len(records),
        "yeni_mac": added,
        "tekrar_mac": duplicate,
        "celiskili_mac": conflicts,
        "atlanan": report["atlanan"],
        "maclar": records
    }


def kaydet(path, report):

    temp = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False
        ) as f:

            temp = Path(f.name)

            json.dump(
                report,
                f,
                ensure_ascii=False,
                indent=2,
                allow_nan=False
            )

            f.flush()
            os.fsync(f.fileno())

        os.replace(temp, path)

    finally:

        if temp is not None and temp.exists():
            temp.unlink()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--arsiv",
        default="v18_tahmin_arsivi.json"
    )

    args = parser.parse_args()

    source = Path(args.arsiv)
    target = Path(BANKA)

    if source.resolve() == target.resolve():
        raise ValueError("Arsiv korunuyor")

    archive = json.loads(
        source.read_text(encoding="utf-8")
    )

    existing = []

    if target.exists():

        old = json.loads(
            target.read_text(encoding="utf-8")
        )

        if old["surum"] != SURUM:
            raise ValueError("Banka surumu hatali")

        existing = old["maclar"]

    report = guncelle(archive, existing)

    if report["celiskili_mac"]:
        raise ValueError("Celiskili kayitlar var")

    if report["toplam_mac"] == 0:
        raise ValueError("Dogrulanmis kayit yok")

    kaydet(target, report)

    print("TOPLAM MAC:", report["toplam_mac"])
    print("YENI MAC:", report["yeni_mac"])
    print("TEKRAR:", report["tekrar_mac"])


if __name__ == "__main__":
    main()
