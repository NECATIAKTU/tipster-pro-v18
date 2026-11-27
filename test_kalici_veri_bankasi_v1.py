import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy

from kalici_veri_bankasi_v1 import (
    veri_kaydet,
    lig_istatistikleri
)

from test_gol_analiz_merkezi import sample


class TestKaliciVeriBankasi(unittest.TestCase):

    def setUp(self):

        self.temp = TemporaryDirectory()

        self.db = (
            Path(self.temp.name) / "test.sqlite3"
        )

    def tearDown(self):

        self.temp.cleanup()

    def test_yeni_kayit(self):

        r = veri_kaydet([sample()], self.db)

        self.assertEqual(r["yeni_mac"], 1)
        self.assertEqual(r["toplam_mac"], 1)

    def test_tekrar_kayit(self):

        veri_kaydet([sample()], self.db)

        r = veri_kaydet([sample()], self.db)

        self.assertEqual(r["tekrar_mac"], 1)
        self.assertEqual(r["toplam_mac"], 1)

    def test_celiskili_skor(self):

        m = sample()

        veri_kaydet([m], self.db)

        m["sonuc"]["ev_gol"] = 5
        m["sonuc"]["toplam_gol"] = 7

        r = veri_kaydet([m], self.db)

        self.assertEqual(r["celiskili_mac"], 1)
        self.assertEqual(r["toplam_mac"], 1)

        ligler = lig_istatistikleri(self.db)

        self.assertEqual(
            ligler[0]["gol_ortalamasi"], 6
        )

    def test_lig_istatistikleri(self):

        veri_kaydet([sample()], self.db)

        r = lig_istatistikleri(self.db)

        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["mac_sayisi"], 1)

        self.assertEqual(
            r[0]["gol_oranlari"]["5.5_ust"],
            100
        )

        self.assertEqual(
            r[0]["gol_oranlari"]["6.5_ust"],
            0
        )

    def test_kaynak_koruma(self):

        m = sample()
        original = deepcopy(m)

        veri_kaydet([m], self.db)

        self.assertEqual(m, original)

    def test_gecersiz_kayit(self):

        m = sample()
        m["durum"] = "BEKLIYOR"

        r = veri_kaydet([m], self.db)

        self.assertEqual(r["toplam_mac"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
