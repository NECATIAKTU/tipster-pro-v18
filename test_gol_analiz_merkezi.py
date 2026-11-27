import unittest
from gol_analiz_merkezi import audit


def sample():
    return {
        "kimlik": "test-1",
        "durum": "DOGRULANDI",
        "mac": {
            "tarih": "2026-11-20T15:00:00+00:00",
            "hesaplama_zamani_utc": "2026-11-20T08:00:00+00:00",
            "lig_kodu": "test.1",
            "ev_sahibi": "Takim A",
            "deplasman": "Takim B"
        },
        "kilit_zamani_utc": "2026-11-20T09:00:00+00:00",
        "sonuc": {
            "ev_gol": 4,
            "dep_gol": 2,
            "toplam_gol": 6
        },
        "kilitli_secim": "RISKLI",
        "olasiliklar": {
            "1.5_ust": 74,
            "2.5_ust": 52,
            "3.5_ust": 30,
            "4.5_ust": 15,
            "5.5_ust": 7,
            "6.5_ust": 3
        }
    }


class TestGolAnaliz(unittest.TestCase):

    def test_kacirilan_gol(self):
        r = audit([sample()])
        self.assertEqual(r["dogrulanan"], 1)
        self.assertEqual(
            len(r["kacirilan_goller"]), 1
        )
        self.assertEqual(
            r["kacirilan_goller"][0]["toplam_gol"], 6
        )

    def test_tekrar_kayit(self):
        r = audit([sample(), sample()])
        self.assertEqual(r["dogrulanan"], 1)

    def test_gec_tahmin(self):
        m = sample()
        m["kilit_zamani_utc"] = "2026-11-20T16:00:00+00:00"
        self.assertEqual(audit([m])["dogrulanan"], 0)

    def test_hatali_skor(self):
        m = sample()
        m["sonuc"]["toplam_gol"] = 9
        self.assertEqual(audit([m])["dogrulanan"], 0)

    def test_bekleyen_mac(self):
        m = sample()
        m["durum"] = "BEKLIYOR"
        self.assertEqual(audit([m])["dogrulanan"], 0)

    def test_hatali_olasilik(self):
        m = sample()
        m["olasiliklar"]["6.5_ust"] = 99
        self.assertEqual(audit([m])["dogrulanan"], 0)

    def test_dusuk_cizgide_kacirilan_gol(self):
        m = sample()
        m["kilitli_secim"] = "1.5 UST"
        r = audit([m])
        self.assertEqual(
            r["kacirilan_goller"][0]["kacirilan_cizgiler"],
            [3.5, 4.5, 5.5]
        )

    def test_yuksek_cizgi_dogru(self):
        m = sample()
        m["kilitli_secim"] = "5.5 UST"
        self.assertEqual(len(audit([m])["kacirilan_goller"]), 0)
if __name__ == "__main__":
    unittest.main()
