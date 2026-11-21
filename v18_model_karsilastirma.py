"""TIPSTER PRO V18 - only-read, retrospective probability comparison.

Reads immutable existing V18 archive and ESPNs historical fixtures.
Never alters live model, selections, results, archive, or Pages.
Uses ESPN kickoff <= original prediction creation - 6 hours as a conservative
proxy for games whose scores were available at the time. This does NOT prove
historical API snapshots, and the report is explicitly retrospective.
"""
import argparse
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gercek_tahmin_v18 import get_json
from v18_guclendirme_v1 import completed_games, estimate

LINES = ("1.5", "2.5", "3.5", "4.5", "5.5", "6.5")


def utc(value):
    if not isinstance(value, str):
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, OverflowError):
        return None


def good_probability(value):
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and 0 <= v <= 100 else None


def eligible(record):
    """Use only completed records with a genuine, pre-kickoff V18 model estimate."""
    if not isinstance(record, dict) or record.get("durum") != "DOGRULANDI":
        return None
    match = record.get("mac") or {}
    result = record.get("sonuc") or {}
    kickoff = utc(match.get("tarih"))
    created = utc(match.get("hesaplama_zamani_utc"))
    locked = utc(record.get("kilit_zamani_utc"))
    if not (kickoff and created and locked and created < kickoff and locked < kickoff):
        return None
    league = match.get("lig_kodu")
    home = match.get("istatistik_ev") or match.get("ev_sahibi")
    away = match.get("istatistik_deplasman") or match.get("deplasman")
    if not all(isinstance(x, str) and x.strip() for x in (league, home, away)):
        return None
    try:
        home_goals = int(result["ev_gol"])
        away_goals = int(result["dep_gol"])
    except (TypeError, ValueError, KeyError):
        return None
    if home_goals < 0 or away_goals < 0:
        return None
    p = record.get("olasiliklar") or match.get("tahmin") or {}
    if not isinstance(p, dict):
        return None
    original = {f"{line}_ust": good_probability(p.get(f"{line}_ust")) for line in LINES}
    if not any(v is not None for v in original.values()):
        return None
    return {
        "kimlik": record.get("kimlik"), "lig_kodu": league,
        "ev": home, "dep": away, "mac": f"{match.get('ev_sahibi')} - {match.get('deplasman')}",
        "baslangic": kickoff, "hesaplama": created,
        "gol": home_goals + away_goals,
        "kilitli_secim": record.get("kilitli_secim"),
        "v18": original,
    }


def make_history(league, cutoff, days, fetch, cache, error_log):
    """Fetch whole UTC dates strictly before the calculation timestamp.

    A 6-hour lag avoids a just-started game's future final score being counted.
    All returned event dates are checked again against that lag, irrespective
    of the date API's timezone behavior.
    """
    latest = cutoff - timedelta(hours=6)
    # Start 1 day earlier than latest date to avoid timezone boundary misses.
    start_day = (cutoff - timedelta(days=days)).date()
    end_day = latest.date()
    events = []
    missed = 0
    day = start_day
    while day <= end_day:
        key = (league, day.isoformat())
        if key not in cache:
            try:
                payload = fetch(league, day)
                matches = payload.get("events")
                if not isinstance(matches, list):
                    raise ValueError("ESPN events list missing")
                cache[key] = matches
            except (OSError, ValueError, TypeError, KeyError, TimeoutError) as exc:
                cache[key] = None
                error_log.append(f"{league} {day}: {str(exc)[:90]}")
        if cache[key] is None:
            missed += 1
        else:
            events.extend(cache[key])
        day += timedelta(days=1)
    # Reject incomplete history rather than comparing unequal quality samples.
    if missed > max(2, int(days * 0.10)):
        return None, missed
    games = [g for g in completed_games(events, cutoff=latest)
             if g[0] >= cutoff - timedelta(days=days)]
    return games, missed


