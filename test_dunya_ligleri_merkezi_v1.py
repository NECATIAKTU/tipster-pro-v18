import unittest
from copy import deepcopy

from dunya_ligleri_merkezi_v1 import (
    build,
    bolge_bul
)


class TestDunyaLigleri(unittest.TestCase):

    def setUp(self):

        self.registry = {
            "eng.1": "Premier League",
            "jpn.1": "Japonya J1",
            "uefa.champions": "Champions League"
        }

        self.archive = [{
            "kimlik": "eng.1|test",
            "durum": "DOGRULANDI",
            "mac": {
                "lig_kodu": "eng.1"
            }
        }]

    def test_bolgeler(self):

        self.assertEqual(
            bolge_bul("eng.1"), "AVRUPA"
        )

        self.assertEqual(
            bolge_bul("jpn.1"), "ASYA"
        )

        self.assertEqual(
            bolge_bul("bra.1"), "GUNEY_AMERIKA"
        )

    def test_mevcut_ligler(self):

        r = build(
            self.registry,
            self.archive
        )

        self.assertEqual(
            r["motor_tanimli"], 3
        )

    def test_tekrar_mac(self):

        r = build(
            self.registry,
            self.archive * 2
        )

        total = sum(
            x["arsiv_mac"]
            for x in r["bolgeler"]
        )

        self.assertEqual(total, 1)

    def test_tekrar_lig(self):

        r = build(
            self.registry,
            self.archive
        )

        codes = [
            lig["kod"]
            for region in r["bolgeler"]
            for lig in region["ligler"]
        ]

        self.assertEqual(
            len(codes), len(set(codes))
        )

    def test_uefa_pasif(self):

        r = build(
            self.registry,
            self.archive
        )

        for region in r["bolgeler"]:
            for lig in region["ligler"]:

                if lig["kod"] == "uefa.champions":

                    self.assertFalse(
                        lig["varsayilan_aktif"]
                    )

    def test_kaynak_koruma(self):

        original = deepcopy(self.archive)
        registry = deepcopy(self.registry)

        build(self.registry, self.archive)

        self.assertEqual(
            self.archive, original
        )

        self.assertEqual(
            self.registry, registry
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
