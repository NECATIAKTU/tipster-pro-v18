import argparse
import json

from pathlib import Path
from datetime import datetime, timezone
from tempfile import TemporaryDirectory

from gol_analiz_merkezi import audit
from yuksek_gol_radari_v1 import radar

from kalici_veri_bankasi_v1 import (
    veri_kaydet,
    lig_istatistikleri
)

from dunya_ligleri_merkezi_v1 import build
from motor_karsilastirma_merkezi_v1 import compare

from v18_lig_kapsam_denetimi import (
    read_league_registry
)


SURUM = "GOL MERKEZ ENTEGRASYON V1"


def run(archive, registry, motor_records=None):

    if not isinstance(archive, list):
        raise ValueError("Gecersiz arsiv")

    now = datetime.now(timezone.utc)

    reports = {}
    errors = {}

    def execute(name, task):

        try:

            reports[name] = task()

        except Exception as exc:

            errors[name] = {
                "hata": type(exc).__name__,
                "aciklama": str(exc)
            }

    execute(
        "gol_analizi",
        lambda: audit(archive)
    )

    execute(
        "yuksek_gol_radari",
        lambda: radar(archive, now)
    )

    def database_report():

        with TemporaryDirectory() as folder:

            db = Path(folder) / "test.sqlite3"

            result = veri_kaydet(
                archive, db
            )

            result["ligler"] = (
                lig_istatistikleri(db)
            )

            result["depolama"] = (
                "GECICI_TEST"
            )

            return result

    execute(
        "veri_bankasi",
        database_report
    )

    execute(
        "dunya_ligleri",
        lambda: build(
            registry, archive
        )
    )

    if motor_records is not None:

        execute(
            "motor_karsilastirma",
            lambda: compare(motor_records)
        )

    else:

        reports["motor_karsilastirma"] = {
            "durum": "ORTAK_VERI_BEKLENIYOR"
        }

    return {
        "surum": SURUM,
        "tarih_utc": now.isoformat(),
        "arsiv_kayit_sayisi": len(archive),
        "durum": (
            "HATA_VAR"
            if errors
            else "RAPOR_HAZIR"
        ),
        "raporlar": reports,
        "hatalar": errors,
        "ana_motor_degisti": False
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--arsiv",
        default="v18_tahmin_arsivi.json"
    )

    parser.add_argument(
        "--motor-verisi",
        default=None
    )

    parser.add_argument(
        "--cikti",
        default="gol_merkez_raporu_v1.json"
    )

    args = parser.parse_args()

    source = Path(args.arsiv)
    target = Path(args.cikti)

    if target.exists():
        raise FileExistsError(
            "Mevcut dosya korunuyor"
        )

    archive = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    registry = read_league_registry(
        "fikstur_yeni.py"
    )

    motor_records = None

    if args.motor_verisi:

        motor_records = json.loads(
            Path(args.motor_verisi).read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(motor_records, list):
            raise ValueError(
                "Gecersiz motor verisi"
            )

    report = run(
        archive,
        registry,
        motor_records
    )

    with target.open(
        "x", encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("DURUM:", report["durum"])
    print("MODULLER:", list(report["raporlar"]))
    print("HATALAR:", report["hatalar"])

    if report["hatalar"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
