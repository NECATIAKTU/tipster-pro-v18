import unittest
import json

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from kalici_veri_bankasi_v2 import (
    guncelle,
    kaydet
)

from test_gol_analiz_merkezi import sample


class TestKaliciVeriBankasiV2(unittest.TestCase):

    def test_yeni_kayit(self):

        r = guncelle([sample()], [])

        self.assertEqual(r["toplam_mac"], 1)
        self.assertEqual(r["yeni_mac"], 1)

    def test_tekrar_kayit(self):

        first = guncelle([sample()], [])

        r = guncelle(
            [sample()], first["maclar"]
        )

        self.assertEqual(r["toplam_mac"], 1)
        self.assertEqual(r["tekrar_mac"], 1)
        self.assertEqual(r["yeni_mac"], 0)

    def test_eski_kayit_koruma(self):

        first = guncelle([sample()], [])

        r = guncelle([], first["maclar"])

        self.assertEqual(
            r["maclar"], first["maclar"]
        )

    def test_yeni_mac_ekleme(self):

        first = guncelle([sample()], [])

        m = sample()
        m["kimlik"] = "test-2"

        r = guncelle(
            [m], first["maclar"]
        )

        self.assertEqual(r["toplam_mac"], 2)
        self.assertEqual(r["yeni_mac"], 1)

    def test_celiskili_skor(self):

        first = guncelle([sample()], [])

        m = sample()
        m["sonuc"]["ev_gol"] = 5
        m["sonuc"]["toplam_gol"] = 7

        r = guncelle(
            [m], first["maclar"]
        )

        self.assertEqual(r["celiskili_mac"], 1)

        self.assertEqual(
            r["maclar"][0]["toplam_gol"], 6
        )

    def test_bekleyen_mac(self):

        m = sample()
        m["durum"] = "BEKLIYOR"

        r = guncelle([m], [])

        self.assertEqual(r["toplam_mac"], 0)

    def test_kaynak_koruma(self):

        data = [sample()]
        original = deepcopy(data)

        guncelle(data, [])

        self.assertEqual(data, original)

    def test_kalici_json(self):

        with TemporaryDirectory() as folder:

            target = Path(folder) / "banka.json"

            r = guncelle([sample()], [])

            kaydet(target, r)

            loaded = json.loads(
                target.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(loaded, r)

    def test_gecersiz_veri(self):

        with self.assertRaises(ValueError):

            guncelle({}, [])

    def test_tekrar_banka_kaydi(self):

        first = guncelle([sample()], [])

        with self.assertRaises(ValueError):

            guncelle([], first["maclar"] * 2)

    def test_hatali_yazma_koruma(self):

        with TemporaryDirectory() as folder:

            target = Path(folder) / "banka.json"

            original = guncelle([sample()], [])

            kaydet(target, original)

            with self.assertRaises(ValueError):

                kaydet(target, {"hata": float("nan")})

            loaded = json.loads(
                target.read_text(encoding="utf-8")
            )

            self.assertEqual(loaded, original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
