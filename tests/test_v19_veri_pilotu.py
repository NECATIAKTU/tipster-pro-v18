import unittest
from datetime import datetime, timezone, timedelta
from v19_veri_pilotu import collect_teams, audit_archive

NOW = datetime(2026, 11, 24, 15, tzinfo=timezone.utc)


def event(id_, day, home='A', away='B', hs=3, ass=1, complete=True):
    return {'id': id_, 'date': day.isoformat(), 'status': {'type': {'completed': complete}},
            'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'displayName': home}, 'score': str(hs)},
                {'homeAway': 'away', 'team': {'displayName': away}, 'score': str(ass)}]}]}


def record(choice='1.5 UST', start=None, confirmed=True):
    start = start or NOW - timedelta(days=2)
    return {'kimlik': 'eng.1|A', 'mac': {'tarih': start.isoformat(), 'lig_kodu':'eng.1',
            'hesaplama_zamani_utc': (start-timedelta(hours=2)).isoformat()},
            'kilit_zamani_utc': (start-timedelta(hours=1)).isoformat(),
            'durum': 'DOGRULANDI' if confirmed else 'BEKLIYOR',
            'kilitli_secim': choice, 'olasiliklar': {'1.5_ust': 80.0},
            'sonuc': {'ev_gol': 2, 'dep_gol': 1} if confirmed else None,
            'sonuc_dogrulama_zamani_utc': (start+timedelta(hours=3)).isoformat()}


class PilotTests(unittest.TestCase):
    def test_counts_and_home_away(self):
        d = NOW - timedelta(days=1)
        events = [event('1', d, 'A','B',3,1), event('2', d+timedelta(hours=1),'B','A',0,2)]
        t, report = collect_teams('eng.1', NOW, 1, lambda lg, day: {'events':events})
        self.assertEqual(report['completed_matches'], 2)
        self.assertEqual(t['A']['mac'],2)
        self.assertEqual(t['A']['ev_attigi'],3)
        self.assertEqual(t['A']['dep_attigi'],2)
        self.assertEqual(t['B']['ev_attigi'],0)
        self.assertEqual(t['A']['son_maclar'],[(3,1),(2,0)])

    def test_future_completed_match_ignored(self):
        t, r = collect_teams('eng.1',NOW,1,lambda l,d:{'events':[event('f',NOW+timedelta(hours=1))]})
        self.assertEqual(r['completed_matches'],0)

    def test_duplicate_events_deduplicated(self):
        t, r = collect_teams('eng.1',NOW,2,lambda l,d:{'events':[event('1',NOW-timedelta(days=1))]})
        self.assertEqual(r['completed_matches'],1)

    def test_incomplete_and_invalid_scores_excluded(self):
        d=NOW-timedelta(days=1)
        t,r=collect_teams('eng.1',NOW,1,lambda l,day:{'events':[event('a',d,complete=False),event('b',d,hs=-1)]})
        self.assertEqual(r['completed_matches'],0)

    def test_fetch_failure_visible(self):
        def bad(l,d): raise TimeoutError()
        t,r=collect_teams('eng.1',NOW,1,bad)
        self.assertEqual(r['failure_days'],1)

    def test_verified_locked_over(self):
        d=audit_archive([record()],NOW)
        self.assertEqual(d['verified_locked_over'],1)
        self.assertEqual(d['correct'],1)
        self.assertEqual(d['largest_group'],1)

    def test_post_kickoff_lock_rejected(self):
        x=record()
        x['kilit_zamani_utc']=(NOW-timedelta(days=1)).isoformat()
        d=audit_archive([x],NOW)
        self.assertEqual(d['verified_locked_over'],0)
        self.assertEqual(d['excluded']['invalid_pre_match_lock_or_timestamp'],1)

    def test_pending_not_used_as_success(self):
        x=record(confirmed=False)
        d=audit_archive([x],NOW)
        self.assertEqual(d['verified_locked_over'],0)
        self.assertEqual(d['excluded']['pending_or_unverified'],1)

    def test_duplicates_not_double_counted(self):
        x=record()
        d=audit_archive([x,x],NOW)
        self.assertEqual(d['verified_locked_over'],1)
        self.assertEqual(d['excluded']['missing_or_duplicate_identity'],1)

    def test_riskli_not_counted(self):
        d=audit_archive([record(choice='RISKLI')],NOW)
        self.assertEqual(d['verified_locked_over'],0)

    def test_current_future_never_counted_as_result(self):
        x=record(start=NOW+timedelta(days=1))
        d=audit_archive([x],NOW)
        self.assertEqual(d['verified_locked_over'],0)
        self.assertEqual(d['future_records'],1)

if __name__ == '__main__':
    unittest.main()
