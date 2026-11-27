import math
from datetime import datetime
from collections import defaultdict
from itertools import combinations

SURUM = "MOTOR KARSILASTIRMA MERKEZI V1"

MOTORLAR = (
    "V18",
    "V19",
    "KARTAL",
    "GELISTIRME_V1"
)

LINES = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


def utc(value):

    d = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if d.tzinfo is None:
        raise ValueError("Saat dilimi eksik")

    return d


def compare(records):

    matches = {}
    conflicts = set()
    skipped = 0

    for r in records:

        try:

            model = r["motor"]

            if model not in MOTORLAR:
                raise ValueError("Bilinmeyen motor")

            if r["durum"] != "DOGRULANDI":
                raise ValueError("Sonuc bekleniyor")

            kick = utc(r["tarih"])
            created = utc(r["hesaplama_zamani_utc"])

            if created >= kick:
                raise ValueError("Gec tahmin")

            total = r["toplam_gol"]

            if type(total) is not int or total < 0:
                raise ValueError("Gecersiz skor")

            probs = [
                float(r["olasiliklar"][f"{l:.1f}_ust"])
                for l in LINES
            ]

            if any(
                not math.isfinite(p)
                or not 0 <= p <= 100
                for p in probs
            ):
                raise ValueError("Gecersiz olasilik")

            if any(
                a < b for a, b
                in zip(probs, probs[1:])
            ):
                raise ValueError("Olasilik sirasi")

            key = (
                r["lig_kodu"],
                r["id"],
                kick.isoformat()
            )

            item = {
                "gol": total,
                "probs": probs,
                "created": created
            }

            group = matches.setdefault(key, {})

            if model in group:

                if group[model] != item:
                    conflicts.add(key)

                continue

            group[model] = item

        except (
            KeyError, TypeError, ValueError,
            AttributeError, OverflowError
        ):
            skipped += 1

    scores = defaultdict(list)

    for key, models in matches.items():

        if key in conflicts:
            continue

        if len({
            m["gol"] for m in models.values()
        }) != 1:
            conflicts.add(key)
            continue

        for a, b in combinations(
            sorted(models), 2
        ):

            first = models[a]
            second = models[b]

            if first["created"] != second["created"]:
                continue

            total = first["gol"]

            for i, line in enumerate(LINES):

                actual = int(total > line)

                pa = first["probs"][i] / 100
                pb = second["probs"][i] / 100

                for scope in ("ALL", key[0]):

                    scores[
                        (scope, a, b, line)
                    ].append((
                        (pa - actual) ** 2,
                        (pb - actual) ** 2
                    ))

    report = []

    for (league, a, b, line), rows in sorted(
        scores.items()
    ):

        n = len(rows)

        ba = sum(x[0] for x in rows) / n
        bb = sum(x[1] for x in rows) / n

        report.append({
            "lig": league,
            "cizgi": line,
            "ortak_mac": n,
            "motor_a": a,
            "motor_b": b,
            "brier_a": round(ba, 6),
            "brier_b": round(bb, 6),
            "veri_durumu": (
                "KISITLI_ORNEKLEM"
                if n < 100
                else "INCELEMEYE_UYGUN"
            )
        })

    return {
        "surum": SURUM,
        "toplam_mac": len(matches),
        "atlanan": skipped,
        "celiskili_mac": len(conflicts),
        "karsilastirmalar": report,
        "uyari": (
            "Dusuk Brier daha iyidir. "
            "Tek basina model ustunlugu kaniti degildir."
        )
    }
