import unittest
from datetime import datetime, timezone
from v19_panel_entegrasyon import combine

NOW = datetime(2026, 11, 24, 10, tzinfo=timezone.utc)
BASE = {'model': 'TIPSTER PRO V18', 'tahminler': [
    {'lig_kodu': 'sui.1', 'id': 'old', 'tahmin': {'2.5_ust': 70}}
]}
NEW = {'lig_kodu': 'pol.1', 'id': 'new', 'ev_sahibi': 'A', 'deplasman': 'B',
       'tarih': '2026-11-25T18:00:00+00:00',
       'hesaplama_zamani_utc': '2026-11-24T09:00:00+00:00',
       'tahmin': {'2.5_ust': 67}, 'kaynak_kodu': 'ornek-ucretsiz-izinli-kaynak'}
ALLOW = [{'kaynak_kodu': 'ornek-ucretsiz-izinli-kaynak', 'panel_yayin_izni': True,
          'tamamen_ucretsiz': True, 'ucretli_plan_gerekiyor': False,
          'izin_dayanagi': 'Ornek test izni; gercek kaynak degildir'}]

class IntegrationTests(unittest.TestCase):
    def test_requires_approved_source(self):
        merged = combine(BASE, [NEW], [], NOW)
        self.assertEqual(len(merged['tahminler']), 1)
        self.assertEqual(merged['v19_entegrasyon_denetimi']['v19_izin_yok'], 1)

    def test_adds_unique_future_selection(self):
        merged = combine(BASE, [NEW], ALLOW, NOW)
        self.assertEqual(len(merged['tahminler']), 2)
        self.assertEqual(merged['tahminler'][1]['model_katmani'], 'V19')
        self.assertEqual(merged['tahminler'][0], BASE['tahminler'][0])

    def test_no_existing_prediction_overwrite(self):
        old = dict(NEW, id='old', lig_kodu='sui.1')
        merged = combine(BASE, [old], ALLOW, NOW)
        self.assertEqual(len(merged['tahminler']), 1)
        self.assertEqual(merged['v19_entegrasyon_denetimi']['v19_tekrar'], 1)

    def test_started_match_is_rejected(self):
        invalid = dict(NEW, tarih='2026-11-24T08:00:00+00:00')
        merged = combine(BASE, [invalid], ALLOW, NOW)
        self.assertEqual(merged['v19_entegrasyon_denetimi']['v19_gecersiz'], 1)

    def test_prediction_after_kickoff_rejected(self):
        invalid = dict(NEW, hesaplama_zamani_utc='2026-11-25T19:00:00+00:00')
        merged = combine(BASE, [invalid], ALLOW, NOW)
        self.assertEqual(merged['v19_entegrasyon_denetimi']['v19_gecersiz'], 1)

    def test_paid_source_is_blocked(self):
        paid = [dict(ALLOW[0], ucretli_plan_gerekiyor=True)]
        merged = combine(BASE, [NEW], paid, NOW)
        self.assertEqual(len(merged['tahminler']), 1)

    def test_free_source_without_public_permission_blocked(self):
        forbidden = [dict(ALLOW[0], panel_yayin_izni=False)]
        merged = combine(BASE, [NEW], forbidden, NOW)
        self.assertEqual(len(merged['tahminler']), 1)

    def test_invalid_source_does_not_change_v18(self):
        original = list(BASE['tahminler'])
        combine(BASE, [NEW], [], NOW)
        self.assertEqual(BASE['tahminler'], original)

if __name__ == '__main__':
    unittest.main()
