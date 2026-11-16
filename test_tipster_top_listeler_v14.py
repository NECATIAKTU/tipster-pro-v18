import unittest
from datetime import datetime,date,timezone
from tipster_top_listeler import run
NOW=datetime(2026,11,10,12,tzinfo=timezone.utc)
def row(id,when,p15=85,p25=75,p35=66):
 return {'id':id,'tarih_utc':when,'kaynak':'TEST','hesaplama_zamani':'2026-11-10T11:00:00+00:00','mac':'A - B','1.5_ust':str(p15),'2.5_ust':str(p25),'3.5_ust':str(p35)}
class TopTests(unittest.TestCase):
 def test_dedup(self):
  a=row('x','2026-11-11T19:00:00+00:00');day,week,audit=run([a,a],date(2026,11,11),NOW)
  self.assertEqual(len(day),1);self.assertEqual(len(week),1)
 def test_started_rejected(self):
  a=row('x','2026-11-09T19:00:00+00:00');day,week,_=run([a],date(2026,11,9),NOW)
  self.assertEqual(len(week),0)
 def test_invalid_probability(self):
  a=row('x','2026-11-11T19:00:00+00:00',70,80,60);day,week,_=run([a],date(2026,11,11),NOW)
  self.assertEqual(len(week),0)
 def test_highest_market(self):
  a=row('x','2026-11-11T19:00:00+00:00');day,week,_=run([a],date(2026,11,11),NOW)
  self.assertEqual(week[0]['tahmin'],'3.5 ÜST')
 def test_threshold(self):
  a=row('x','2026-11-11T19:00:00+00:00',74,64,30);day,week,_=run([a],date(2026,11,11),NOW)
  self.assertEqual(len(week),0)
 def test_late_calculation(self):
  a=row('x','2026-11-11T19:00:00+00:00');a['hesaplama_zamani']='2026-11-11T20:00:00+00:00'
  day,week,_=run([a],date(2026,11,11),NOW);self.assertEqual(len(week),0)
if __name__=='__main__':unittest.main()
