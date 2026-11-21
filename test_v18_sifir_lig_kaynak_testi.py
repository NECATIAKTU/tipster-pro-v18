import unittest
from datetime import datetime, timedelta, timezone
from v18_sifir_lig_kaynak_testi import audit

class DiagnosticTest(unittest.TestCase):
    def test_no_events_is_not_broken_league(self):
        now = datetime(2026,11,21,tzinfo=timezone.utc)
        r = audit('sui.1',now,7,fetcher=lambda code,day: [])
        self.assertEqual(r['api_durumu'],'API_BOS_DONDU')
        self.assertEqual(r['pencereler']['7'].get('gelecek_mac',0),0)

    def test_event_in_seven_days(self):
        now = datetime(2026,11,21,tzinfo=timezone.utc)
        e = {'id':'123','date':(now+timedelta(days=2)).isoformat(),
             'status':{'type':{'state':'pre','completed':False}},
             'competitions':[{'competitors':[{'homeAway':'home','team':{'displayName':'A'}},
                                              {'homeAway':'away','team':{'displayName':'B'}}]}]}
        r = audit('sui.1',now,7,fetcher=lambda code,day: [e])
        self.assertEqual(r['pencereler']['7']['gelecek_mac'],1)

if __name__ == '__main__':
    unittest.main()
