import copy
import json
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path
from v18_panel_aktar import convert

class PanelArchiveTest(unittest.TestCase):
    def setUp(self):
        self.archive = json.loads(Path('v18_tahmin_arsivi.json').read_text(encoding='utf-8'))
        # Relative fixture time: just after the latest archived lock, not wall clock.
        self.now = max(datetime.fromisoformat(r['kilit_zamani_utc']) for r in self.archive)

    def test_archive_projection(self):
        original = copy.deepcopy(self.archive)
        output = convert(self.archive, self.now)['tahminler']
        eligible = {r['kimlik']: r for r in self.archive if r.get('kilitli_secim') and r['durum'] == 'BEKLIYOR' and datetime.fromisoformat(r['mac']['tarih']) > self.now}
        self.assertEqual(set(eligible), {m['id'] for m in output})
        self.assertEqual(len(eligible), len(output))
        for m in output:
            r = eligible[m['id']]
            self.assertEqual(m['olasiliklar'], r['olasiliklar'])
            self.assertEqual(m['kilitli_secim'], r['kilitli_secim'])
            self.assertEqual(m['kilit_zamani_utc'], r['kilit_zamani_utc'])
        self.assertEqual(original, self.archive)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            convert(self.archive + [self.archive[0]], self.now)

    def test_invalid_lock_rejected(self):
        r = copy.deepcopy(self.archive[-1])
        r['kilit_zamani_utc'] = r['mac']['tarih']
        r['durum'] = 'BEKLIYOR'
        r['kilitli_secim'] = '1.5 UST'
        now = datetime.fromisoformat(r['mac']['hesaplama_zamani_utc'])
        with self.assertRaises(ValueError):
            convert([r], now)

    def test_missing_choice_excluded(self):
        r = copy.deepcopy(self.archive[-1])
        r.pop('kilitli_secim', None)
        self.assertEqual(convert([r], self.now)['tahminler'], [])
    def test_guncel_mac_saati(self):
        from datetime import timedelta
        r = copy.deepcopy(self.archive[-1])
        r['durum'] = 'BEKLIYOR'
        original = copy.deepcopy(r)
        now = datetime.fromisoformat(r['kilit_zamani_utc'])
        mac = copy.deepcopy(r['mac'])
        yeni = datetime.fromisoformat(mac['tarih']) + timedelta(hours=2)
        mac['tarih'] = yeni.isoformat()
        output = convert([r], now, {'maclar': [mac]})['tahminler']
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['tarih'], yeni.isoformat())
        self.assertEqual(output[0]['olasiliklar'], r['olasiliklar'])
        self.assertEqual(r, original)
if __name__ == '__main__': unittest.main()
