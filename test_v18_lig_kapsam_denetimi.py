import json
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from v18_lig_kapsam_denetimi import read_league_registry, archived_codes, probe_espn, build_report, write_report

class DummyResponse:
    def __init__(self, payload): self.stream = BytesIO(json.dumps(payload).encode('utf-8'))
    def __enter__(self): return self.stream
    def __exit__(self, *args): self.stream.close()

class CoverageTests(unittest.TestCase):
    def test_extract_only_literal_without_executing_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, 'test.py')
            p.write_text("LIGLER={'eng.1':'Premier League'}\nraise RuntimeError('must not execute')\n")
            self.assertEqual(read_league_registry(p), {'eng.1': 'Premier League'})

    def test_nested_archive_and_missing_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, 'archive.json')
            p.write_text(json.dumps([{'mac': {'lig_kodu':'eng.1'}}, {'mac':{'lig_kodu':'eng.1'}}, {'other':1}]))
            counts, total = archived_codes(p)
            report = build_report({'eng.1':'Premier League','tur.2':'1. Lig'}, counts, total, today=date(2026,11,21))
            self.assertEqual((report['arsivde_kayitli_lig'],report['arsivde_kayitsiz_lig']), (1,['tur.2']))
            self.assertEqual(report['arsiv_toplam_kayit'], 3)
            self.assertGreater(report['aday_sayisi'], 0)

    def test_empty_scoreboard_is_not_confirmed_coverage(self):
        result = probe_espn('foo.1', [date(2026,11,21)], lambda *_args, **_kw: DummyResponse({'events':[]}))
        self.assertEqual(result['durum'], 'YANIT_VAR_MAC_KANITI_YOK')

    def test_scoreboard_with_event_is_evidence(self):
        result = probe_espn('eng.1', [date(2026,11,21)], lambda *_args, **_kw: DummyResponse({'events':[{'id':'11'}]}))
        self.assertEqual(result['durum'], 'MAC_KANITI_VAR')

    def test_never_mutates_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp,'source.py')
            a = Path(tmp,'archive.json')
            p.write_text("LIGLER={'eng.1':'Premier League'}\n")
            a.write_text('[{"mac":{"lig_kodu":"eng.1"}}]')
            before = (p.read_bytes(),a.read_bytes())
            counts,total = archived_codes(a)
            write_report(build_report(read_league_registry(p),counts,total),Path(tmp,'report'))
            self.assertEqual(before, (p.read_bytes(),a.read_bytes()))
            self.assertTrue(Path(tmp,'report','lig_kapsam_raporu.csv').exists())

if __name__=='__main__': unittest.main()
