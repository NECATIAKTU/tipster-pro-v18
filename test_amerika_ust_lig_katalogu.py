import json
from pathlib import Path
p=Path(__file__).with_name("amerika_ust_ligler.json")
data=json.loads(p.read_text(encoding="utf-8"))["ligler"]
assert len(data)==51
assert sum(x["konfederasyon"]=="CONCACAF" for x in data)==41
assert sum(x["konfederasyon"]=="CONMEBOL" for x in data)==10
assert len({x["federasyon"] for x in data})==51
assert all(not x["tahmin_motoru_baglandi"] for x in data)
print("Amerika lig katalog testleri başarılı")
