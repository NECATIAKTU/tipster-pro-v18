import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import tipster_yuzdelik_rapor as rapor
import tipster_v4_kilitle as kilit

class BoundaryTests(unittest.TestCase):
    def test_nonfinite_probability(self):
        for value in ('NaN', 'Infinity', '-Infinity', float('nan'), float('inf')):
            self.assertIsNone(rapor.yuzde(value))
    def test_percentage_bounds(self):
        self.assertIsNone(rapor.yuzde(-1))
        self.assertIsNone(rapor.yuzde(101))
        self.assertEqual(rapor.yuzde(75.125), 75.12)
    def test_naive_timestamp_is_not_verified(self):
        self.assertIsNone(kilit.parse_utc('2026-11-10T14:00:00'))
    def test_valid_utc_timestamp(self):
        self.assertIsNotNone(kilit.parse_utc('2026-11-10T14:00:00+00:00'))

if __name__ == '__main__':
    unittest.main()
