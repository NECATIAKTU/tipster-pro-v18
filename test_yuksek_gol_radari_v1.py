import unittest
from copy import deepcopy
from datetime import datetime, timezone

from yuksek_gol_radari_v1 import radar, gol_dagilimi


NOW = datetime(
    2026, 11, 27, 8, 0,
    tzinfo=timezone.utc
)


def sample():
    return {
        "id": "test-1",
        "lig_kodu": "test.1",
        "lig": "Test Ligi",
        "ev_sahibi": "Takim A",
        "deplasman": "Takim B",
        "tarih": "2026-11-27T18:00:00+00:00",
        "hesaplama_zamani_utc":
            "2026-11-27T06:00:00+00:00",
        "tahmin": {
            "1.5_ust": 90,
            "2.5_ust": 80,
            "3.5_ust": 70,
            "4.5_ust": 50,
            "5.5_ust": 30,
            "6.5_ust": 15
        }
    }


class TestYuksekGolRadari(unittest.TestCase):

    def test_dort_radar(self):
        r = radar([sample()], NOW)

        self.assertEqual(r["taranan_mac"], 1)

        for goals in range(4, 8):
            self.assertEqual(
                len(r["radarlar"][f"{goals}_PLUS"]),
                1
            )

    def test_baslamis_mac(self):
        m = sample()
        m["tarih"] = "2026-11-27T07:00:00+00:00"

        self.assertEqual(
            radar([m], NOW)["taranan_mac"], 0
        )

    def test_tekrar_mac(self):
        r = radar([sample(), sample()], NOW)
        self.assertEqual(r["taranan_mac"], 1)

    def test_hatali_yuzde(self):
        m = sample()
        m["tahmin"]["6.5_ust"] = 110

        self.assertEqual(
            radar([m], NOW)["taranan_mac"], 0
        )

    def test_olasilik_sirasi(self):
        m = sample()
        m["tahmin"]["6.5_ust"] = 95

        self.assertEqual(
            radar([m], NOW)["taranan_mac"], 0
        )

    def test_kaynak_koruma(self):
        m = sample()
        original = deepcopy(m)

        radar([m], NOW)

        self.assertEqual(m, original)

    def test_radar_siralama(self):
        a = sample()
        b = deepcopy(a)

        b["id"] = "test-2"
        b["tahmin"]["3.5_ust"] = 75

        r = radar([a, b], NOW)

        self.assertEqual(
            r["radarlar"]["4_PLUS"][0]["id"],
            "test-2"
        )

    def test_gol_dagilimi(self):
        gecmis = {
            "ev": [(3, 2)] * 5,
            "dep": [(2, 2)] * 5
        }
        r = gol_dagilimi(gecmis)
        self.assertEqual(r["ev"]["gol_ortalamasi"], 5.0)
        self.assertEqual(r["ev"]["gol_frekanslari"]["4.5_ust"], 100)
        self.assertEqual(r["dep"]["gol_frekanslari"]["4.5_ust"], 0)

    def test_eksik_gol_gecmisi(self):
        self.assertIsNone(gol_dagilimi({}))
if __name__ == "__main__":
    unittest.main(verbosity=2)