def compare(archive, fetch, days=90, limit=30):
    """Compare both probability vectors on exactly the same completed matches.

    Unlike a betting result, Brier score evaluates probability calibration per
    goal line; lower means better. No picks are created, blocked, or revised.
    """
    source = [x for r in archive if (x := eligible(r)) is not None]
    source.sort(key=lambda x: (x["baslangic"], str(x["kimlik"])), reverse=True)
    source = source[:limit]
    cache, errors = {}, []
    rows = []
    for item in source:
        games, failures = make_history(item["lig_kodu"], item["hesaplama"], days, fetch, cache, errors)
        if games is None:
            model = {"durum": "ESPN_GECMIS_EKSIK"}
        else:
            model = estimate(games, item["ev"], item["dep"])
        comparison = {}
        for line in LINES:
            key = f"{line}_ust"
            old = item["v18"].get(key)
            new = good_probability((model.get("olasiliklar") or {}).get(key))
            if old is None or new is None or model.get("durum") != "ARASTIRMA_TAHMINI":
                continue
            actual = int(item["gol"] > float(line))
            comparison[line] = {
                "oldu": actual, "v18_yuzde": old, "guclendirme_yuzde": new,
                "v18_brier": round((old / 100 - actual)**2, 6),
                "guclendirme_brier": round((new / 100 - actual)**2, 6),
            }
        rows.append({
            "kimlik": item["kimlik"], "mac": item["mac"],
            "lig": item["lig_kodu"], "baslangic_utc": item["baslangic"].isoformat(),
            "hesaplama_utc": item["hesaplama"].isoformat(),
            "toplam_gol": item["gol"], "v18_kilitli_secim": item["kilitli_secim"],
            "yeni_model_durum": model.get("durum"), "kaynak_eksik_gun": failures,
            "olasilik_karsilastirmasi": comparison,
        })
    metric = {}
    for line in LINES:
        pairs = [r["olasilik_karsilastirmasi"][line]
                 for r in rows if line in r["olasilik_karsilastirmasi"]]
        metric[line] = {
            "ortak_mac": len(pairs),
            "v18_brier": round(sum(x["v18_brier"] for x in pairs) / len(pairs), 5) if pairs else None,
            "guclendirme_brier": round(sum(x["guclendirme_brier"] for x in pairs) / len(pairs), 5) if pairs else None,
        }
    return {
        "rapor": "V18 ve Guclendirme V1 - RETROSPEKTIF olasilik karsilastirmasi",
        "tarih_utc": datetime.now(timezone.utc).isoformat(),
        "not": "Eski V18 tahminleri korunur. Yeni model geriye donuk tekrar hesaplanir; tarihsel API revizyonlari nedeniyle gercek zamanli ileriye donuk kanit degildir. Kucuk orneklem ve secilmis maclar genellenemez.",
        "secim_kurali_degisti": False, "canli_motor_degisti": False,
        "incelenen": len(rows),
        "karsilastirilabilen": sum(bool(x["olasilik_karsilastirmasi"]) for x in rows),
        "basarisiz_gecmis_sorgusu": len(errors), "hata_ornekleri": errors[:12],
        "brier_dusuk_iyidir": metric,
        "maclar": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arsiv", default="v18_tahmin_arsivi.json")
    parser.add_argument("--cikti", default="v18_guclendirme_karsilastirma.json")
    parser.add_argument("--gun", type=int, default=90)
    parser.add_argument("--adet", type=int, default=30)
    args = parser.parse_args()
    if not (30 <= args.gun <= 180) or not (1 <= args.adet <= 200):
        parser.error("--gun: 30..180, --adet: 1..200")
    src, dst = Path(args.arsiv), Path(args.cikti)
    if src.resolve() == dst.resolve() or dst.exists():
        raise SystemExit("Girdi veya mevcut rapor korunuyor. Yeni bir cikti adi secin.")
    archive = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(archive, list):
        raise SystemExit("V18 arsivi JSON liste olmali")
    report = compare(archive, get_json, args.gun, args.adet)
    dst.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("KARSILASTIRMA:", report["karsilastirilabilen"], "/", report["incelenen"])
    for line, stats in report["brier_dusuk_iyidir"].items():
        print(line, "UST", stats)
    print("RAPOR:", dst)


if __name__ == "__main__":
    main()
