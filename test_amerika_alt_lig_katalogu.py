import json
from pathlib import Path
r=json.loads(Path(__file__).with_name('amerika_alt_ligler.json').read_text(encoding='utf-8'))
a=r['ligler']
assert r['federasyon_sayisi']==51
assert r['kayit_sayisi']==len(a)
assert len({x['federasyon'] for x in a})==51
assert all(not x['tahmin_motoru_baglandi'] for x in a)
print('Amerika alt lig katalog testi başarılı')
