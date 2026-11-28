import unittest
from datetime import datetime, timezone, timedelta
from gercek_tahmin_v18 import historical_stats, produce

NOW = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)

class Tests(unittest.TestCase):
    def test_stale_rejected(self):
        with self.assertRaisesRegex(ValueError, 'FIKSTUR_GUNCEL_DEGIL'):
            produce({'olusturulma_utc':'2026-11-09T00:00:00+00:00', 'maclar':[]}, NOW)

    def test_real_history_scores_and_dedup(self):
        def fetch(lig, day):
            return {'events':[{'id':str(day), 'status':{'type':{'completed':True}}, 'competitions':[{'competitors':[
                {'homeAway':'home','team':{'displayName':'Home City'},'score':'2'},
                {'homeAway':'away','team':{'displayName':'Away United'},'score':'1'}]}]}]}
        stats, audit = historical_stats('eng.1', NOW, 30, fetch)
        self.assertEqual(stats['Home City']['mac'], 30)
        self.assertEqual(audit['tamamlanmis_mac'], 30)

    def test_predict_with_mock_verified_history(self):
        def fetch(lig, day):
            return {'events':[{'id':str(day), 'status':{'type':{'completed':True}}, 'competitions':[{'competitors':[
                {'homeAway':'home','team':{'displayName':'Home City'},'score':'2'},
                {'homeAway':'away','team':{'displayName':'Away United'},'score':'1'}]}]}]}
        fixture={'olusturulma_utc':NOW.isoformat(),'maclar':[{'id':'test-1','lig_kodu':'eng.1', 'tarih':(NOW+timedelta(days=2)).isoformat(), 'ev_sahibi':'Home City','deplasman':'Away United'}]}
        result=produce(fixture, NOW, 30, fetch)
        self.assertEqual(len(result['tahminler']),1)
        self.assertIn('tahmin', result['tahminler'][0])
    def test_form_ve_ev_deplasman(self):
        def fetch(lig, day):
            return {'events': [{
                'id': str(day),
                'date': day.isoformat(),
                'status': {'type': {'completed': True}},
                'competitions': [{'competitors': [
                    {'homeAway': 'home', 'team': {'displayName': 'Home City'}, 'score': str(day.day)},
                    {'homeAway': 'away', 'team': {'displayName': 'Away United'}, 'score': '1'}
                ]}]
            }]}

        stats, audit = historical_stats('eng.1', NOW, 5, fetch)
        self.assertEqual(stats['Home City']['ev_mac'], 5)
        self.assertEqual(stats['Away United']['dep_mac'], 5)
        self.assertEqual(stats['Home City']['ev_attigi'], 45)
        self.assertEqual(stats['Away United']['dep_yedigi'], 45)
        self.assertEqual(stats['Home City']['son_maclar'][-1], (11, 1))
    def test_negatif_binom(self):
        from gol_modeli import negatif_binom_ust, poisson_ust
        self.assertAlmostEqual(
            negatif_binom_ust(3, 3, 2),
            poisson_ust(3, 2)
        )
        p = [negatif_binom_ust(3, 6, k)
             for k in range(1, 7)]
        self.assertTrue(all(0 <= x <= 1 for x in p))
        self.assertTrue(all(a >= b for a, b in zip(p, p[1:])))
        self.assertAlmostEqual(negatif_binom_ust(2, 4, 2), 0.3125)
if __name__ == '__main__':
    unittest.main()
