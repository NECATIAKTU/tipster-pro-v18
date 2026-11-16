"""UEFA top-flight coverage registry; no network and no changes to prediction logic."""
import json
from pathlib import Path

def kayitlari_al():
    path = Path(__file__).with_name("avrupa_ust_ligler.json")
    return json.loads(path.read_text(encoding="utf-8"))["ligler"]

def eksik_fikstur_ligleri():
    return [r for r in kayitlari_al() if r["durum"] == "candidate_unverified"]

def motor_eksikleri():
    return [r for r in kayitlari_al() if r["ust_lig"] and not r["tahmin_motoruna_bagli"]]
