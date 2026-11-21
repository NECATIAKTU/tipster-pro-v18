import unittest
from lig_akisi_teshis import calculate

class FlowTest(unittest.TestCase):
    def test_all_stages(self):
        r={'eng.1':'Premier','tur.2':'Birinci Lig','ned.2':'Eerste'}
        s,rows=calculate(r,{'maclar':[{'lig_kodu':'eng.1'},{'lig_kodu':'tur.2'}]},
            {'tahminler':[{'lig_kodu':'eng.1'}],'lig_denetimi':{'tur.2':{'durum':'YETERSIZ_VERI'}}},
            [{'mac':{'lig_kodu':'eng.1'}}],{'tahminler':[{'lig_kodu':'eng.1'}]})
        self.assertEqual(s['toplam_model'],1)
        self.assertEqual(rows[0]['teshis'],'PANELDE_TAHMIN_VAR')
        self.assertEqual(rows[1]['teshis'],'YETERSIZ_VERI')
        self.assertEqual(rows[2]['teshis'],'FIKSTURDE_MAC_YOK_VEYA_KAYNAK_SORUNU')
    def test_missing_files_not_reported_as_failure(self):
        s,rows=calculate({'eng.1':'PL'},None,None,None,None)
        self.assertEqual(rows[0]['teshis'],'FIKSTUR_DOSYASI_YOK')
if __name__=='__main__':unittest.main()
