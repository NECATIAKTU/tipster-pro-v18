import unittest
from datetime import datetime, timedelta, timezone
from v18_model_karsilastirma import eligible, make_history, compare

BASE = datetime(2026, 10, 20, tzinfo=timezone.utc)

def event(id_, date, home='A', away='B', hg=2, ag=1):
    return {'id':str(id_), 'date':date.isoformat(),
            'status': {'type': {'completed': True}},
            'competitions': [{'competitors': [
                {'homeAway':'home','team':{'displayName':home},'score':str(hg)},
                {'homeAway':'away','team':{'displayName':away},'score':str(ag)}]}]}

def record():
    return {'kimlik':'test.1|77','durum':'DOGRULANDI',
            'mac': {'tarih':(BASE+timedelta(days=1)).isoformat(),
                    'hesaplama_zamani_utc':BASE.isoformat(),
                    'lig_kodu':'test.1','ev_sahibi':'A','deplasman':'B',
                    'tahmin':{'1.5_ust':80,'2.5_ust':60}},
            'kilit_zamani_utc':(BASE+timedelta(hours=1)).isoformat(),
            'kilitli_secim':'1.5 UST',
            'olasiliklar':{'1.5_ust':80,'2.5_ust':60},
            'sonuc':{'ev_gol':1,'dep_gol':1}}

class Tests(unittest.TestCase):
    def setUp(self):
        self.history = [event(i, BASE - timedelta(days=20-i), hg=2, ag=1)
                        for i in range(12)]

    def fetch(self, league, day):
        return {'events':[e for e in self.history if e['date'][:10] == day.isoformat()]}

    def test_eligible_and_frozen(self):
        r = record()
        result = eligible(r)
        self.assertEqual(result['v18']['1.5_ust'], 80)
        self.assertEqual(result['gol'], 2)
        self.assertEqual(r['kilitli_secim'], '1.5 UST')

    def test_reject_backdated(self):
        r=record()
        r['mac']['hesaplama_zamani_utc']=(BASE+timedelta(days=2)).isoformat()
        self.assertIsNone(eligible(r))

    def test_no_future_or_same_day_leak(self):
        later=event(222, BASE-timedelta(hours=1), hg=10, ag=10)
        test=event(223, BASE+timedelta(hours=2), hg=10, ag=10)
        def fetch(league, day):
            events = self.fetch(league, day)['events']
            return {'events':events+[e for e in [later,test] if e['date'][:10] == day.isoformat()]}
        games, missing = make_history('test.1', BASE, 30, fetch, {}, [])
        self.assertEqual(missing, 0)
        ids=[x[1] for x in games]
        self.assertNotIn('222',ids)
        self.assertNotIn('223',ids)
        self.assertEqual(len(games),12)

    def test_equal_sample_brier(self):
        report=compare([record()], self.fetch, days=30, limit=3)
        self.assertEqual(report['incelenen'], 1)
        self.assertEqual(report['karsilastirilabilen'],1)
        self.assertEqual(report['brier_dusuk_iyidir']['1.5']['ortak_mac'],1)
        self.assertEqual(report['maclar'][0]['v18_kilitli_secim'],'1.5 UST')

    def test_incomplete_source_skips(self):
        def broken(league, day):
            raise OSError('source temporarily unavailable')
        report=compare([record()], broken, days=30, limit=2)
        self.assertEqual(report['karsilastirilabilen'],0)
        self.assertEqual(report['incelenen'],1)

    def test_no_records(self):
        report=compare([], self.fetch, days=30,limit=1)
        self.assertEqual(report['incelenen'],0)
        self.assertIsNone(report['brier_dusuk_iyidir']['3.5']['v18_brier'])

if __name__=='__main__':
    unittest.main()
