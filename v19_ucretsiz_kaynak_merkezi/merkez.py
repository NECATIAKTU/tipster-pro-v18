"""V19 read-only discovery of free football league sources.

Does not import or modify V18 or V19 prediction engines.  No predictions generated.
The Football Charts free tier is for personal research; DO NOT use this module
as a commercial/public-panel data feed without provider permission.
"""
import argparse
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = 'https://api.football-charts.com/api/v1'
CATALOG = Path(__file__).resolve().parents[1] / 'v19_ucretsiz_ligler' / 'ligler.json'
# Confirmed provider documentation examples, not assumptions of availability today.
KNOWN_CODES = {'de.3': 'germany3'}

def normalize(s):
    s = unicodedata.normalize('NFKD', str(s).casefold())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c))).strip()

def request_json(url, token=None, fetch=None):
    if fetch is not None:
        return fetch(url, token)
    headers = {'User-Agent': 'TIPSTER-V19-Research/1.0', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)

def catalog_leagues(payload):
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next((payload[k] for k in ('leagues','results','data') if isinstance(payload.get(k), list)), [])
    else:
        rows = []
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = next((row[k] for k in ('code','slug','id','league_code') if isinstance(row.get(k),str) and row[k]), None)
        title = next((row[k] for k in ('name','title','league','strLeague') if isinstance(row.get(k),str) and row[k]), None)
        if code and title:
            out[code] = title
    return out

def match_league(item, provider_codes):
    """Only an exact normalized name or documented known code may be selected."""
    explicit = KNOWN_CODES.get(item['kod'])
    if explicit in provider_codes:
        return {'kod': explicit, 'yontem': 'belgelenmis_kod'}
    name = normalize(item['ad'])
    candidates = [k for k,v in provider_codes.items() if normalize(v) == name]
    if len(candidates) == 1:
        return {'kod':candidates[0],'yontem':'tam_ad_eslesmesi'}
    return {'kod':None,'durum':'ESLESME_DOGRULANMADI'}

def check_payload(payload):
    if isinstance(payload,list):
        return {'kayit_sayisi':len(payload), 'sekil':'liste'}
    if isinstance(payload,dict):
        for field in ('results','fixtures','matches','data'):
            value = payload.get(field)
            if isinstance(value,list):
                return {'kayit_sayisi':len(value),'sekil':field}
        return {'kayit_sayisi':None,'sekil':'bilinmeyen_json'}
    return {'kayit_sayisi':None,'sekil':'beklenmeyen_json'}

def run(path=CATALOG, *, token=None, max_leagues=10, fetch=None):
    if max_leagues < 0 or (max_leagues > 12 and not token):
        raise ValueError('Anahtarsiz denetim en fazla 12 lig (25 istek/gun siniri)')
    catalog = json.loads(Path(path).read_text(encoding='utf-8'))
    wanted = catalog['sifir_fikstur'] + catalog['yeni_adaylar']
    output = {'olusturulma_utc':datetime.now(timezone.utc).isoformat(),
              'modul':'V19 Ucretsiz Kaynak Kesfi', 'salt_okunur':True,
              'not':'Lig bulunsa bile canli motora baglanmaz. Tam takim ve tarih denetimi gerekir.',
              'kaynak':'Football Charts - personal/research free tier',
              'ligler':[]}
    try:
        leagues = catalog_leagues(request_json(BASE + '/leagues/', token, fetch))
        output['kaynak_lig_sayisi'] = len(leagues)
        if not leagues:
            output['uyari'] = 'Katalog bicimi bilinmiyor veya bos: lig kodu icat edilmedi'
    except (OSError, ValueError, TypeError, KeyError) as e:
        output['kaynak_hatasi'] = type(e).__name__ + ': ' + str(e)[:160]
        leagues = {}
    selected = 0
    for entry in wanted:
        row = {'bizim_kod':entry['kod'],'lig':entry['ad'], 'durum':'ADAY'}
        mapping = match_league(entry, leagues)
        row['eslesme'] = mapping
        provider = mapping['kod']
        if provider and selected < max_leagues:
            selected += 1
            for kind in ('fixtures','results'):
                try:
                    payload = request_json(f'{BASE}/leagues/{provider}/{kind}/', token, fetch)
                    row[kind] = check_payload(payload)
                except (OSError, ValueError, TypeError, KeyError) as e:
                    row[kind] = {'hata':type(e).__name__ + ': ' + str(e)[:160]}
            row['durum'] = 'KAYNAK_DENETLENDI_TAHMIN_YOK'
        elif provider:
            row['durum'] = 'KOTA_NEDENIYLE_DENENMEDI'
        else:
            row['durum'] = 'KOD_DOGRULANMADI'
        output['ligler'].append(row)
    output['eslesen'] = sum(bool(r['eslesme']['kod']) for r in output['ligler'])
    output['denetlenen'] = selected
    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--katalog',default=str(CATALOG))
    parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--cikti', default='v19_kaynak_kesif_raporu.json')
    args=parser.parse_args()
    token=os.environ.get('FC_API_KEY')  # optional, never printed
    result=run(args.katalog,token=token,max_leagues=args.limit)
    Path(args.cikti).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('HEDEF:',len(result['ligler']),'ESLESEN:',result['eslesen'],'DENETLENEN:',result['denetlenen'])
    print('RAPOR:',args.cikti)
if __name__ == '__main__':
    main()
