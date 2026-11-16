"""TIPSTER PRO - Toplu eslesme denetimi. Tahmin/arsiv dosyalarini DEGISTIRMEZ.
Calistir: python toplu_eslesme_kontrol.py
"""
import csv, json, re, unicodedata
from collections import defaultdict, Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'eslesmeyen_takimlar.json'
if not SOURCE.exists():
    SOURCE=Path('eslesmeyen_takimlar.json')

# Lig bazli ad alternatifleri; sadece hedef ad ilgili ligin gercek veri listesinde varsa kabul edilir.
ALIASES={
 'B1':{'Cercle Brugge KSV':'Cercle Brugge','KAA Gent':'Gent','KVC Westerlo':'Westerlo','OH Leuven':'Oud-Heverlee Leuven','Racing Genk':'Genk','Royal Charleroi SC':'Charleroi','Sint-Truidense':'St Truiden','Standard Liege':'Standard','Union St.-Gilloise':'Union St Gilloise','Waasland-Beveren':'Beveren','Zulte-Waregem':'Waregem'},
 'D1':{'Borussia Dortmund':'Dortmund','Eintracht Frankfurt':'Ein Frankfurt','Hamburg SV':'Hamburg'},
 'E0':{'Coventry City':'Coventry','Leeds United':'Leeds'},
 'E1':{'Birmingham City':'Birmingham','Blackburn Rovers':'Blackburn','Cardiff City':'Cardiff','Lincoln City':'Lincoln','Stoke City':'Stoke','Swansea City':'Swansea'},
 'E2':{'Bradford City':'Bradford','Burton Albion':'Burton','Cambridge United':'Cambridge','Doncaster Rovers':'Doncaster','Huddersfield Town':'Huddersfield','Leicester City':'Leicester','Luton Town':'Luton','Mansfield Town':'Mansfield','Oxford United':'Oxford','Peterborough United':'Peterboro','Plymouth Argyle':'Plymouth','Sheffield Wednesday':'Sheffield Weds','Stockport County':'Stockport','Wigan Athletic':'Wigan','Wycombe Wanderers':'Wycombe'},
 'E3':{'Accrington Stanley':'Accrington','Bristol Rovers':'Bristol Rvs','Cheltenham Town':'Cheltenham','Colchester United':'Colchester','Crewe Alexandra':'Crewe','Exeter City':'Exeter','Grimsby Town':'Grimsby','Northampton Town':'Northampton','Oldham Athletic':'Oldham','Rotherham United':'Rotherham','Salford City':'Salford','Shrewsbury Town':'Shrewsbury','Swindon Town':'Swindon','Tranmere Rovers':'Tranmere','York City':'York'},
 'F1':{'AJ Auxerre':'Auxerre','AS Monaco':'Monaco'},
 'I1':{'AS Roma':'Roma'},
 'N1':{'ADO Den Haag':'Den Haag','Ajax Amsterdam':'Ajax','FC Twente':'Twente','FC Utrecht':'Utrecht','Feyenoord Rotterdam':'Feyenoord','Fortuna Sittard':'For Sittard','NEC Nijmegen':'Nijmegen','PEC Zwolle':'Zwolle','SC Cambuur':'Cambuur'},
 'P1':{'Braga':'Sp Braga','C.D. Nacional':'Nacional','FC Porto':'Porto','Sporting CP':'Sporting','Vitória de Guimaraes':'Guimaraes'},
 'SP1':{'Atlético Madrid':'Ath Madrid','Celta Vigo':'Celta','Deportivo':'La Coruna','Racing Santander':'Santander','Real Betis':'Betis','Real Sociedad':'Sociedad'},
 'T1':{'Amed SFK':'Amedspor','Erzurum BB':'Erzurumspor','Istanbul Basaksehir':'Basaksehir','Çorum FK':'Corum','Çorum FK':'Corum FK'},
}
def norm(s):
    s=unicodedata.normalize('NFKD',s or '').casefold()
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]','',s)

def main():
    rows=json.loads(SOURCE.read_text(encoding='utf-8'))
    names=defaultdict(lambda:Counter())
    for row in rows:
        for namefield,matchfield in [('ev_sahibi','eslesen_ev'),('deplasman','eslesen_deplasman')]:
            if row.get(matchfield) is None:
                names[row['veri_ligi']][row[namefield]]+=1
    try:
        from coklu_lig_motoru import lig_verisi_al
    except ImportError:
        lig_verisi_al=None
    results=[]; rosters={}; errors={}
    for league in sorted(names):
        try:
            if lig_verisi_al is None:raise RuntimeError('coklu_lig_motoru.py bu klasorde degil')
            roster=lig_verisi_al(league)
            if not isinstance(roster,dict) or not roster:raise ValueError('bos/uygunsuz lig verisi')
            rosters[league]=list(roster)
        except Exception as exc:
            errors[league]=str(exc)
            rosters[league]=[]
        normalized=defaultdict(list)
        for team in rosters[league]:normalized[norm(team)].append(team)
        for name,count in sorted(names[league].items()):
            options=[]
            for suggestion in [name,ALIASES.get(league,{}).get(name,'')]:
                options.extend(normalized.get(norm(suggestion),[]))
            options=sorted(set(options))
            status='DOGRULANDI' if len(options)==1 else ('BELIRSIZ' if len(options)>1 else 'KONTROL_GEREKLI')
            results.append({'lig':league,'kaynak_takim':name,'mac_tekrari':count,
                'onerilen_veri_adi':options[0] if len(options)==1 else '',
                'durum':status,'not':errors.get(league,'') if not options else ''})
        fieldnames = [
        'lig',
        'kaynak_takim',
        'mac_tekrari',
        'onerilen_veri_adi',
        'durum',
        'not'
    ]

    with open(ROOT/'toplu_eslesme_sonuclari.csv',
              'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
        
    verified={}
    for r in results:
        if r['durum']=='DOGRULANDI':verified.setdefault(r['lig'],{})[r['kaynak_takim']]=r['onerilen_veri_adi']
    (ROOT/'dogrulanmis_aliaslar.json').write_text(json.dumps(verified,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'kayit_sayisi':len(rows),'benzersiz_lig_takim':len(results),
        'dogrulanan':sum(r['durum']=='DOGRULANDI' for r in results),
        'kontrol_gereken':sum(r['durum']!='DOGRULANDI' for r in results),
        'veri_hatalari':errors}
    (ROOT/'toplu_eslesme_ozet.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print('Tahminler ve mevcut arsiv DEGISMEDI. Yalnizca denetim raporlari uretildi.')
if __name__=='__main__':main()
