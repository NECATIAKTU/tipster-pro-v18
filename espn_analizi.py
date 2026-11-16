
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher

from coklu_lig_motoru import tum_ligleri_al, mac_analizi

LIG_ESLESTIRME = {
    'eng.1': 'E0', 'eng.2': 'E1', 'eng.3': 'E2', 'eng.4': 'E3',
    'esp.1': 'SP1', 'ger.1': 'D1', 'ita.1': 'I1', 'fra.1': 'F1',
    'ned.1': 'N1', 'por.1': 'P1', 'tur.1': 'T1', 'sco.1': 'SC0',
    'bel.1': 'B1',
}

KISALTMALAR = {
    'manchester united': 'man united',
    'manchester city': 'man city',
    'nottingham forest': 'nottm forest',
    'tottenham hotspur': 'tottenham',
    'newcastle united': 'newcastle',
    'west ham united': 'west ham',
    'brighton hove albion': 'brighton',
    'brighton and hove albion': 'brighton',
    'wolverhampton wanderers': 'wolves',
    'leicester city': 'leicester',
    'ipswich town': 'ipswich',
    'norwich city': 'norwich',
    'birmingham city': 'birmingham',
    'cardiff city': 'cardiff',
    'swansea city': 'swansea',
    'hull city': 'hull',
    'stoke city': 'stoke',
    'sheffield wednesday': 'sheffield weds',
    'queens park rangers': 'qpr',
    'west bromwich albion': 'west brom',
    'leeds united': 'leeds',
    'fortuna sittard': 'for sittard',
    'nec nijmegen': 'nijmegen',
    'fc groningen': 'groningen',
    'feyenoord rotterdam': 'feyenoord',
    'ajax amsterdam': 'ajax',
    'sc cambuur': 'cambuur',
    'pec zwolle': 'zwolle',
    'internazionale': 'inter',
    'ac milan': 'milan',
    'as roma': 'roma',
    'racing genk': 'genk',
    'standard liege': 'standard',
    'kaa gent': 'gent',
    'kv mechelen': 'mechelen',
    'sint truidense': 'st truiden',
    'union st gilloise': 'union saint gilloise',
    'union saint gilloise': 'union saint gilloise',
    'athletic club': 'ath bilbao',
    'celta vigo': 'celta',
    'real betis': 'betis',
    'real sociedad': 'sociedad',
    'atletico madrid': 'ath madrid',
    'heart of midlothian': 'hearts',
    'paris saint germain': 'paris sg',
    'as monaco': 'monaco',
    'stade rennais': 'rennes',
    'aj auxerre': 'auxerre',
    'le havre ac': 'le havre',
    'bayer leverkusen': 'leverkusen',
    'tsg hoffenheim': 'hoffenheim',
    'sc freiburg': 'freiburg',
    'vfb stuttgart': 'stuttgart',
    'borussia monchengladbach': 'm gladbach',
    'borussia dortmund': 'dortmund',
    'caykur rizespor': 'rizespor',
    'istanbul basaksehir': 'basaksehir',
    'sporting cp': 'sporting',
    'c d nacional': 'nacional',
    'sporting clube de portugal': 'sporting',
    'vitoria de guimaraes': 'guimaraes',
    'vitoria guimaraes': 'guimaraes',
    'eintracht frankfurt': 'ein frankfurt',
    'borussia m gladbach': 'm gladbach',
    'rayo vallecano': 'vallecano',
}


def temizle_taban(ad):
    ad = str(ad or '').casefold()
    ad = ad.replace('ı', 'i')
    ad = ad.replace('æ', 'ae').replace('œ', 'oe')
    ad = unicodedata.normalize('NFKD', ad)
    ad = ''.join(
        c for c in ad
        if not unicodedata.combining(c)
    )
    ad = ad.replace('&', ' and ')
    ad = re.sub(r'[^a-z0-9 ]', ' ', ad)
    return ' '.join(ad.split())


ALIASES = {
    temizle_taban(k): temizle_taban(v)
    for k, v in KISALTMALAR.items()
}


def temizle(ad):
    ad = temizle_taban(ad)
    ad = ALIASES.get(ad, ad)

    for ek in ('fc ', 'afc '):
        if ad.startswith(ek):
            ad = ad[len(ek):]
            break

    return ALIASES.get(ad, ad)


def takim_bul(ad, takimlar):
    hedef = temizle(ad)

    if not hedef:
        return None, 'bos_ad'

    tam = [
        t for t in takimlar
        if temizle(t) == hedef
    ]

    if len(tam) == 1:
        return tam[0], 'tam'

    if len(tam) > 1:
        return None, 'coklu_tam'

    puanlar = sorted(
        (
            (
                SequenceMatcher(
                    None, hedef, temizle(t)
                ).ratio(),
                t,
            )
            for t in takimlar
        ),
        key=lambda x: x[0],
        reverse=True,
    )

    if not puanlar:
        return None, 'bulunamadi'

    en_iyi = puanlar[0]
    ikinci = (
        puanlar[1][0]
        if len(puanlar) > 1 else 0.0
    )

    if (
        en_iyi[0] >= 0.94
        and en_iyi[0] - ikinci >= 0.10
    ):
        return en_iyi[1], 'yaklasik'

    return None, 'belirsiz'


