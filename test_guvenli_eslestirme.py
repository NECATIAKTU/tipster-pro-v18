import unittest
from guvenli_eslestirme import match_team, match_fixture, norm
class TestMatcher(unittest.TestCase):
 def test_exact(self): self.assertEqual(match_team('Ájax', ['Ajax'], 'N1')['status'],'matched')
 def test_approved(self): self.assertEqual(match_team('Burton Albion',['Burton'],'E2',{'E2':{'Burton Albion':'Burton'}})['status'],'matched')
 def test_cross_league(self): self.assertEqual(match_team('Burton Albion',['Burton'],'E3',{'E2':{'Burton Albion':'Burton'}})['status'],'unmatched')
 def test_no_fuzzy(self): self.assertEqual(match_team('Man Utd',['Man United'],'E0')['status'],'unmatched')
 def test_ambiguous(self): self.assertEqual(match_team('Ajax',['Ajax','Ájax'],'N1')['status'],'ambiguous')
 def test_same_team(self): self.assertEqual(match_fixture('Ajax','Ajax',['Ajax'],'N1')['status'],'review')
 def test_unknown(self): self.assertEqual(match_team('X',[],'E0')['status'],'unmatched')
if __name__=='__main__':unittest.main()
