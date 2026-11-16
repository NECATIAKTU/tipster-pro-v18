"""Fikstur ligleri icin tek, denetlenebilir uyumluluk kaydi.

Kaynak baglantisi olmayan ligler asla otomatik olarak baska ligin
istatistikleriyle eslestirilmez.
"""
from fikstur_yeni import LIGLER as FIKSTUR_LIGLER
from coklu_lig_motoru import LIGLER as ISTATISTIK_LIGLER

# Bu eslestirmeler mevcut tahmin_motoru.py'deki dogrulanmis kod yollaridir.
# NOR/SWZ ozel modul kullanir; digerleri istatistik motorundan gelir.
ESLESTIRMELER = {
    'eng.1':'E0','eng.2':'E1','eng.3':'E2','eng.4':'E3','eng.5':'EC',
    'sco.1':'SC0','sco.2':'SC1','sco.3':'SC2',
    'ger.1':'D1','ger.2':'D2','esp.1':'SP1','esp.2':'SP2',
    'ita.1':'I1','ita.2':'I2','fra.1':'F1','fra.2':'F2',
    'ned.1':'N1','por.1':'P1','tur.1':'T1','bel.1':'B1',
    'gre.1':'G1','nor.1':'NOR','sui.1':'SWZ',
    'jpn.1':'J1',
}
OZEL = {'NOR','SWZ'}

def rapor():
    sonuc = []
    for kod, ad in sorted(FIKSTUR_LIGLER.items()):
        veri = ESLESTIRMELER.get(kod)
        bagli = bool(veri and (veri in ISTATISTIK_LIGLER or veri in OZEL))
        sonuc.append({'fikstur_kodu':kod,'lig':ad,'veri_kodu':veri,
                      'durum':'BAGLANTI_TANIMLI' if bagli else 'VERI_KAYNAGI_GEREKLI'})
    return sonuc

if __name__ == '__main__':
    import json
    from pathlib import Path
    Path('lig_uyumluluk_raporu.json').write_text(
        json.dumps(rapor(), ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    from collections import Counter
    print('Lig sayisi:',len(rapor()))
    print('Durum:',dict(Counter(x['durum'] for x in rapor())))
