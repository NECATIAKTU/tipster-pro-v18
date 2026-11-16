"""Verified, pre-match-only real prediction report. Never mutates prediction inputs."""
import json, math, os, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "tahminler.json"
REPORT = ROOT / "gercek_tahmin_raporu.txt"
CURRENT = ROOT / "guncel_tahmin_raporu.txt"
AUDIT = ROOT / "gercek_tahmin_kalite_raporu.json"
THRESHOLDS = (("6.5_ust", 65, "6.5 ÜST"), ("5.5_ust", 65, "5.5 ÜST"), ("4.5_ust", 65, "4.5 ÜST"), ("3.5_ust", 65, "3.5 ÜST"), ("2.5_ust", 65, "2.5 ÜST"), ("1.5_ust", 75, "1.5 ÜST"))

def utc(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None

def probability(value):
    if isinstance(value, bool): return None
    try: n = float(value)
    except (ValueError, TypeError): return None
    return n if math.isfinite(n) and 0 <= n <= 100 else None

def decide(prediction):
    if not isinstance(prediction, dict): return "RİSKLİ"
    for key, threshold, label in THRESHOLDS:
        p = probability(prediction.get(key))
        if p is not None and p >= threshold: return label
    return "RİSKLİ"

def validate(record, now):
    if not isinstance(record, dict): return None, "gecersiz_kayit"
    if not all(isinstance(record.get(k), str) and record[k].strip() for k in ("lig", "ev_sahibi", "deplasman")):
        return None, "eksik_mac_bilgisi"
    start = utc(record.get("tarih"))
    computed = utc(record.get("hesaplama_zamani"))
    if start is None or computed is None: return None, "gecersiz_veya_eksik_utc_zamani"
    if computed >= start: return None, "mac_basladiktan_sonra_hesaplanmis"
    if computed > now: return None, "gelecekten_hesaplama_zamani"
    prediction = record.get("tahmin")
    if not isinstance(prediction, dict) or not prediction: return None, "eksik_tahmin"
    for key in ("1.5_ust", "2.5_ust", "3.5_ust", "4.5_ust", "5.5_ust", "6.5_ust"):
        if key in prediction and probability(prediction[key]) is None: return None, "gecersiz_olasilik"
    available = [probability(prediction[k]) for k in ("1.5_ust", "2.5_ust", "3.5_ust", "4.5_ust", "5.5_ust", "6.5_ust") if k in prediction]
    if any(a < b for a, b in zip(available, available[1:])): return None, "tutarsiz_gol_olasiliklari"
    return (start, computed, record), None

def atomic_write(path, content):
    fd, temp = tempfile.mkstemp(prefix=path.name+".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def build(records, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(records, list): raise ValueError("tahminler.json liste olmali")
    rejected = {}; selected = {}
    for rec in records:
        item, reason = validate(rec, now)
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        start, computed, row = item
        key = (start.isoformat(), row["lig"].strip().casefold(), row["ev_sahibi"].strip().casefold(), row["deplasman"].strip().casefold())
        # Immutable earliest pre-match prediction; later recalculations never replace it.
        if key not in selected or computed < selected[key][1]: selected[key] = item
    ordered = sorted(selected.values(), key=lambda x: (x[0], x[2]["lig"], x[2]["ev_sahibi"]))
    header = ["TIPSTER PRO - DOGRULANABILIR MAC ONCESI TAHMIN RAPORU", "Olusturulma (UTC): " + now.isoformat(), "Not: Olasiliklar model ciktisidir; gercek basari orani degildir.", "", "TARIH | LIG | MAC | TAHMIN"]
    lines = header[:]
    upcoming = ["TIPSTER PRO - HENUZ BASLAMAMIS MACLAR", "Olusturulma (UTC): " + now.isoformat(), "", "TARIH | LIG | MAC | TAHMIN"]
    counts = {}; upcoming_count = 0
    for start, computed, rec in ordered:
        decision = decide(rec["tahmin"])
        counts[decision] = counts.get(decision, 0) + 1
        line = f'{start.isoformat()} | {rec["lig"]} | {rec["ev_sahibi"]} - {rec["deplasman"]} | {decision}'
        lines.append(line)
        if start > now:
            upcoming.append(line); upcoming_count += 1
    lines += ["", "TOPLAM FARKLI MAC: " + str(len(ordered)), "HENUZ BASLAMAMIS: " + str(upcoming_count)]
    for _, _, label in THRESHOLDS: lines.append(f'{label}: {counts.get(label, 0)}')
    lines.append(f'RİSKLİ: {counts.get("RİSKLİ", 0)}')
    audit = {"olusturulma_utc":now.isoformat(), "kaynak_satir":len(records), "kabul_edilen_farkli_mac":len(ordered), "henuz_baslamamis":upcoming_count, "reddedilen":rejected, "yinelenen_gecerli_satir":sum(1 for rec in records if validate(rec, now)[0] is not None)-len(ordered), "kararlar":counts, "not":"Gercek fikstur ve model verisi disaridan bagimsiz dogrulanmadi; bu rapor kaynak kayitlarin zaman ve olasilik tutarliligini kontrol eder."}
    return "\n".join(lines)+"\n", "\n".join(upcoming)+"\n", audit

def main():
    if not SOURCE.is_file(): raise SystemExit("HATA: tahminler.json yok; rapor degistirilmedi")
    records = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    report, current, audit = build(records)
    atomic_write(REPORT, report)
    atomic_write(CURRENT, current)
    atomic_write(AUDIT, json.dumps(audit, ensure_ascii=False, indent=2)+"\n")
    print(report)

if __name__ == "__main__": main()