def zaman_kontrolu(deger, simdi):
    if not isinstance(deger, str) or not deger.strip():
        return False

    try:
        tarih = datetime.fromisoformat(
            deger.replace('Z', '+00:00')
        )

        if tarih.tzinfo is None:
            return False

        return (
            tarih.astimezone(timezone.utc) > simdi
        )

    except ValueError:
        return False


def main():
    with open(
        'gelecek_maclar.json',
        encoding='utf-8'
    ) as f:
        kaynak = json.load(f)

    maclar = (
        kaynak['maclar']
        if isinstance(kaynak, dict)
        else kaynak
    )

    if not isinstance(maclar, list):
        raise ValueError(
            'gelecek_maclar.json icinde maclar listesi bulunamadi'
        )

    lig_verileri = tum_ligleri_al()
    simdi = datetime.now(timezone.utc)

    sonuclar = []
    nedenler = Counter()
    eslesmeler = Counter()
    eslesmeyen_maclar = []
    gorulen = set()

    for mac in maclar:
        if not isinstance(mac, dict):
            nedenler['gecersiz_mac'] += 1
            continue

        espn_lig = mac.get('lig_kodu', '')
        lig = LIG_ESLESTIRME.get(espn_lig)

        if not lig:
            nedenler['desteklenmeyen_lig'] += 1
            continue

        if lig not in lig_verileri:
            nedenler['lig_verisi_yok'] += 1
            continue

        if not zaman_kontrolu(
            mac.get('tarih'), simdi
        ):
            nedenler['gecmis_veya_gecersiz_tarih'] += 1
            continue

        anahtar = (
            espn_lig,
            str(mac.get('id')),
            mac.get('tarih'),
            mac.get('ev_sahibi'),
            mac.get('deplasman'),
        )

        if anahtar in gorulen:
            nedenler['tekrar_mac'] += 1
            continue

        gorulen.add(anahtar)

        takimlar = lig_verileri[lig]

        ev, ev_tur = takim_bul(
            mac.get('ev_sahibi', ''),
            takimlar
        )

        dep, dep_tur = takim_bul(
            mac.get('deplasman', ''),
            takimlar
        )

        if not ev or not dep or ev == dep:
            nedenler['takim_eslesmedi'] += 1

            eslesmeyen_maclar.append({
                'lig': espn_lig,
                'ev_sahibi': mac.get('ev_sahibi'),
                'deplasman': mac.get('deplasman'),
                'eslesen_ev': ev,
                'eslesen_dep': dep,
                'ev_durumu': ev_tur,
                'dep_durumu': dep_tur,
            })
            continue

        try:
            analiz = mac_analizi(
                lig, ev, dep, lig_verileri
            )
        except ValueError:
            nedenler['yetersiz_veri'] += 1
            continue

        eslesmeler[ev_tur] += 1
        eslesmeler[dep_tur] += 1

        sonuclar.append({
            'id': mac.get('id'),
            'tarih': mac.get('tarih'),
            'espn_lig': espn_lig,
            'lig': lig,
            'ev': mac.get('ev_sahibi'),
            'dep': mac.get('deplasman'),
            'eslesen_ev': ev,
            'eslesen_dep': dep,
            'ev_eslesme_turu': ev_tur,
            'dep_eslesme_turu': dep_tur,
            'model': 'ESPN_POISSON_TEST',
            'analiz': analiz,
        })

    with open(
        'espn_tahmin_testi.json',
        'w',
        encoding='utf-8'
    ) as f:
        json.dump(
            {
                'toplam_mac': len(maclar),
                'analiz_edilen': len(sonuclar),
                'analiz_edilemeyen': dict(nedenler),
                'eslesmeler': dict(eslesmeler),
                'tahminler': sonuclar,
                'olusturulma_utc': simdi.isoformat(),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with open(
        'eslesmeyen_maclar.json',
        'w',
        encoding='utf-8'
    ) as f:
        json.dump(
            eslesmeyen_maclar,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print('TIPSTER PRO - ESPN ANALIZ TESTI')
    print('TOPLAM MAC:', len(maclar))
    print('ANALIZ EDILEN:', len(sonuclar))
    print('ANALIZ EDILEMEYEN:', dict(nedenler))
    print('ESLESMELER:', dict(eslesmeler))
    print('DOSYA: espn_tahmin_testi.json')

    for sonuc in sonuclar[:10]:
        a = sonuc['analiz']

        print(
            sonuc['ev'], '-', sonuc['dep'],
            '| 1.5:', a['1.5_ust'],
            '| 2.5:', a['2.5_ust'],
            '| 3.5:', a['3.5_ust'],
        )


if __name__ == '__main__':
    main()
