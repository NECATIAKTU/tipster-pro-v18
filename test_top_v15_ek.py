import unittest
from datetime import datetime,date,timezone
from tipster_top_listeler import run
NOW=datetime(2026,11,10,12,tzinfo=timezone.utc)
class TestV15(unittest.TestCase):
 def test_two_source_ids_same_match(self):
  base={'tarih_utc':'2026-11-11T19:00:00+00:00','kaynak':'A','hesaplama_zamani':'2026-11-10T11:00:00+00:00','mac':'Team A - Team B','1.5_ust':'85','2.5_ust':'75','3.5_ust':'66'}
  a=dict(base,id='a');b=dict(base,id='b',kaynak='B')
  day,week,audit=run([a,b],date(2026,11,11),NOW)
  self.assertEqual(len(day),1);self.assertEqual(len(week),1)
  self.assertEqual(audit['gunluk']['reddedilen'].get('mukerrer_mac'),1)
 def test_missing_time_is_flagged_not_certified(self):
  a={'id':'x','tarih_utc':'2026-11-11T19:00:00+00:00','kaynak':'A','mac':'A - B','1.5_ust':'85','2.5_ust':'75','3.5_ust':'66'}
  _,_,audit=run([a],date(2026,11,11),NOW)
  self.assertEqual(audit['gunluk']['reddedilen'].get('zaman_dogrulanamadi'),1)
  self.assertEqual(len(run([a],date(2026,11,11),NOW)[0]),0)
if __name__=='__main__':unittest.main()
