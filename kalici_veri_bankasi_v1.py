import argparse
import json
import sqlite3

from pathlib import Path
from datetime import datetime, timezone
from gol_analiz_merkezi import audit


SURUM = "KALICI VERI BANKASI V1"

DB_NAME = "gol_veri_bankasi_v1.sqlite3"


def veri_kaydet(records, db):

    report = audit(records)

    added = 0
    duplicate = 0
    conflicts = 0

    with sqlite3.connect(db) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS maclar (
                id TEXT PRIMARY KEY,
                lig TEXT NOT NULL,
                tarih TEXT NOT NULL,
                ev TEXT NOT NULL,
                dep TEXT NOT NULL,
                ev_gol INTEGER NOT NULL,
                dep_gol INTEGER NOT NULL,
                toplam_gol INTEGER NOT NULL
            )
        """)

        for m in report["veri_bankasi"]:

            row = (
                m["id"],
                m["lig_kodu"],
                m["tarih"],
                m["ev_sahibi"],
                m["deplasman"],
                m["ev_gol"],
                m["dep_gol"],
                m["toplam_gol"]
            )

            old = conn.execute(
                "SELECT * FROM maclar WHERE id = ?",
                (m["id"],)
            ).fetchone()

            if old is not None:

                if old == row:
                    duplicate += 1
                else:
                    conflicts += 1

                continue

            conn.execute(
                "INSERT INTO maclar VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

            added += 1

        total = conn.execute(
            "SELECT COUNT(*) FROM maclar"
        ).fetchone()[0]

        leagues = conn.execute(
            "SELECT COUNT(DISTINCT lig) FROM maclar"
        ).fetchone()[0]

    return {
        "surum": SURUM,
        "tarih": datetime.now(
            timezone.utc
        ).isoformat(),
        "yeni_mac": added,
        "tekrar_mac": duplicate,
        "celiskili_mac": conflicts,
        "toplam_mac": total,
        "toplam_lig": leagues,
        "atlanan": report["atlanan"]
    }


def lig_istatistikleri(db):

    with sqlite3.connect(db) as conn:

        rows = conn.execute("""
            SELECT
                lig,
                COUNT(*),
                AVG(toplam_gol),
                SUM(CASE WHEN toplam_gol >= 2
                    THEN 1 ELSE 0 END),
                SUM(CASE WHEN toplam_gol >= 3
                    THEN 1 ELSE 0 END),
                SUM(CASE WHEN toplam_gol >= 4
                    THEN 1 ELSE 0 END),
                SUM(CASE WHEN toplam_gol >= 5
                    THEN 1 ELSE 0 END),
                SUM(CASE WHEN toplam_gol >= 6
                    THEN 1 ELSE 0 END),
                SUM(CASE WHEN toplam_gol >= 7
                    THEN 1 ELSE 0 END)
            FROM maclar
            GROUP BY lig
            ORDER BY lig
        """).fetchall()

    result = []

    for row in rows:

        lig, n, avg, *counts = row

        result.append({
            "lig": lig,
            "mac_sayisi": n,
            "gol_ortalamasi": round(avg, 2),
            "gol_oranlari": {
                f"{i + 1.5:.1f}_ust":
                    round(100 * count / n, 2)
                for i, count in enumerate(counts)
            }
        })

    return result


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--arsiv",
        default="v18_tahmin_arsivi.json"
    )

    args = parser.parse_args()

    source = Path(args.arsiv)
    db = Path(DB_NAME)

    if source.resolve() == db.resolve():
        raise ValueError("Kaynak korunuyor")

    records = json.loads(
        source.read_text(encoding="utf-8")
    )

    if not isinstance(records, list):
        raise ValueError("Gecersiz arsiv")

    report = veri_kaydet(records, db)

    report["ligler"] = lig_istatistikleri(db)

    print(json.dumps(
        report,
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    main()
