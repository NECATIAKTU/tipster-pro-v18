import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from denetim import parse_espn, check_espn, check_csv, run

NOW = datetime(2026, 11, 23, 8, 0, tzinfo=timezone.utc)

def event(id, date, state='pre'):
    return {'id': id, 'date': date, 'status': {'type': {'state': state, 'completed': state == 'post'}},
            'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'displayName': 'Home'}},
                {'homeAway': 'away', 'team': {'displayName': 'Away'}}]}]}

class AuditTests(unittest.TestCase):
    def test_date_windows_and_dedup(self):
        e = event('a', '2026-11-24T08:00:00Z')
        x = parse_espn([e, e, event('b', '2026-12-03T08:00:00Z')], NOW)
        self.assertEqual(x, {'7': 1, '14': 2, '30': 2})
    def test_old_or_complete_excluded(self):
        x = parse_espn([event('a','2026-11-22T12:00:00Z'), event('b','2026-11-24T08:00:00Z','post')], NOW)
        self.assertEqual(x['30'], 0)
    def test_empty_is_not_invalid_code(self):
        def fetch(url): return b'{"events":[]}'
        r = check_espn('sco.2', NOW, 7, fetch)
        self.assertEqual(r['durum'], 'BOS_YANIT')
        self.assertEqual(r['fikstur']['7'], 0)
    def test_partial_error_preserved(self):
        def fetch(url):
            if '20261124' in url: raise OSError('down')
            return b'{"events":[]}'
        r = check_espn('sui.1', NOW, 7, fetch)
        self.assertEqual(r['hatali_gun'], 1)
        self.assertEqual(r['durum'], 'KISMI_HATA')
    def test_csv_results(self):
        def fetch(url): return b'Date,HomeTeam,AwayTeam,FTHG,FTAG\n23/11/26,A,B,2,1\n24/11/26,B,A,,\n'
        self.assertEqual(check_csv('SC1','2627',fetch)['skorlu_mac'], 1)
    def test_no_predictions_made(self):
        def fetch(url): return b'{"events":[]}' if 'espn.com' in url else b'Date,HomeTeam,AwayTeam,FTHG,FTAG\n'
        out = run(NOW, horizon=7, fetch=fetch, include_candidates=True)
        self.assertEqual(len(out['ligler']), 25)
        self.assertTrue(all(not x['tahmin_motoruna_bagli'] for x in out['ligler']))

if __name__ == '__main__': unittest.main()
