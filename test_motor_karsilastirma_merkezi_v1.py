import unittest
from copy import deepcopy

from motor_karsilastirma_merkezi_v1 import compare


def sample(model="V18", probability=60):

    return {
        "motor": model,
        "id": "test-1",
        "lig_kodu": "test.1",
        "durum": "DOGRULANDI",
        "tarih": "2026-11-27T18:00:00+00:00",
        "hesaplama_zamani_utc":
            "2026-11-27T06:00:00+00:00",
        "toplam_gol": 4,
        "olasiliklar": {
            "1.5_ust": 90,
            "2.5_ust": 80,
            "3.5_ust": probability,
            "4.5_ust": 30,
            "5.5_ust": 15,
            "6.5_ust": 5
        }
    }


class TestMotorKarsilastirma(unittest.TestCase):

    def test_ortak_mac(self):

        r = compare([
            sample("V18"),
            sample("V19")
        ])

        self.assertEqual(r["toplam_mac"], 1)

        self.assertEqual(
            len(r["karsilastirmalar"]), 12
        )

    def test_brier(self):

        r = compare([
            sample("V18", 60),
            sample("V19", 70)
        ])

        row = next(
            x for x in r["karsilastirmalar"]
            if x["lig"] == "ALL"
            and x["cizgi"] == 3.5
        )

        self.assertAlmostEqual(row["brier_a"], 0.16)
        self.assertAlmostEqual(row["brier_b"], 0.09)

    def test_gec_tahmin(self):

        m = sample()

        m["hesaplama_zamani_utc"] = (
            "2026-11-27T19:00:00+00:00"
        )

        self.assertEqual(
            compare([m])["atlanan"], 1
        )

    def test_farkli_zaman(self):

        a = sample("V18")
        b = sample("V19")

        b["hesaplama_zamani_utc"] = (
            "2026-11-27T07:00:00+00:00"
        )

        self.assertEqual(
            compare([a, b])["karsilastirmalar"],
            []
        )

    def test_celiskili_skor(self):

        a = sample("V18")
        b = sample("V19")

        b["toplam_gol"] = 7

        r = compare([a, b])

        self.assertEqual(r["celiskili_mac"], 1)
        self.assertEqual(r["karsilastirmalar"], [])

    def test_tekrar_kayit(self):

        a = sample()

        r = compare([a, a])

        self.assertEqual(r["toplam_mac"], 1)

    def test_hatali_olasilik(self):

        m = sample()
        m["olasiliklar"]["6.5_ust"] = 110

        self.assertEqual(
            compare([m])["atlanan"], 1
        )

    def test_kaynak_koruma(self):

        data = [
            sample("V18"),
            sample("V19")
        ]

        original = deepcopy(data)

        compare(data)

        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
