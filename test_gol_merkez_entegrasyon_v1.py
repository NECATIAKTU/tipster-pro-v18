import unittest
from copy import deepcopy
from unittest.mock import patch

from gol_merkez_entegrasyon_v1 import run
from test_gol_analiz_merkezi import sample


class TestGolMerkezEntegrasyon(unittest.TestCase):

    def setUp(self):

        self.archive = [sample()]

        self.registry = {
            "test.1": "Test Ligi"
        }

    def test_merkezi_rapor(self):

        r = run(
            self.archive,
            self.registry
        )

        self.assertEqual(
            r["durum"], "RAPOR_HAZIR"
        )

        self.assertEqual(r["hatalar"], {})

    def test_modul_baglantilari(self):

        r = run(
            self.archive,
            self.registry
        )

        for name in (
            "gol_analizi",
            "yuksek_gol_radari",
            "veri_bankasi",
            "dunya_ligleri",
            "motor_karsilastirma"
        ):

            self.assertIn(
                name, r["raporlar"]
            )

    def test_arsiv_koruma(self):

        original = deepcopy(self.archive)

        run(
            self.archive,
            self.registry
        )

        self.assertEqual(
            self.archive, original
        )

    def test_ana_motor_koruma(self):

        r = run(
            self.archive,
            self.registry
        )

        self.assertFalse(
            r["ana_motor_degisti"]
        )

    def test_gecici_veri_bankasi(self):

        r = run(
            self.archive,
            self.registry
        )

        db = r["raporlar"]["veri_bankasi"]

        self.assertEqual(
            db["depolama"], "GECICI_TEST"
        )

        self.assertEqual(
            db["toplam_mac"], 1
        )

    def test_modul_hata_izolasyonu(self):

        with patch(
            "gol_merkez_entegrasyon_v1.radar",
            side_effect=ValueError("Test hatasi")
        ):

            r = run(
                self.archive,
                self.registry
            )

        self.assertEqual(
            r["durum"], "HATA_VAR"
        )

        self.assertIn(
            "yuksek_gol_radari",
            r["hatalar"]
        )

        self.assertIn(
            "gol_analizi",
            r["raporlar"]
        )

        self.assertIn(
            "veri_bankasi",
            r["raporlar"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
