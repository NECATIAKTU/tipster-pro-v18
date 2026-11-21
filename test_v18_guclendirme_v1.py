import unittest
from datetime import datetime, timezone, timedelta
from v18_guclendirme_v1 import completed_games, estimate, poisson_over, predict_before_fixture


def event(i, day, hg, ag):
    return {'id': str(i), 'date': day.isoformat(), 'status': {'type': {'completed': True}},
            'competitions': [{'competitors': [
                {'homeAway':'home','team':{'displayName':'A'},'score':str(hg)},
                {'homeAway':'away','team':{'displayName':'B'},'score':str(ag)}]}]}

class Tests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.events = [event(i, self.start + timedelta(days=i), 2, 1) for i in range(12)]
    def test_no_future_leakage(self):
        fixture = {'tarih': (self.start + timedelta(days=10)).isoformat(), 'ev_sahibi':'A','deplasman':'B'}
        self.assertEqual(predict_before_fixture(self.events, fixture)['durum'], 'ARASTIRMA_TAHMINI')
        self.assertEqual(len(completed_games(self.events, self.start + timedelta(days=10))), 10)
    def test_deduplicate(self):
        self.assertEqual(len(completed_games(self.events + self.events)), 12)
    def test_all_lines_monotonic(self):
        x = estimate(completed_games(self.events), 'A', 'B')
        self.assertEqual(x['durum'], 'ARASTIRMA_TAHMINI')
        p = list(x['olasiliklar'].values())
        self.assertEqual(p, sorted(p, reverse=True))
    def test_insufficient(self):
        self.assertEqual(estimate(completed_games(self.events[:4]), 'A', 'B')['durum'], 'YETERSIZ_VERI')
    def test_poisson(self):
        self.assertAlmostEqual(poisson_over(0, 1.5), 0)
        self.assertGreater(poisson_over(3, 1.5), poisson_over(3, 2.5))

if __name__ == '__main__': unittest.main()
