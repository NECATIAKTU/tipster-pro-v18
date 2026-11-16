"""AFC 47 federasyon üst lig kataloğu için güvenli okuma katmanı.
Canlı veri veya tahmin ürettiği iddia edilmez. Aktif tarama varsayılan olarak kapalıdır.
"""
from pathlib import Path
import json

CATALOG_PATH = Path(__file__).with_name('asya_ust_ligler.json')

def ligleri_al():
    with CATALOG_PATH.open(encoding='utf-8') as f:
        return json.load(f)['ligler']

def aktif_ligleri_al():
    return [lig for lig in ligleri_al() if lig.get('aktif_tarama') and lig.get('fikstur_bagli') and lig.get('gecmis_mac_verisi_bagli') and lig.get('tahmin_motoruna_bagli')]

def kapsama_ozeti():
    ligler=ligleri_al()
    return {'katalog':len(ligler),'aktif':len(aktif_ligleri_al()),'fikstur_bagli':sum(bool(l.get('fikstur_bagli')) for l in ligler),'motor_bagli':sum(bool(l.get('tahmin_motoruna_bagli')) for l in ligler)}

if __name__ == '__main__':
    print(json.dumps(kapsama_ozeti(),ensure_ascii=False,indent=2))
