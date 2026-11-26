import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from gelistirme_veri_v1 import historical_stats

from gelistirme_istatistik_v1 import (
    takim_denetle,
    takim_profili,
    lig_profili,
)

from gelistirme_model_v1 import (
    model_analizi,
    olasilik_denetimi,
    GOL_CIZGILERI,
)


NOW = datetime(
    2026, 1, 20, 12, 0,
    tzinfo=timezone.utc
)


def ornek_mac(i):

    ev, dep = (
        ("Takim A", "Takim B")
        if i % 2 == 0
        else ("Takim B", "Takim A")
    )

    return {
        "id": str(i),
        "date": (
            NOW - timedelta(days=i)
        ).isoformat(),

        "status": {
            "type": {
                "completed": True,
                "name": "STATUS_FINAL",
            }
        },

        "competitions": [{
            "competitors": [
                {
                    "homeAway": "home",
                    "team": {"displayName": ev},
                    "score": "2",
                },
                {
                    "homeAway": "away",
                    "team": {"displayName": dep},
                    "score": "1",
                },
            ]
        }],
    }


def ornek_kaynak(lig, tarih):

    maclar = [
        ornek_mac(i)
        for i in range(1, 11)
        if (NOW - timedelta(days=i)).date()
        == tarih
    ]

    return {"events": maclar}


class GelistirmeTestV1(unittest.TestCase):

    def setUp(self):

        self.takimlar, self.rapor = historical_stats(
            "test.lig",
            NOW,
            10,
            ornek_kaynak,
        )

    def test_01_mac_sayisi(self):

        self.assertEqual(
            self.rapor["tamamlanmis_mac"], 10
        )

    def test_02_takim_sayisi(self):

        self.assertEqual(len(self.takimlar), 2)

    def test_03_takim_tutarliligi(self):

        for veri in self.takimlar.values():
            self.assertTrue(takim_denetle(veri))

    def test_04_saha_istatistikleri(self):

        a = self.takimlar["Takim A"]

        self.assertEqual(a["ev_mac"], 5)
        self.assertEqual(a["dep_mac"], 5)
        self.assertEqual(a["attigi"], 15)
        self.assertEqual(a["yedigi"], 15)

    def test_05_form_istatistikleri(self):

        a = takim_profili(
            "Takim A",
            self.takimlar["Takim A"],
        )

        self.assertEqual(a["form_mac"], 5)
        self.assertTrue(a["yeterli_veri"])

        self.assertAlmostEqual(
            a["form_atak"], 21 / 15
        )

    def test_06_lig_ortalama(self):

        lig = lig_profili(self.takimlar)

        self.assertTrue(
            lig["lig_verisi_tutarli"]
        )

        self.assertEqual(
            lig["lig_toplam_gol_ortalamasi"],
            3.0,
        )

    def test_07_model_entegrasyon(self):

        analiz = model_analizi(
            "Takim A",
            "Takim B",
            self.takimlar,
        )

        self.assertTrue(
            analiz["veri_denetimi"]
        )

        for alan in GOL_CIZGILERI:
            self.assertIn(
                alan, analiz["sonuc"]
            )

    def test_08_olasilik_sirasi(self):

        analiz = model_analizi(
            "Takim A",
            "Takim B",
            self.takimlar,
        )

        self.assertTrue(
            olasilik_denetimi(
                analiz["sonuc"]
            )
        )

    def test_09_bozuk_istatistik(self):

        veri = deepcopy(
            self.takimlar["Takim A"]
        )

        veri["attigi"] += 10

        self.assertFalse(
            takim_denetle(veri)
        )

    def test_10_eksik_takim(self):

        with self.assertRaises(ValueError):

            model_analizi(
                "Olmayan Takim",
                "Takim B",
                self.takimlar,
            )

    def test_11_tekrar_mac(self):

        def kaynak(lig, tarih):

            veri = ornek_kaynak(lig, tarih)

            veri["events"] *= 2

            return veri

        _, rapor = historical_stats(
            "test.lig", NOW, 10, kaynak
        )

        self.assertEqual(
            rapor["tamamlanmis_mac"], 10
        )

    def test_12_kaynak_hatasi(self):

        def kaynak(lig, tarih):
            raise OSError("Baglanti hatasi")

        takimlar, rapor = historical_stats(
            "test.lig", NOW, 10, kaynak
        )

        self.assertEqual(
            rapor["hata_gunu"], 10
        )

        self.assertEqual(takimlar, {})

    def test_13_celiskili_skor(self):

        def kaynak(lig, tarih):

            veri = ornek_kaynak(lig, tarih)

            if veri["events"]:

                kopya = deepcopy(
                    veri["events"][0]
                )

                kopya["competitions"][0][
                    "competitors"
                ][0]["score"] = "9"

                veri["events"].append(kopya)

            return veri

        _, rapor = historical_stats(
            "test.lig", NOW, 10, kaynak
        )

        self.assertEqual(
            rapor["celiskili_mac"], 10
        )

        self.assertEqual(
            rapor["tamamlanmis_mac"], 0
        )

    def test_14_gecersiz_olasilik(self):

        sonuc = {
            alan: 50
            for alan in GOL_CIZGILERI
        }

        sonuc["6.5_ust"] = 90

        self.assertFalse(
            olasilik_denetimi(sonuc)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
