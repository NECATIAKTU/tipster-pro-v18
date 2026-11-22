import json,math,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from v19_core.engine import utc,poisson_tail,sanitize,forecast,select,walk_forward
from v19_core.audit import archive_audit
from v19_core.loaders import read_csv

BASE=datetime(2026,1,1,tzinfo=timezone.utc)
def sample(n=100):
    out=[]
    for i in range(n):
        home=('A','B','C','D')[i%4]
        away=('C','D','A','B')[(i//4)%4]
        if home==away:away='Z'
        out.append({'tarih':(BASE+timedelta(days=i)).isoformat(),'lig_kodu':'DEMO',
                    'ev_sahibi':home,'deplasman':away,'ev_gol':i%4,'dep_gol':i%3})
    return out

class EngineTests(unittest.TestCase):
    def test_poisson_known(self):
        self.assertAlmostEqual(poisson_tail(2,1),1-math.exp(-2)*3,places=10)
    def test_probabilities_monotone(self):
        self.assertTrue(all(poisson_tail(2.8,x)>=poisson_tail(2.8,y) for x,y in zip((1.5,2.5,3.5,4.5,5.5),(2.5,3.5,4.5,5.5,6.5))))
    def test_invalid_lambda(self):
        with self.assertRaises(ValueError):poisson_tail(-1,2.5)
    def test_no_naive_datetime(self):
        with self.assertRaises(ValueError):utc('2026-01-01T10:00:00')
    def test_duplicate_removed(self):
        rows,report=sanitize(sample(3)+[sample(3)[1]])
        self.assertEqual(len(rows),3);self.assertEqual(report['mukerrer'],1)
    def test_no_future_training(self):
        rows,_=sanitize(sample())
        fixture={'tarih':(BASE+timedelta(days=75)).isoformat(),'lig_kodu':'DEMO','ev_sahibi':'A','deplasman':'C'}
        a=forecast(rows,fixture)
        future={'tarih':(BASE+timedelta(days=110)).isoformat(),'lig_kodu':'DEMO','ev_sahibi':'A','deplasman':'C','ev_gol':20,'dep_gol':0}
        future_clean,_=sanitize([future])
        b=forecast(rows+future_clean,fixture)
        self.assertEqual(a,b)
    def test_no_default_betting_pick(self):
        model={'durum':'MODEL_HESAPLANDI','olasiliklar':{'1.5_ust':99},'veri':{'ev_saha':4,'dep_saha':4}}
        self.assertEqual(select(model)['karar'],'INCELEME')
    def test_venue_data_low(self):
        matches,_=sanitize(sample(40))
        f={'tarih':(BASE+timedelta(days=45)).isoformat(),'lig_kodu':'DEMO','ev_sahibi':'A','deplasman':'B'}
        out=forecast(matches,f)
        self.assertIn(out['durum'],('PAS','MODEL_HESAPLANDI'))
    def test_future_skipped(self):
        x=walk_forward(sample(90))
        self.assertEqual(x['giris'],90)
        self.assertIn('1.5_ust',x['metrikler'])
    def test_archive_time_leak_rejected(self):
        rec={'mac':{'tarih':'2026-01-01T12:00:00+00:00','hesaplama_zamani_utc':'2026-01-01T13:00:00+00:00'},
             'kilit_zamani_utc':'2026-01-01T11:00:00+00:00','durum':'DOGRULANDI','sonuc':{'toplam_gol':2},
             'olasiliklar':{f'{l:.1f}_ust':50 for l in (1.5,2.5,3.5,4.5,5.5,6.5)}}
        report=archive_audit([rec]);self.assertEqual(report['dogrulanmis_ve_zaman_gecerli'],0)
    def test_archive_correct_locked_score(self):
        rec={'mac':{'tarih':'2026-01-01T12:00:00+00:00','hesaplama_zamani_utc':'2026-01-01T10:00:00+00:00'},
             'kilit_zamani_utc':'2026-01-01T11:00:00+00:00','durum':'DOGRULANDI','sonuc':{'toplam_gol':3},
             'kilitli_secim':'2.5 ÜST','olasiliklar':{f'{l:.1f}_ust':50 for l in (1.5,2.5,3.5,4.5,5.5,6.5)}}
        report=archive_audit([rec]);self.assertEqual(report['kilitli_secimler']['2.5 UST']['dogru'],1)
    def test_csv_loader(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'E0.csv';p.write_text('Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/2026,A,B,2,1\n',encoding='utf-8')
            matches,bad=read_csv([str(p)])
            self.assertEqual(bad,0);self.assertEqual(len(matches),1)
    def test_shrinkage_stability(self):
        events,_=sanitize(sample(100))
        f={'tarih':(BASE+timedelta(days=110)).isoformat(),'lig_kodu':'DEMO','ev_sahibi':'A','deplasman':'C'}
        out=forecast(events,f)
        self.assertEqual(out['durum'],'MODEL_HESAPLANDI')
        self.assertTrue(0<=out['olasiliklar']['6.5_ust']<=out['olasiliklar']['1.5_ust']<=100)

if __name__=='__main__':unittest.main()
