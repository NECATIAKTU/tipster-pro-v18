import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LINES = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


def utc(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Timezone missing")
    return d


def audit(records):
    groups = defaultdict(list)
    missed = []
    bank = {}
    skipped = defaultdict(int)

    for r in records:
        try:
            if r["durum"] != "DOGRULANDI":
                skipped["unverified_result"] += 1
                continue

            m, s = r["mac"], r["sonuc"]
            kick = utc(m["tarih"])

            if not utc(m["hesaplama_zamani_utc"]) <= utc(r["kilit_zamani_utc"]) < kick:
                raise ValueError("Late prediction")

            key = r["kimlik"]

            if key in bank:
                skipped["duplicate"] += 1
                continue

            hg, ag = s["ev_gol"], s["dep_gol"]

            if any(type(x) is not int or x < 0 for x in (hg, ag)):
                raise ValueError("Bad score")

            total = hg + ag

            if total != s["toplam_gol"]:
                raise ValueError("Score mismatch")

            probs = [
                float(r["olasiliklar"][f"{l:.1f}_ust"]) / 100
                for l in LINES
            ]

            if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probs):
                raise ValueError("Bad probability")

            if any(a < b for a, b in zip(probs, probs[1:])):
                raise ValueError("Invalid probability order")

            league = m["lig_kodu"]

            row = dict(
                id=key,
                tarih=m["tarih"],
                lig_kodu=league,
                ev_sahibi=m["ev_sahibi"],
                deplasman=m["deplasman"],
                ev_gol=hg,
                dep_gol=ag,
                toplam_gol=total
            )

            bank[key] = row

            for line, p in zip(LINES, probs):
                y = int(total > line)
                bucket = min(9, int(p * 10))

                for scope in ("ALL", league):
                    groups[(scope, line, "all")].append((p, y))
                    groups[(scope, line, str(bucket))].append((p, y))

            if total >= 4 and str(
                r.get("kilitli_secim", "")
            ).upper() in ("RISKLI", "RİSKLİ"):
                missed.append({
                    **row,
                    "olasiliklar": r["olasiliklar"]
                })

        except (
            KeyError, TypeError, ValueError,
            AttributeError, OverflowError
        ):
            skipped["invalid_record"] += 1

    metrics = []

    for (scope, line, bucket), vals in sorted(groups.items()):
        n = len(vals)

        metrics.append(dict(
            lig=scope,
            cizgi=line,
            dilim=bucket,
            n=n,
            model=round(100 * sum(p for p, y in vals) / n, 2),
            gercek=round(100 * sum(y for p, y in vals) / n, 2),
            brier=round(sum((p-y)**2 for p, y in vals) / n, 5)
        ))

    return dict(
        dogrulanan=len(bank),
        atlanan=dict(skipped),
        kacirilan_goller=sorted(
            missed,
            key=lambda x: (-x["toplam_gol"], x["tarih"])
        ),
        kalibrasyon=metrics,
        veri_bankasi=list(bank.values())
    )


def main():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--arsiv",
        default="v18_tahmin_arsivi.json"
    )

    p.add_argument(
        "--cikti",
        default="gol_analiz_raporu.json"
    )

    a = p.parse_args()
    source = Path(a.arsiv)
    dest = Path(a.cikti)

    if dest.resolve() == source.resolve():
        p.error("Archive cannot be overwritten")

    data = json.loads(
        source.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        p.error("Expected archive list")

    with dest.open("x", encoding="utf-8") as f:
        json.dump(
            audit(data),
            f,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    main()
