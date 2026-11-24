"""TIPSTER PRO V19: read-only historical confidence audit; standard library only.

Not a betting recommendation. Does not alter prediction, archive, panel or settings.
All historical records must have been verified before the evaluated pick was made.
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

LINES = ('1.5', '2.5', '3.5', '4.5', '5.5', '6.5')


def utc(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None


def probability(rec, line):
    pool = rec.get('olasiliklar') or (rec.get('mac') or {}).get('tahmin') or {}
    if not isinstance(pool, dict):
        return None
    try:
        num = float(pool.get(line + '_ust'))
    except (TypeError, ValueError):
        return None
    return num / 100 if math.isfinite(num) and 0 <= num <= 100 else None


def valid_record(row):
    if not isinstance(row, dict) or not isinstance(row.get('mac'), dict):
        return None
    m = row['mac']
    start, made, locked = utc(m.get('tarih')), utc(m.get('hesaplama_zamani_utc')), utc(row.get('kilit_zamani_utc'))
    if not all((start, made, locked)) or not (made <= locked < start):
        return None
    league = m.get('lig_kodu')
    if not isinstance(league, str) or not league:
        return None
    return {'id': row.get('kimlik'), 'lig': league, 'lig_adi': m.get('lig') or league,
            'ev': m.get('ev_sahibi'), 'dep': m.get('deplasman'),
            'start': start, 'made': made, 'locked': locked, 'row': row}


def settled(row):
    rec = valid_record(row)
    if rec is None or row.get('durum') != 'DOGRULANDI':
        return None
    verified = utc(row.get('sonuc_dogrulama_zamani_utc'))
    result = row.get('sonuc')
    if verified is None or verified < rec['start'] or not isinstance(result, dict):
        return None
    home, away = result.get('ev_gol'), result.get('dep_gol')
    if (type(home) is not int or type(away) is not int or home < 0 or away < 0):
        return None
    rec['verified'] = verified
    rec['goals'] = home + away
    return rec


def wilson_lower(wins, n, z=1.96):
    if n == 0:
        return None
    p = wins / n
    den = 1 + z*z/n
    center = p + z*z/(2*n)
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return max(0., (center-margin)/den)


def metrics(events):
    n = len(events)
    if n == 0:
        return {'ornek': 0, 'isabet': None, 'wilson_alt_95': None,
                'brier': None, 'model_ortalama': None, 'kalibrasyon_farki': None}
    wins = sum(e['hit'] for e in events)
    actual = wins/n
    avg = sum(e['prob'] for e in events)/n
    return {'ornek': n, 'isabet': round(actual*100, 2),
            'wilson_alt_95': round(100*wilson_lower(wins, n), 2),
            'brier': round(sum((e['prob']-e['hit'])**2 for e in events)/n, 4),
            'model_ortalama': round(avg*100, 2),
            'kalibrasyon_farki': round((avg-actual)*100, 2)}


def audit(archive, now):
    if not isinstance(archive, list):
        raise ValueError('Arsiv liste olmali')
    settled_records = [r for row in archive if (r := settled(row))]
    # Only actual pre-match locked UST selections are audited as picks.
    outcomes = []
    for r in settled_records:
        choice = str(r['row'].get('kilitli_secim') or '').strip().upper().split()
        if len(choice) != 2 or choice[1] != 'UST' or choice[0] not in LINES:
            continue
        p = probability(r['row'], choice[0])
        if p is None:
            continue
        outcomes.append({'lig':r['lig'], 'line':choice[0], 'prob':p,
                         'hit':int(r['goals'] > float(choice[0])),
                         'verified':r['verified']})
    past = [e for e in outcomes if e['verified'] <= now]
    by_lig = defaultdict(list)
    by_market = defaultdict(list)
    for e in past:
        by_lig[(e['lig'],e['line'])].append(e)
        by_market[e['line']].append(e)
    candidates = []
    rejected = defaultdict(int)
    for row in archive:
        r = valid_record(row)
        if r is None:
            rejected['kilit_veya_tarih_gecersiz'] += 1
            continue
        if r['start'] <= now or row.get('durum') == 'DOGRULANDI':
            continue
        choice = str(row.get('kilitli_secim') or '').strip().upper().split()
        if len(choice)!=2 or choice[1]!='UST' or choice[0] not in LINES:
            rejected['riskli_veya_secimsiz'] += 1
            continue
        line = choice[0]
        p = probability(row, line)
        if p is None:
            rejected['model_yuzdesi_gecersiz'] += 1
            continue
        # No historical result verified after the candidate's own forecast time.
        local = [e for e in by_lig[(r['lig'],line)] if e['verified'] <= r['made']]
        broader = [e for e in by_market[line] if e['verified'] <= r['made']]
        lm, gm = metrics(local), metrics(broader)
        eligible = (p >= .75 and lm['ornek'] >= 30 and gm['ornek'] >= 100
                    and lm['wilson_alt_95'] >= 65
                    and abs(lm['kalibrasyon_farki']) <= 10)
        candidates.append({'lig':r['lig_adi'], 'mac': f"{r['ev']} - {r['dep']}",
                           'tarih':r['start'].isoformat(), 'secim':line+' UST',
                           'model_yuzdesi':round(p*100,2),
                           'lig_ve_cizgi':lm, 'genel_cizgi':gm,
                           'durum':'INCELEME_ADAYI' if eligible else 'YETERSIZ_KANIT',
                           'not':'Bu karar kar garantisi veya onaylanmis bahis tavsiyesi degildir.'})
    candidates.sort(key=lambda r:(r['durum']!='INCELEME_ADAYI',-r['model_yuzdesi'],r['tarih']))
    return {'olusturulma_utc':now.isoformat(), 'modul':'V19 BAGIMSIZ GUVEN DENETCISI',
            'canliya_yazildi':False, 'ucretli_kaynak':False,
            'gecmis_kilitli_ust_sayisi':len(past), 'toplam_aday':len(candidates),
            'inceleme_adayi':sum(x['durum']=='INCELEME_ADAYI' for x in candidates),
            'top20':candidates[:20], 'tum_adaylar':candidates,
            'reddedilenler':dict(rejected), 'uyari':'Kalibrasyon kontrolu gozlemseldir; ileri donem basarisi garanti degildir.'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--arsiv', required=True)
    p.add_argument('--cikti', default='v19_guven_raporu.json')
    a=p.parse_args()
    dest=Path(a.cikti)
    if dest.exists():
        raise SystemExit('Rapor zaten var; eski kaydi silmiyoruz.')
    source=json.loads(Path(a.arsiv).read_text(encoding='utf-8'))
    result=audit(source,datetime.now(timezone.utc))
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('KILITLI GECMIS:',result['gecmis_kilitli_ust_sayisi'],
          'ADAY:',result['toplam_aday'],'INCELEME:',result['inceleme_adayi'])

if __name__=='__main__':
    main()
