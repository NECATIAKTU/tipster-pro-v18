import tempfile, json, unittest
from pathlib import Path
from datetime import datetime, timezone
from haftalik_kapasite import evaluate

class CapacityTests(unittest.TestCase):
    def test_unique_and_pre_match(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            good={'lig':'A','ev_sahibi':'X','deplasman':'Y','tarih':'2026-11-11T19:00:00+00:00','hesaplama_zamani':'2026-11-11T10:00:00+00:00','tahmin':{'2.5_ust':70}}
            bad=dict(good,ev_sahibi='Z',hesaplama_zamani='2026-11-11T20:00:00+00:00')
            (root/'tahminler.json').write_text(json.dumps([good,good,bad]))
            (root/'gelecek_maclar.json').write_text(json.dumps({'maclar':[good,bad]}))
            result=evaluate(datetime(2026,11,11,12,tzinfo=timezone.utc),root)
            self.assertEqual(result['zaman_dogrulanmis_tahmin_farkli_mac'],1)
            self.assertEqual(result['fikstur_farkli_mac'],2)
            self.assertEqual(result['hedefe_kalan'],99)
    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as td:
            result=evaluate(datetime(2026,11,10,tzinfo=timezone.utc),Path(td))
            self.assertEqual(result['zaman_dogrulanmis_tahmin_farkli_mac'],0)

if __name__=='__main__':unittest.main()
