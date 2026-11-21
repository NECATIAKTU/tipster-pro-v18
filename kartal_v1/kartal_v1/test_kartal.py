import unittest
from datetime import datetime,timedelta,timezone
from kartal import prob,legacy_select,unwrap,audit,backtest,discovery
from kartal_model import model_events,poisson_tail

class KartalTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,21,tzinfo=timezone.utc)
        self.row={'id':'lig|1','tarih':'2026-11-23T10:00:00+00:00','lig_kodu':'lig','ev_sahibi':'A','deplasman':'B','hesaplama_zamani_utc':'2026-11-21T00:00:00+00:00','tahmin':{'1.5_ust':84.0,'2.5_ust':65.5,'3.5_ust':38,'4.5_ust':18,'5.5_ust':6,'6.5_ust':1}}
    def test_no_silent_fake_prob(self):self.assertIsNone(prob('nan'));self.assertIsNone(prob(101))
    def test_reverse_line_selection(self):self.assertEqual(legacy_select(unwrap(self.row)),'2.5')
    def test_diagnostics(self):self.assertEqual(audit([self.row])['eski_secim_dagilimi']['2.5'],1)
    def test_discovery_no_mutation(self):
        x=discovery([self.row],self.now);self.assertTrue(x);self.assertEqual(self.row['tahmin']['2.5_ust'],65.5)
    def test_leakage_lock_required(self):
        archived={'kimlik':'lig|1','mac':self.row,'kilit_zamani_utc':'2026-11-24T10:00:00+00:00','durum':'DOGRULANDI','sonuc':{'toplam_gol':4},'kilitli_secim':'2.5 UST'}
        self.assertEqual(backtest([archived])['kilit_ve_zaman_dogrulanmis_skorlu'],0)
    def test_locked_metrics(self):
        archived={'kimlik':'lig|1','mac':self.row,'kilit_zamani_utc':'2026-11-22T10:00:00+00:00','durum':'DOGRULANDI','sonuc':{'toplam_gol':4},'kilitli_secim':'2.5 UST'}
        x=backtest([archived]);self.assertEqual(x['sadece_kilitli_secimler']['2.5']['kazanan'],1)
    def test_poisson_monotone(self):self.assertGreater(poisson_tail(3.1,'1.5'),poisson_tail(3.1,'2.5'))
    def test_home_away_output(self):
        start=datetime(2026,8,1,tzinfo=timezone.utc)
        games=[]
        for i in range(35):
            games.append({'tarih':(start+timedelta(days=i)).isoformat(),'lig_kodu':'test.1','ev_sahibi': ['A','B'][i%2], 'deplasman':['C','D'][i%2], 'ev_gol':2,'dep_gol':1})
        fix=[{'id':'x','tarih':'2026-11-22T12:00:00+00:00','lig_kodu':'test.1','ev_sahibi':'A','deplasman':'C'}]
        x=model_events(games,fix,self.now); self.assertEqual(x['analizler'][0]['durum'],'DENEYSEL_HESAPLANDI')
    def test_no_future_match(self):
        future=[{'tarih':'2026-11-25T12:00:00+00:00','lig_kodu':'x','ev_sahibi':'A','deplasman':'B','ev_gol':8,'dep_gol':8}]
        fix=[{'id':'x','tarih':'2026-11-22T12:00:00+00:00','lig_kodu':'x','ev_sahibi':'A','deplasman':'B'}]
        x=model_events(future,fix,self.now);self.assertEqual(x['analizler'][0]['durum'],'INCELEME')
if __name__=='__main__':unittest.main()
