"""Offline regression tests; do not edit production archives."""
import importlib.util
import unittest
from datetime import timezone
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('birlesik', Path(__file__).resolve().with_name('tipster_birlesik_rapor.py'))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

class TestBirlesik(unittest.TestCase):
    def test_timezone_equivalence(self):
        a = {'tarih':'2026-11-13T19:30:00Z','espn_lig':'eng.1','ev':'Team A','dep':'Team B'}
        b = {**a,'tarih':'2026-11-13T20:30:00+01:00'}
        self.assertEqual(mod.imza(a), mod.imza(b))

    def test_missing_timezone_rejected(self):
        self.assertIsNone(mod.zaman({'tarih':'2026-11-13T19:30:00'}))

    def test_normalization(self):
        a={'tarih':'2026-11-13T19:30:00Z','espn_lig':'esp.2','ev':'Leganés','dep':'Burgos'}
        b={**a,'ev':'Leganes'}
        self.assertEqual(mod.imza(a),mod.imza(b))

    def test_invalid_percentage(self):
        self.assertEqual(mod.karar_ver({'analiz':{'3.5_ust':999}}),'RİSKLİ')

    def test_threshold(self):
        self.assertEqual(mod.karar_ver({'analiz':{'3.5_ust':65}}),'3.5 ÜST')

    def test_no_probabilities(self):
        self.assertEqual(mod.karar_ver({}),'RİSKLİ')

if __name__=='__main__': unittest.main()
