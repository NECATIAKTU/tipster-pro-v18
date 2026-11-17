#!/usr/bin/env python3
"""Existing V18 prediction output -> static panel JSON; never modifies engine or source."""
import argparse, json, pathlib
from datetime import datetime, timezone, timedelta

def utc(v):
    if not isinstance(v,str): return None
    try:
        dt=datetime.fromisoformat(v.replace('Z','+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError: return None

def convert(src, now):
    if not isinstance(src,dict) or src.get('model') != 'TIPSTER PRO V18' or not isinstance(src.get('tahminler'),list):
        raise ValueError('V18 model formatı değil')
    created=utc(src.get('olusturulma_utc'))
    if created is None or created>now+timedelta(minutes=5) or now-created>timedelta(hours=24):
        raise ValueError('Eski veya tarihsiz V18 çıktısı: panelde güncel olarak yayınlanamaz')
    clean=[]
    for item in src['tahminler']:
        if not isinstance(item,dict): continue
        start=utc(item.get('tarih')); made=utc(item.get('hesaplama_zamani_utc'))
        if start is None or made is None or not (made < start and now < start): continue
        if not item.get('ev_sahibi') or not item.get('deplasman'): continue
        if not isinstance(item.get('tahmin'),dict): continue
        clean.append(item)
    return {'model':src['model'],'olusturulma_utc':src['olusturulma_utc'],
            'not':'V18 model olasılıkları; doğrulanmış başarı yüzdesi değildir.',
            'tahminler':clean,'durum_sayilari':src.get('durum_sayilari',{}),
            'lig_denetimi':src.get('lig_denetimi',{})}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('kaynak',help='gercek_tahmin_v18.py çıktısı: v18_yeni_tahminler.json')
    p.add_argument('--cikti',default='panel_tahminler.json')
    a=p.parse_args()
    source=json.loads(pathlib.Path(a.kaynak).read_text(encoding='utf-8'))
    result=convert(source,datetime.now(timezone.utc))
    pathlib.Path(a.cikti).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Panel için maç öncesi gerçek V18 kayıtları:',len(result['tahminler']))
if __name__=='__main__': main()
