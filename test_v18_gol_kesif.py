import unittest
from datetime import datetime,timezone
from v18_gol_kesif import historical_stats,audit
class TestPilot(unittest.TestCase):
 def test_stats(self):
  def event(i,date,h,a,hg,ag):
   return {'id':i,'date':date,'status':{'type':{'completed':True}},'competitions':[{'competitors':[{'homeAway':'home','team':{'displayName':h},'score':hg},{'homeAway':'away','team':{'displayName':a},'score':ag}]}]}
  events=[event('2','2026-11-23T12:00:00Z','B','A',3,1),event('1','2026-11-22T12:00:00Z','A','B',2,0)]
  t,p=historical_stats('x',datetime(2026,11,25,tzinfo=timezone.utc),3,lambda *_:{'events':events})
  self.assertEqual(p['tamamlanmis_mac'],2); self.assertEqual(t['A']['son_maclar'],[(2,0),(1,3)]); self.assertEqual(t['A']['ev_mac'],1); self.assertEqual(t['A']['dep_yedigi'],3)
 def test_audit(self):
  r={'durum':'DOGRULANDI','sonuc':{'toplam_gol':1},'olasiliklar':{'1.5_ust':80},'kilitli_secim':'1.5 UST','mac':{'lig_kodu':'x'}}
  a=audit([r]); self.assertEqual(len(a['yanlis_kilitli_secimler']),1); self.assertEqual(a['gruplar']['ALL|1.5_ust']['brier'],.64)
if __name__=='__main__': unittest.main()
