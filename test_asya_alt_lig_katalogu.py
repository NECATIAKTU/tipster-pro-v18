import json
from pathlib import Path
p=Path(__file__).with_name("asya_alt_ligler.json")
a=json.loads(p.read_text(encoding="utf-8"))
assert len({x["ulke"] for x in a["ligler"]})==47
assert len({(x["ulke"],x["lig"]) for x in a["ligler"]})==len(a["ligler"])
assert all(not x["aktif_tarama"] and not x["tahmin_motoruna_bagli"] for x in a["ligler"])
print("OK",len(a["ligler"]),"alt lig adayi")
