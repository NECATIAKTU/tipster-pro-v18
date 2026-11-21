import unittest
from datetime import date
from polonya_kaynak_pilot import parse_csv

class PolandCsvTests(unittest.TestCase):
    def test_normal_and_missing(self):
        csv_data = ("Date,Home,Away,HG,AG\n20/11/2026,Legia,Lech,2,1\n"
                    "21/11/2026,Wisla,Zaglebie,,\n23/11/2026,Future,Team,0,0\n")
        games, issues = parse_csv(csv_data.encode(), date(2026,11,21))
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]['lig_kodu'], 'pol.1')
        self.assertEqual(issues['sonuc_eksik'], 1)
        self.assertEqual(issues['gelecek_olay_ayrildi'], 1)
    def test_alt_schema(self):
        games, _ = parse_csv(b'Date,HomeTeam,AwayTeam,FTHG,FTAG\n2026-11-15,A,B,1,2\n', date(2026,11,21))
        self.assertEqual(len(games), 1)
    def test_bad_schema_rejected(self):
        with self.assertRaises(ValueError):
            parse_csv(b'wrong,headers\nX,Y\n', date(2026,11,21))
    def test_dedup(self):
        data=b'Date,Home,Away,HG,AG\n20/11/2026,A,B,1,2\n20/11/2026,A,B,1,2\n'
        games, problems = parse_csv(data, date(2026,11,21))
        self.assertEqual(len(games),1)
        self.assertEqual(problems['tekrar'],1)
if __name__ == '__main__': unittest.main()
