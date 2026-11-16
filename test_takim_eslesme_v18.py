import unittest
from tahmin_motoru import takim_bul, indeks_olustur

class TakimEslesmeTest(unittest.TestCase):
    def test_known_aliases(self):
        pairs = [
            ('Exeter City','Exeter'),('Cheltenham Town','Cheltenham'),
            ('Burton Albion','Burton'),('Wigan Athletic','Wigan'),
            ('Colchester United','Colchester'),('Crewe Alexandra','Crewe'),
            ('Salford City','Salford'),('Northampton Town','Northampton'),
            ('Shrewsbury Town','Shrewsbury'),('Oldham Athletic','Oldham'),
            ('Swindon Town','Swindon'),('Grimsby Town','Grimsby'),
            ('Tranmere Rovers','Tranmere')]
        for original, target in pairs:
            with self.subTest(original=original):
                teams = {target:{'mac':6}}
                self.assertEqual(takim_bul(original,'E3',teams,indeks_olustur(teams)), target)
    def test_missing_team_is_not_invented(self):
        teams = {'Arsenal':{},'Chelsea':{}}
        self.assertIsNone(takim_bul('Exeter City','E3',teams,indeks_olustur(teams)))
    def test_ambiguous_alias_is_not_forced(self):
        teams = {'Exeter':{},'Exeter City':{}}
        self.assertIsNone(takim_bul('Exeter City','E3',teams,indeks_olustur(teams)))

if __name__ == '__main__': unittest.main()
