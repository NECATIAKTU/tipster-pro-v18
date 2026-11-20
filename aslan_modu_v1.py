"""ASLAN MODU V1 - V18'e dokunmadan bağımsız gol fırsatı raporu.
Kullanım: python aslan_modu_v1.py --girdi v18_canli_cikti.json --cikti aslan_modu_rapor.json
Sadece okur; V18 dosyalarını, arşivini, eşiklerini veya panelini değiştirmez.
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

LINES = ('6.5', '5.5', '4.5', '3.5', '2.5', '1.5')

def inspect(match):
    raw = match.get('tahmin') or {}
    probs = {}
    for line in LINES:
        value = raw.get(f'{line}_ust')
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 100:
            probs[line] = float(value)
    if not probs:
        return {'durum': 'VERI_YOK', 'gerekce': 'Gecerli gol olasiligi bulunamadi'}
    # Önce yüksek çizgileri inceler; hiçbir çizgiyi sessizce elemez.
    ranked = [{'cizgi': f'{line} UST', 'model_yuzdesi': probs[line]} for line in LINES if line in probs]
    # En yüksek çizgi için en az %50: keşif etiketi, bahis önerisi değil.
    discoveries = [r for r in ranked if r['model_yuzdesi'] >= 50]
    strongest = discoveries[0] if discoveries else ranked[-1]
    return {'durum': 'KESIF_ADAYI' if discoveries else 'INCELEME',
            'en_yuksek_uygun_cizgi': strongest,
            'tum_cizgiler': ranked,
            'not': 'Yuzdeler V18 model ciktisidir; dogrulanmis basari veya bahis tavsiyesi degildir.'}

def build(data):
    matches = data.get('tahminler')
    if not isinstance(matches, list):
        raise ValueError('V18 tahminler listesi bulunamadi')
    items = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        items.append({'id': m.get('id'), 'tarih': m.get('tarih'), 'lig': m.get('lig'),
                      'ev_sahibi': m.get('ev_sahibi'), 'deplasman': m.get('deplasman'),
                      'analiz': inspect(m)})
    return {'modul': 'ASLAN MODU V1 - BAGIMSIZ KESIF',
            'olusturulma_utc': datetime.now(timezone.utc).isoformat(),
            'kaynak_model': data.get('model'), 'mac_sayisi': len(items), 'maclar': items}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--girdi', required=True)
    p.add_argument('--cikti', default='aslan_modu_rapor.json')
    args = p.parse_args()
    source, target = Path(args.girdi), Path(args.cikti)
    if source.resolve() == target.resolve() or target.exists():
        raise ValueError('Kaynak dosya korunuyor; mevcut cikti ustune yazilmaz')
    report = build(json.loads(source.read_text(encoding='utf-8')))
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('ASLAN MODU:', report['mac_sayisi'], 'mac analiz edildi; V18 degistirilmedi')

if __name__ == '__main__':
    main()
