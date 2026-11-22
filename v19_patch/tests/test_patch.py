import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from v19_patch.analysis import normalize_event,load_history,forecast,poisson_tail,archive_report,publication_guard,backtest
from v19_patch.cli import main

BASE=datetime(2025,1,1,tzinfo=timezone.utc)
def sample(n=110):
    out=[]
    for i in range(n):
        home=['A','B','C','D'][i%4];away=['B','C','D','A'][i%4]
        out.append({'id':str(i),'lig_kodu':'DEMO','tarih':(BASE+timedelta(days=i)).isoformat(),
                    'ev_sahibi':home,'deplasman':away,'ev_gol':i%4,'dep_gol':i%3})
    return out
class PatchTests(unittest.TestCase):
    def test_poisson(self):self.assertAlmostEqual(poisson_tail(2.0,1.5),1-3*2.718281828459045**-2,places=8)
    def test_future_skipped(self):
        rows=sample();target={k:rows[95][k] for k in ('tarih','lig_kodu','ev_sahibi','deplasman')}
        x=forecast(rows[:95],target);z=forecast(rows[:95]+[rows[105]],target)
        self.assertEqual(x,z)
    def test_same_day_excluded(self):
        rows=sample(100);fx=dict(rows[-1]);now=BASE+timedelta(days=100)
        fx['tarih']=now.isoformat()
        a=forecast(rows,fx);b=forecast(rows+[dict(rows[-1],id='extra',ev_gol=25,tarih=now.replace(hour=1).isoformat())],fx)
        self.assertEqual(a,b)
    def test_espn(self):
        e={'id':'123','date':'2026-01-01T12:00:00Z','lig':'eng.1','status':{'type':{'completed':True}},'competitions':[{'competitors':[{'homeAway':'home','score':'2','team':{'displayName':'A'}},{'homeAway':'away','score':'1','team':{'displayName':'B'}}]}]}
        self.assertEqual(normalize_event(e)['ev_gol'],2)
    def test_archive_and_publication(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);a=d/'arsiv.json';p=d/'panel.json';o=d/'rapor.json'
            row={'kimlik':'x|1','durum':'DOGRULANDI','mac':{'tarih':'2026-01-02T12:00:00Z','hesaplama_zamani_utc':'2026-01-01T12:00:00Z','lig_kodu':'x'},'kilit_zamani_utc':'2026-01-01T13:00:00Z','kilitli_secim':'2.5 UST','sonuc':{'toplam_gol':3},'olasiliklar':{'2.5_ust':60}}
            a.write_text(json.dumps([row]));p.write_text(json.dumps({'tahminler':[]}))
            self.assertEqual(archive_report(a)['dogru'],1)
            self.assertFalse(publication_guard(a,p)['onay'])
            main(['--arsiv',str(a),'--panel',str(p),'--cikti',str(o)])
            self.assertTrue(o.exists())
            with self.assertRaises(SystemExit):main(['--arsiv',str(a),'--cikti',str(o)])
    def test_backtest(self):
        result=backtest(sample(),limit=25)
        self.assertEqual(result['giris'],25)
        self.assertIn('2.5_ust',result['cizgiler'])
if __name__=='__main__':unittest.main()
