import json
from pathlib import Path
d=json.loads(Path(__file__).with_name('afrika_ligler.json').read_text(encoding='utf-8'))
a=d['ligler']
assert d['federasyon_sayisi']==54
assert len(a)==108
assert len({x['ulke'] for x in a})==54
assert len({(x['ulke'],x['seviye']) for x in a})==108
assert all(not x['tahmin_motoru_baglandi'] for x in a)
print('Afrika katalog testi başarılı')
