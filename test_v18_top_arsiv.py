import unittest,copy
from v18_top_arsiv import append
class Test(unittest.TestCase):
 def test_history(self):
  r=dict(id='a',lig='L',ev_sahibi='A',deplasman='B',tarih='2026-11-26T00:00:00Z',hesaplama_zamani_utc='2026-11-24T00:00:00Z',kilit_zamani_utc='2026-11-24T01:00:00Z',kilitli_secim='2.5 UST',olasiliklar={'2.5_ust':80})
  p=dict(olusturulma_utc='2026-11-25T00:00:00Z',tahminler=[r]); h=append(dict(version=1,yayinlar=[]),p,'1'); old=copy.deepcopy(h)
  self.assertEqual(append(h,p,'1'),h)
  p['tahminler'][0]['olasiliklar']['2.5_ust']=70
  h2=append(h,p,'2');self.assertEqual(h,old);self.assertEqual(h2['yayinlar'][0]['adaylar'][0]['yuzde'],80);self.assertEqual(h2['yayinlar'][1]['adaylar'][0]['yuzde'],70)
 def test_invalid(self):
  with self.assertRaises(ValueError): append({}, {}, '1')
