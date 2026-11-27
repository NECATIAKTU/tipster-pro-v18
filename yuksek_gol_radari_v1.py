import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

SURUM = "YUKSEK GOL RADARI V1"

LINES = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


def utc(value):
    d = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if d.tzinfo is None:
        raise ValueError("Saat dilimi eksik")

    return d.astimezone(timezone.utc)


def radar(records, now=None):

    now = now or datetime.now(timezone.utc)

    groups = {
        "4_PLUS": [],
        "5_PLUS": [],
        "6_PLUS": [],
        "7_PLUS": []
    }

    seen = set()
    skipped = 0
    scanned = 0

    for record in records:

        try:
            m = record.get("mac", record)

            kick = utc(m["tarih"])
            created = utc(
                m["hesaplama_zamani_utc"]
            )

            if not created <= now < kick:
                skipped += 1
                continue

            key = record.get("kimlik") or m["id"]

            if key in seen:
                skipped += 1
                continue

            probs = record.get(
                "olasiliklar"
            ) or m["tahmin"]

            values = [
                float(probs[f"{line:.1f}_ust"])
                for line in LINES
            ]

            if any(
                not math.isfinite(p)
                or not 0 <= p <= 100
                for p in values
            ):
                raise ValueError("Olasilik hatasi")

            if any(
                a < b
                for a, b in zip(
                    values, values[1:]
                )
            ):
                raise ValueError("Olasilik sirasi")

            home = m["ev_sahibi"]
            away = m["deplasman"]

            if not home or not away or home == away:
                raise ValueError("Takim hatasi")

            base = {
                "id": key,
                "lig_kodu": m["lig_kodu"],
                "lig": m.get("lig", ""),
                "mac": home + " - " + away,
                "tarih": m["tarih"],
                "hesaplama_zamani_utc": created.isoformat(),
                "olasiliklar": {
                    f"{line:.1f}_ust": p
                    for line, p in zip(
                        LINES, values
                    )
                }
            }

            seen.add(key)
            scanned += 1

            for goals in range(4, 8):

                line = goals - 0.5

                groups[f"{goals}_PLUS"].append({
                    **base,
                    "cizgi": f"{line:.1f} UST",
                    "model_yuzdesi": float(
                        probs[f"{line:.1f}_ust"]
                    )
                })

        except (
            KeyError,
            ValueError,
            TypeError,
            AttributeError,
            OverflowError
        ):
            skipped += 1

    for items in groups.values():

        items.sort(
            key=lambda x: (
                -x["model_yuzdesi"],
                x["tarih"],
                x["id"]
            )
        )

    return {
        "surum": SURUM,
        "olusturulma_utc": now.isoformat(),
        "taranan_mac": scanned,
        "atlanan_kayit": skipped,
        "radarlar": groups,
        "uyari": (
            "Arastirma siralamasidir. "
            "Kalibre edilmis tahmin degildir."
        )
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--girdi",
        default="v18_tahmin_arsivi.json"
    )

    parser.add_argument(
        "--cikti",
        default="yuksek_gol_radari_raporu.json"
    )

    args = parser.parse_args()

    source = Path(args.girdi)
    target = Path(args.cikti)

    if source.resolve() == target.resolve():
        parser.error("Kaynak dosya korunuyor")

    data = json.loads(
        source.read_text(encoding="utf-8")
    )

    if isinstance(data, dict):
        data = data["tahminler"]

    if not isinstance(data, list):
        raise ValueError("Gecersiz veri")

    report = radar(data)

    with target.open("x", encoding="utf-8") as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("TARANAN:", report["taranan_mac"])
    print("ATLANAN:", report["atlanan_kayit"])


if __name__ == "__main__":
    main()
