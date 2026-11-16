import unittest
from asya_lig_katalogu import ligleri_al,aktif_ligleri_al,kapsama_ozeti
class TestAsyaKatalog(unittest.TestCase):
    def test_47(self): self.assertEqual(len(ligleri_al()),47)
    def test_unique(self): self.assertEqual(len({x['ulke'] for x in ligleri_al()}),47)
    def test_safe_default(self): self.assertEqual(aktif_ligleri_al(),[])
    def test_schema(self):
        for l in ligleri_al():
            self.assertTrue(l['lig'] and l['ulke'])
            self.assertFalse(l['tahmin_motoruna_bagli'])
if __name__=='__main__': unittest.main()
