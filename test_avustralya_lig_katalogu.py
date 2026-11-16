import json
from pathlib import Path
x=json.loads(Path(__file__).with_name('avustralya_ligler.json').read_text(encoding='utf-8'))
a=x['ligler']
assert len(a)==x['kayit_sayisi']
assert len({(i['bolge'],i['lig']) for i in a})==len(a)
assert not any(i['tahmin_motoru_baglantisi'] for i in a)
print('Avustralya katalog testi geçti:',len(a))
