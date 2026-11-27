import unittest

from dunya_ligleri_merkezi_v2 import (
    analiz, kimlik, indeks, tarih
)


def mac(ev="Takim A", dep="Takim B",
        lig="eng.1",
        zaman="2026-11-28T15:00:00Z"):

    return {
        "lig_kodu": lig,
        "ev_sahibi": ev,
        "deplasman": dep,
        "tarih": zaman
    }


class TestDunyaLigleriV2(unittest.TestCase):

    def setUp(self):

        self.registry = {
            "eng.1": "Premier League",
            "tur.1": "Super Lig"
        }

        self.a = mac()

        self.b = mac(
            ev="Takim C",
            dep="Takim D"
        )

        self.fikstur = {
            "maclar": [self.a, self.b],
            "lig_sayilari": {"eng.1": 2},
            "hatalar": []
        }

        self.model = {
            "olusturulma_utc":
                "2026-11-27T06:00:00Z",
            "tahminler": [self.a],
            "lig_denetimi": {}
        }

        self.panel = {
            "olusturulma_utc":
                "2026-11-27T06:10:00Z",
            "tahminler": [self.a]
        }

    def rapor(self):

        return analiz(
            self.registry,
            self.fikstur,
            self.model,
            self.panel
        )

    def test_toplam_mac(self):

        r = self.rapor()

        self.assertEqual(r["fikstur_mac"], 2)
        self.assertEqual(r["model_mac"], 1)
        self.assertEqual(r["panel_mac"], 1)

    def test_kapsama(self):

        self.assertEqual(
            self.rapor()["panel_kapsama_yuzdesi"],
            50.0
        )

    def test_eksik_mac(self):

        r = self.rapor()

        self.assertEqual(
            r["panelde_eksik_gelecek_mac"], 1
        )

    def test_model_panel_kaybi(self):

        self.model["tahminler"].append(self.b)

        r = self.rapor()

        self.assertEqual(
            r["durum_sayilari"][
                "MODELDE_VAR_PANELDE_YOK"
            ], 1
        )

    def test_gecmis_veri_yetersiz(self):

        self.model["lig_denetimi"] = {
            "eng.1": {
                "durum": "YETERSIZ_VERI"
            }
        }

        r = self.rapor()

        self.assertEqual(
            r["durum_sayilari"][
                "GECMIS_VERI_YETERSIZ"
            ], 1
        )

    def test_tekrar_mac(self):

        self.fikstur["maclar"].append(self.a)

        r = self.rapor()

        self.assertEqual(r["tekrar_fikstur"], 1)
        self.assertEqual(r["fikstur_mac"], 2)

    def test_gecersiz_kimlik(self):

        with self.assertRaises(ValueError):
            kimlik({})

    def test_gecersiz_tarih(self):

        self.assertIsNone(tarih("hatali"))

    def test_zaman_esitligi(self):

        a = mac(
            zaman="2026-11-28T15:00:00Z"
        )

        b = mac(
            zaman="2026-11-28T18:00:00+03:00"
        )

        self.assertEqual(kimlik(a), kimlik(b))

    def test_bos_fikstur(self):

        self.fikstur["maclar"] = []

        self.assertIsNone(
            self.rapor()["panel_kapsama_yuzdesi"]
        )

    def test_kaynak_hatasi(self):

        self.fikstur["hatalar"] = [
            {"lig": "eng.1"}
        ]

        r = self.rapor()

        lig = next(
            x for x in r["ligler"]
            if x["lig_kodu"] == "eng.1"
        )

        self.assertEqual(
            lig["kaynak_durumu"],
            "KAYNAK_HATASI_VAR"
        )

    def test_baslamis_mac(self):

        self.fikstur["maclar"].append(
            mac(zaman="2026-11-27T05:00:00Z")
        )

        self.assertEqual(
            self.rapor()["durum_sayilari"][
                "MODEL_ONCESI_BASLAMIS"
            ], 1
        )

    def test_motor_koruma(self):

        self.assertFalse(
            self.rapor()["ana_motor_degisti"]
        )


if __name__ == "__main__":
    unittest.main()
