import copy
import unittest

from aslan_modu_v1 import build, inspect


class TestAslanModu(unittest.TestCase):

    def test_yuksek_gol_kesfi(self):
        mac = {
            "tahmin": {
                "1.5_ust": 90,
                "2.5_ust": 80,
                "3.5_ust": 70,
                "4.5_ust": 55,
                "5.5_ust": 30,
                "6.5_ust": 10,
            }
        }
        sonuc = inspect(mac)
        self.assertEqual(sonuc["durum"], "KESIF_ADAYI")
        self.assertEqual(
            sonuc["en_yuksek_uygun_cizgi"]["cizgi"],
            "4.5 UST"
        )

    def test_esik_alti_analiz_durmaz(self):
        mac = {"tahmin": {
            "1.5_ust": 49,
            "2.5_ust": 35
        }}
        sonuc = inspect(mac)
        self.assertEqual(sonuc["durum"], "INCELEME")
        self.assertEqual(
            sonuc["en_yuksek_uygun_cizgi"]["cizgi"],
            "1.5 UST"
        )

    def test_eksik_veri(self):
        sonuc = inspect({"tahmin": {}})
        self.assertEqual(sonuc["durum"], "VERI_YOK")

    def test_v18_verisi_korunur(self):
        veri = {
            "model": "TIPSTER PRO V18",
            "tahminler": [{
                "id": "123",
                "ev_sahibi": "A",
                "deplasman": "B",
                "tahmin": {"2.5_ust": 75}
            }]
        }
        orijinal = copy.deepcopy(veri)
        rapor = build(veri)
        self.assertEqual(veri, orijinal)
        self.assertEqual(rapor["mac_sayisi"], 1)


if __name__ == "__main__":
    unittest.main()
