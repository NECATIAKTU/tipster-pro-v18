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

if __name__ == '__main__':
    unittest.main()
