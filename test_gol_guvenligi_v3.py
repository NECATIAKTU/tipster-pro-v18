import unittest
from gol_guclendirme_v1 import valid_history, over_probability

class GolGuvenligi(unittest.TestCase):
    def setUp(self):
        self.base={"league":"E0","status":"FT","home":"A","away":"B","home_goals":2,"away_goals":1}
    def test_recent_match_blocked(self):
        m=dict(self.base,kickoff="2026-11-10T12:00:00Z")
        self.assertEqual(valid_history([m],"E0","2026-11-10T13:30:00Z"),[])
    def test_old_match_allowed(self):
        m=dict(self.base,kickoff="2026-11-10T10:00:00Z")
        self.assertEqual(len(valid_history([m],"E0","2026-11-10T13:30:00Z")),1)
    def test_explicit_completion_after_cutoff_blocked(self):
        m=dict(self.base,kickoff="2026-11-10T10:00:00Z",finished_at="2026-11-10T14:00:00Z")
        self.assertEqual(valid_history([m],"E0","2026-11-10T13:30:00Z"),[])
    def test_probabilities_monotonic(self):
        self.assertTrue(all(over_probability(3.1,a)>=over_probability(3.1,b) for a,b in zip([1.5,2.5,3.5,4.5,5.5],[2.5,3.5,4.5,5.5,6.5])))
if __name__=="__main__":unittest.main()
