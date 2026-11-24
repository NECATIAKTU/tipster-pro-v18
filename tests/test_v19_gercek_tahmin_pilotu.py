import unittest
from datetime import datetime, timedelta, timezone
from v19_gercek_tahmin_pilotu import forecast

NOW = datetime(2026, 11, 24, 15, tzinfo=timezone.utc)


def e(i, home, away, hg, ag):
    return {'id': str(i), 'date': (NOW-timedelta(days=1)).isoformat(),
      'status': {'type': {'completed': True}}, 'competitions': [{'competitors': [
        {'homeAway': 'home', 'team': {'displayName':home}, 'score':str(hg)},
        {'homeAway': 'away', 'team': {'displayName':away}, 'score':str(ag)}]}]}


def fixture(kickoff=None):
    kickoff = kickoff or NOW + timedelta(days=1)
    return {'olusturulma_utc': NOW.isoformat(), 'maclar': [
        {'id':'eng.1|future', 'lig_kodu':'eng.1', 'tarih': kickoff.isoformat(),
         'ev_sahibi':'A','deplasman':'B'}]}


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.events=[e(str(i), 'A','B', 2,1) for i in range(12)]

    def test_real_fixture_and_history_produce_model(self):
        def fake(league,day): return {'events':self.events}
        result=forecast(fixture(),NOW,30,fetch=fake)
        self.assertEqual(len(result['tahminler']),1)
        self.assertTrue(0 <= result['tahminler'][0]['model_tahmini']['1.5_ust'] <= 100)
        self.assertFalse(result['tahminler_kilitlendi'])
        self.assertEqual(result['tahminler'][0]['model_durumu'],'PILOT_KILITLENMEDI')

    def test_insufficient_history_no_prediction(self):
        def fake(league,day): return {'events':self.events[:4]}
        result=forecast(fixture(),NOW,30,fetch=fake)
        self.assertEqual(len(result['tahminler']),0)
        self.assertEqual(result['durum']['historical_source_insufficient'],1)

    def test_started_fixture_never_predicted(self):
        result=forecast(fixture(NOW-timedelta(minutes=1)),NOW,30,fetch=lambda l,d: {'events':self.events})
        self.assertEqual(result['durum']['already_started_or_invalid_date'],1)

    def test_stale_fixture_rejected(self):
        x=fixture()
        x['olusturulma_utc']=(NOW-timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError): forecast(x,NOW,30,fetch=lambda l,d: {'events':self.events})

    def test_source_failure_excluded(self):
        def fail(league,day): raise OSError('offline')
        result=forecast(fixture(),NOW,30,fetch=fail)
        self.assertEqual(len(result['tahminler']),0)
        self.assertEqual(result['durum']['historical_source_insufficient'],1)

if __name__=='__main__': unittest.main()
