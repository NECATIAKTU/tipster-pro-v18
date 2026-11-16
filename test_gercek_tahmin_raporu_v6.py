import unittest
from datetime import datetime, timezone
from gercek_tahmin_raporu import build, decide
NOW = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
def fixture(**overrides):
    row = dict(tarih="2026-11-14T15:00:00+00:00", hesaplama_zamani="2026-11-10T10:00:00+00:00", lig="Test", ev_sahibi="A", deplasman="B", tahmin={"1.5_ust":85,"2.5_ust":70,"3.5_ust":50})
    row.update(overrides)
    return row
class TestRealPredictions(unittest.TestCase):
    def test_decision(self): self.assertEqual(decide({"1.5_ust":85,"2.5_ust":70,"3.5_ust":66}),"3.5 ÜST")
    def test_invalid_probability(self):
        _,_,a=build([fixture(tahmin={"1.5_ust":float("nan")})],NOW)
        self.assertEqual(a["kabul_edilen_farkli_mac"],0)
    def test_after_kickoff(self):
        _,_,a=build([fixture(hesaplama_zamani="2026-11-14T16:00:00+00:00")],NOW)
        self.assertEqual(a["reddedilen"]["mac_basladiktan_sonra_hesaplanmis"],1)
    def test_no_naive_timezone(self):
        _,_,a=build([fixture(tarih="2026-11-14T15:00:00")],NOW)
        self.assertEqual(a["kabul_edilen_farkli_mac"],0)
    def test_duplicate_first_wins(self):
        earlier=fixture(tahmin={"1.5_ust":85})
        later=fixture(hesaplama_zamani="2026-11-10T11:00:00+00:00",tahmin={"1.5_ust":20})
        txt,_,a=build([later,earlier],NOW)
        self.assertEqual(a["kabul_edilen_farkli_mac"],1)
        self.assertIn("1.5 ÜST",txt)
    def test_monotonic(self):
        _,_,a=build([fixture(tahmin={"1.5_ust":40,"2.5_ust":60})],NOW)
        self.assertEqual(a["kabul_edilen_farkli_mac"],0)
    def test_only_upcoming(self):
        _,cur,a=build([fixture(tarih="2026-11-09T15:00:00+00:00")],NOW)
        self.assertEqual(a["henuz_baslamamis"],0)
        self.assertNotIn("A - B",cur)
if __name__=="__main__": unittest.main()
