import unittest
from datetime import datetime,timedelta,timezone
from gol_guclendirme_v1 import valid_history,over_probability,predict

BASE=datetime(2026,1,1,tzinfo=timezone.utc)
def fixture(i, league='E0'):
    return {'league':league,'kickoff':(BASE+timedelta(days=i)).isoformat(),'home':'A' if i%2==0 else 'C','away':'B' if i%2==0 else 'D','home_goals':2,'away_goals':1,'status':'FT'}

class TestGoalModel(unittest.TestCase):
    def setUp(self):
        self.matches=[fixture(i) for i in range(40)]
        self.kickoff=(BASE+timedelta(days=50)).isoformat()
    def test_probability_order(self):
        ps=[over_probability(2.8,x) for x in (1.5,2.5,3.5,4.5,5.5,6.5)]
        self.assertTrue(all(a>=b for a,b in zip(ps,ps[1:])))
    def test_no_future_leak(self):
        self.assertEqual(len(valid_history(self.matches,'E0',(BASE+timedelta(days=20)).isoformat())),20)
    def test_duplicate_removed(self):
        self.assertEqual(len(valid_history(self.matches+[self.matches[0]],'E0',self.kickoff)),40)
    def test_cross_league(self):
        self.assertEqual(len(valid_history(self.matches,'E1',self.kickoff)),0)
    def test_min_history(self):
        self.assertEqual(predict(self.matches[:3],'E0','A','B',self.kickoff)['decision'],'RISKLI')
    def test_valid_model(self):
        p=predict(self.matches,'E0','A','B',self.kickoff)
        self.assertEqual(p['decision'],'MODEL_OUTPUT_NOT_CALIBRATED')
        self.assertGreater(p['over_probabilities']['1.5'],p['over_probabilities']['6.5'])
    def test_timezone_required(self):
        with self.assertRaises(ValueError):valid_history(self.matches,'E0','2026-02-01T00:00:00')
    def test_no_invalid_score(self):
        bad=dict(self.matches[0],home_goals=-1)
        self.assertEqual(len(valid_history([bad],'E0',self.kickoff)),0)
    def test_no_live_game(self):
        live=dict(self.matches[0],status='LIVE')
        self.assertEqual(len(valid_history([live],'E0',self.kickoff)),0)
    def test_invalid_lambda(self):
        with self.assertRaises(ValueError):over_probability(float('nan'),2.5)

if __name__=='__main__':unittest.main()
