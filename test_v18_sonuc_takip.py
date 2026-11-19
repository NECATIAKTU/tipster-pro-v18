"""Deterministic offline integration tests. No real ESPN calls or repository writes."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import v18_sonuc_takip as v

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
CFG = {'secim_politikasi':'YUKSEK_CIZGIDEN_BASLA_V1', 'otomatik_secim_aktif':True,
       'esikler':{'1.5':75,'2.5':65,'3.5':65,'4.5':65,'5.5':65,'6.5':65}}


def match(id='7', start=None, created=None, prob=None, league='eng.1'):
    start = start or NOW + timedelta(days=2)
    return {'id':f'{league}|{id}', 'lig_kodu':league, 'tarih':start.isoformat(),
            'hesaplama_zamani_utc':(created or min(start-timedelta(hours=5), NOW-timedelta(minutes=1))).isoformat(),
            'ev_sahibi':'Home', 'deplasman':'Away',
            'tahmin':prob or {'1.5_ust':88,'2.5_ust':77,'3.5_ust':59,'4.5_ust':29}}


def result_event(id='7', hg=2, ag=1, completed=True):
    return {'id':id, 'status':{'type':{'completed':completed}},
            'competitions':[{'competitors':[
                {'homeAway':'home','score':str(hg)},
                {'homeAway':'away','score':str(ag)}]}]}


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.a=base/'archive.json'; self.o=base/'results.json'; self.c=base/'settings.json'; self.s=base/'source.json'
        self.c.write_text(json.dumps(CFG))
        for name, dest in [('ARSIV',self.a),('SONUCLAR',self.o),('AYARLAR',self.c)]:
            patcher=patch.object(v,name,dest); patcher.start(); self.addCleanup(patcher.stop)

    def source(self, matches):
        self.s.write_text(json.dumps({'model':'TIPSTER PRO V18','tahminler':matches}))

    def test_id_normalization_and_rejection(self):
        self.assertEqual(v.kimlik(match()),'eng.1|7')
        self.assertEqual(v.kimlik(dict(match(),id='7')),'eng.1|7')
        self.assertIsNone(v.kimlik(dict(match(),id='arg.1|7')))
        self.assertIsNone(v.kimlik(dict(match(),id='eng.1|7|8')))
        self.assertIsNone(v.kimlik(dict(match(),lig_kodu='')))

    def test_percent_and_invalid_probabilities(self):
        self.assertEqual(v.olasiliklar({'tahmin':{'1.5_ust':'75,5%','2.5_ust':110,'3.5_ust':-1}}),{'1.5_ust':75.5})

    def test_selection_thresholds_and_risk(self):
        self.assertEqual(v.kilitli_secim_uret({'1.5_ust':74}), 'RISKLI')
        self.assertEqual(v.kilitli_secim_uret({'1.5_ust':78,'2.5_ust':66}), '2.5 UST')
        self.assertEqual(v.kilitli_secim_uret({'1.5_ust':78,'5.5_ust':66}), '5.5 UST')
        self.assertEqual(v.kilitli_secim_uret({}), 'RISKLI')

    def test_disabled_selection_never_grades(self):
        self.c.write_text(json.dumps(dict(CFG, otomatik_secim_aktif=False)))
        self.source([match(start=NOW+timedelta(hours=6))])
        v.arsivle(self.s,now=NOW)
        self.assertNotIn('kilitli_secim',json.loads(self.a.read_text())[0])

    def test_archive_first_pick_is_immutable(self):
        original=match(prob={'1.5_ust':80,'2.5_ust':66})
        self.source([original,original])
        self.assertEqual(v.arsivle(self.s,now=NOW),1)
        self.source([match(prob={'1.5_ust':81,'5.5_ust':80})])
        self.assertEqual(v.arsivle(self.s,now=NOW),0)
        a=json.loads(self.a.read_text())
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]['kilitli_secim'],'2.5 UST')
        self.assertEqual(a[0]['mac']['tahmin']['2.5_ust'],66)

    def test_started_or_late_predictions_cannot_archive(self):
        bad=[match(id='1', start=NOW-timedelta(minutes=1)),
             match(id='2',start=NOW+timedelta(hours=1),created=NOW+timedelta(hours=2)),
             dict(match(id='3'), tarih='not-a-date')]
        self.source(bad)
        self.assertEqual(v.arsivle(self.s,now=NOW),0)
        self.assertFalse(self.a.exists())

    def test_both_completed_and_pending_exact_match(self):
        first=match(id='7',start=NOW-timedelta(hours=4))
        second=match(id='8',start=NOW-timedelta(hours=3))
        a=[{'kimlik':v.kimlik(m),'mac':m,'durum':'BEKLIYOR','sonuc':None,
            'kilit_zamani_utc':(NOW-timedelta(hours=10)).isoformat(),
            'kilitli_secim':'2.5 UST','olasiliklar':v.olasiliklar(m)} for m in [first,second]]
        self.a.write_text(json.dumps(a))
        def fetch(league,day): return {'events':[result_event('7',2,1),result_event('8',3,2,False)]}
        data=v.kontrol(fetch=fetch,now=NOW)
        self.assertEqual(data['dogru'],1)
        self.assertEqual(data['yanlis'],0)
        self.assertEqual(data['dogrulanan_mac'],1)
        self.assertEqual(data['bekleyen_mac'],1)

    def test_legacy_unselected_never_backfilled(self):
        m=match(start=NOW-timedelta(days=2))
        self.a.write_text(json.dumps([{'kimlik':v.kimlik(m),'mac':m,'durum':'BEKLIYOR',
                         'sonuc':None,'kilit_zamani_utc':(NOW-timedelta(days=3)).isoformat(),
                         'olasiliklar':v.olasiliklar(m)}]))
        data=v.kontrol(fetch=lambda league,day: {'events':[result_event()]},now=NOW)
        self.assertEqual((data['dogru'],data['yanlis'],data['dogrulanan_mac']),(0,0,1))
        self.assertNotIn('tahmin_sonucu',data['kayitlar'][0])

    def test_wrong_grade_and_no_past_kickoff_lock(self):
        m=match(start=NOW-timedelta(days=2))
        records=[{'kimlik':v.kimlik(m),'mac':m,'durum':'BEKLIYOR','sonuc':None,
                  'kilit_zamani_utc':(NOW-timedelta(days=3)).isoformat(),
                  'kilitli_secim':'2.5 UST','olasiliklar':v.olasiliklar(m)},
                 {'kimlik':'eng.1|8','mac':dict(m,id='eng.1|8'),'durum':'BEKLIYOR','sonuc':None,
                  'kilit_zamani_utc':NOW.isoformat(),'kilitli_secim':'2.5 UST', 'olasiliklar':v.olasiliklar(m)}]
        self.a.write_text(json.dumps(records))
        data=v.kontrol(fetch=lambda league,day: {'events':[result_event('7',1,1),result_event('8',1,1)]},now=NOW)
        self.assertEqual((data['dogru'],data['yanlis'],data['dogrulanan_mac']),(0,1,2))
        self.assertNotIn('tahmin_sonucu',data['kayitlar'][1])

    def test_no_future_api_requests(self):
        m=match(start=NOW+timedelta(days=8))
        calls=[]
        def fetch(league,day): calls.append((league,day)); return {'events':[]}
        self.assertFalse(v.espn_sonuclari([{'mac':m,'durum':'BEKLIYOR'}],fetch=fetch,now=NOW))
        self.assertEqual(calls,[])

    def test_results_persist_when_api_unavailable(self):
        m=match(start=NOW-timedelta(days=2))
        self.a.write_text(json.dumps([{'kimlik':v.kimlik(m),'mac':m,'durum':'BEKLIYOR','sonuc':None,
                    'kilit_zamani_utc':(NOW-timedelta(days=3)).isoformat(),
                    'kilitli_secim':'2.5 UST','olasiliklar':v.olasiliklar(m)}]))
        v.kontrol(fetch=lambda l,d: {'events':[result_event()]},now=NOW)
        second=v.kontrol(fetch=lambda l,d: (_ for _ in ()).throw(OSError('offline')),now=NOW+timedelta(days=1))
        self.assertEqual((second['dogrulanan_mac'],second['dogru']),(1,1))

    def test_historical_score_cannot_be_changed_silently(self):
        m=match(start=NOW-timedelta(days=2))
        self.a.write_text(json.dumps([{'kimlik':v.kimlik(m),'mac':m,'durum':'DOGRULANDI',
                 'sonuc':{'ev_gol':2,'dep_gol':1,'toplam_gol':3,'skor':'2-1'},
                 'kilit_zamani_utc':(NOW-timedelta(days=3)).isoformat(),
                 'kilitli_secim':'2.5 UST','olasiliklar':v.olasiliklar(m)}]))
        data=v.kontrol(fetch=lambda l,d: {'events':[result_event('7',0,0)]},now=NOW)
        self.assertEqual(data['kayitlar'][0]['sonuc']['skor'],'2-1')

    def test_invalid_and_partial_esports_not_scored(self):
        self.assertIsNone(v._completed_event(result_event(completed=False)))
        self.assertIsNone(v._completed_event({'id':'7','status':{'type':{'completed':True}},'competitions':[]}))

    def test_summary_invariant(self):
        self.a.write_text('[]')
        data=v.kontrol(fetch=lambda l,d: {'events':[]},now=NOW)
        self.assertEqual(data['basari_yuzdesi'],None)
        self.assertEqual(data['degerlendirilen_tahmin'],0)
        self.assertTrue(self.o.exists())

    def test_bad_model_rejected(self):
        self.s.write_text('{}')
        with self.assertRaisesRegex(ValueError,'Gecersiz V18'):
            v.arsivle(self.s,now=NOW)


if __name__ == '__main__':
    unittest.main()
