#!/usr/bin/env python3
"""TIPSTER V18 - ligi fikstur -> model -> panel boyunca salt okunur denetle.
Kaynaktaki tahminleri, esikleri veya is akisini DEGISTIRMEZ.
"""
import argparse, ast, csv, json
from collections import Counter, defaultdict
from pathlib import Path


def read_json(path):
    p = Path(path)
    if not p.is_file(): return None
    return json.loads(p.read_text(encoding='utf-8-sig'))


def registry(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LIGLER' for t in n.targets):
            return ast.literal_eval(n.value)
    raise ValueError('LIGLER bulunamadi')


def records(payload, names):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        for name in names:
            if isinstance(payload.get(name), list): return payload[name]
    return []


def code(item):
    if not isinstance(item, dict): return None
    m = item.get('mac')
    if isinstance(m, dict) and m.get('lig_kodu'): return m['lig_kodu']
    return item.get('lig_kodu')


def calculate(reg, fixture, model, archive, panel):
    fs = Counter(code(x) for x in records(fixture, ('maclar', 'matches')) if code(x))
    ms = Counter(code(x) for x in records(model, ('tahminler', 'predictions')) if code(x))
    ars = Counter(code(x) for x in records(archive, ('kayitlar', 'records')) if code(x))
    ps = Counter(code(x) for x in records(panel, ('tahminler', 'predictions')) if code(x))
    audit = model.get('lig_denetimi', {}) if isinstance(model, dict) else {}
    info = {'tanımlı_lig':len(reg), 'fikstur_dosyasi_var':fixture is not None,
            'model_dosyasi_var':model is not None, 'arsiv_dosyasi_var':archive is not None,
            'panel_dosyasi_var':panel is not None}
    out = []
    for league, label in reg.items():
        a = audit.get(league,{}) if isinstance(audit,dict) else {}
        if not isinstance(a,dict): a={}
        if fixture is None: reason='FIKSTUR_DOSYASI_YOK'
        elif fs[league] == 0: reason='FIKSTURDE_MAC_YOK_VEYA_KAYNAK_SORUNU'
        elif model is None: reason='MODEL_DOSYASI_YOK'
        elif ms[league] == 0: reason=str(a.get('durum') or 'MODELE_GIRDI_AMA_TAHMIN_YOK')
        elif panel is None: reason='PANEL_DOSYASI_YOK'
        elif ps[league] == 0: reason='MODELDE_VAR_PANELDE_YOK'
        else: reason='PANELDE_TAHMIN_VAR'
        out.append({'lig_kodu':league,'lig':label,'fikstur_mac':fs[league],
                    'model_tahmin':ms[league], 'panel_tahmin':ps[league],
                    'arsiv_kayit':ars[league], 'gecmis_mac':a.get('tamamlanmis_mac',''),
                    'gecmis_hata_gunu':a.get('hata_gunu',''), 'teshis':reason})
    info['toplam_fikstur']=sum(fs.values()); info['toplam_model']=sum(ms.values())
    info['toplam_panel']=sum(ps.values())
    info['ekranda_gorunen_lig']=sum(r['panel_tahmin']>0 for r in out)
    return info,out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--klasor',default='.',help='Mevcut V18 repo kok klasoru')
    p.add_argument('--cikti',default='lig_teshis_ciktilari')
    args=p.parse_args()
    root=Path(args.klasor)
    r=registry(root/'fikstur_yeni.py')
    summary,rows=calculate(r,
        read_json(root/'gelecek_maclar.json'),read_json(root/'v18_canli_cikti.json'),
        read_json(root/'v18_tahmin_arsivi.json'),read_json(root/'panel_tahminler.json'))
    target=Path(args.cikti);target.mkdir(parents=True,exist_ok=True)
    (target/'ozet.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (target/'lig_bazli_teshis.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('LIG:',summary['tanımlı_lig'],'FIKSTUR:',summary['toplam_fikstur'],'MODEL:',summary['toplam_model'],
          'PANEL:',summary['toplam_panel'],'PANEL LIG:',summary['ekranda_gorunen_lig'])
    print('RAPOR:',target.resolve())
    print('UYARI: Bu denetim sadece mevcut dosya anlik goruntusudur. Canli API dogrulamasi degildir.')

if __name__=='__main__': main()
