import unittest
from datetime import datetime,date,timezone
from tipster_top_listeler import run
from haftalik_kapasite import dt
NOW=datetime(2026,11,10,12,tzinfo=timezone.utc)
class V17Security(unittest.TestCase):
    def test_missing_calculation_time_rejected(self):
        a={'id':'x','tarih_utc':'2026-11-11T19:00:00+00:00','kaynak':'A','mac':'A - B','1.5_ust':'85','2.5_ust':'75','3.5_ust':'66'}
        day,week,audit=run([a],date(2026,11,11),NOW)
        self.assertEqual((len(day),len(week)),(0,0))
        self.assertEqual(audit['gunluk']['reddedilen'].get('zaman_dogrulanamadi'),1)
    def test_naive_capacity_timestamp_rejected(self):
        self.assertIsNone(dt('2026-11-11T19:00:00'))
    def test_future_calculation_time_rejected(self):
        a={'id':'x','tarih_utc':'2026-11-11T19:00:00+00:00','hesaplama_zamani':'2026-11-11T18:00:00+00:00','kaynak':'A','mac':'A - B','1.5_ust':'85','2.5_ust':'75','3.5_ust':'66'}
        day,week,_=run([a],date(2026,11,11),NOW)
        self.assertEqual((len(day),len(week)),(0,0))
if __name__=='__main__':unittest.main()
