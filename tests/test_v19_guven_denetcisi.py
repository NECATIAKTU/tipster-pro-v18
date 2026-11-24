import unittest
from datetime import datetime, timezone, timedelta
from v19_guven_denetcisi import audit, metrics, valid_record, settled, wilson_lower

NOW=datetime(2026,11,24,12,tzinfo=timezone.utc)

def item(*,start=1, made=-1, locked=-1, verified=None, goals=3, league='eng.1', line='1.5', prob=83, status='BEKLIYOR', choice=None):
    kickoff=NOW+timedelta(days=start)
    made_at=NOW+timedelta(days=made)
    lock_at=NOW+timedelta(days=locked,hours=1)
    r={'kimlik':'abc','mac':{'id':'abc','lig_kodu':league,'lig':'LIG','ev_sahibi':'A','deplasman':'B',
     'tarih':kickoff.isoformat(),'hesaplama_zamani_utc':made_at.isoformat()},
     'kilit_zamani_utc':lock_at.isoformat(),'kilitli_secim':choice or line+' UST',
     'olasiliklar':{line+'_ust':prob},'durum':status}
    if verified is not None:
        r['sonuc']={'ev_gol':goals,'dep_gol':0}
        r['sonuc_dogrulama_zamani_utc']=(NOW+timedelta(days=verified)).isoformat()
    return r

class Tests(unittest.TestCase):
    def test_empty(self):self.assertEqual(audit([], NOW)['toplam_aday'],0)
    def test_invalid_archive(self):
        with self.assertRaises(ValueError):audit({}, NOW)
    def test_future_candidate_unproven(self):
        x=audit([item()],NOW)
        self.assertEqual(x['top20'][0]['durum'],'YETERSIZ_KANIT')
    def test_invalid_lock_rejected(self):
        self.assertIsNone(valid_record(item(start=1,locked=2)))
    def test_no_backdated_results(self):
        r=item(start=-3,made=-4,locked=-4,verified=-1,status='DOGRULANDI')
        x=audit([r,item(made=-2)],NOW)
        self.assertEqual(x['top20'][0]['genel_cizgi']['ornek'],0)
    def test_valid_verified(self):
        r=item(start=-3,made=-4,locked=-4,verified=-2,status='DOGRULANDI')
        self.assertIsNotNone(settled(r))
    def test_unverified_result_excluded(self):
        r=item(start=-3,made=-4,locked=-4,verified=None,status='DOGRULANDI')
        self.assertIsNone(settled(r))
    def test_riskli_not_candidate(self):
        self.assertEqual(audit([item(choice='RISKLI')],NOW)['toplam_aday'],0)
    def test_wilson_penalizes_tiny_sample(self):
        self.assertLess(wilson_lower(3,3),.75)
    def test_perfect_probabilities(self):
        s=metrics([{'hit':1,'prob':1.0},{'hit':0,'prob':0.0}])
        self.assertEqual(s['brier'],0.0)
    def test_percent_nan_rejected(self):
        self.assertEqual(audit([item(prob=float('nan'))],NOW)['toplam_aday'],0)
    def test_started_not_recommended(self):
        self.assertEqual(audit([item(start=-1,made=-3,locked=-2)],NOW)['toplam_aday'],0)

if __name__=='__main__':unittest.main()
