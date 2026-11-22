"""Read-only five-stage audit CLI; writes ONLY user-specified new report path."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
from .analysis import load_history,archive_report,backtest,decision_audit,publication_guard

def main(argv=None):
    p=argparse.ArgumentParser(description='V19 five-stage audit, isolated from V18 production')
    p.add_argument('--arsiv', required=True)
    p.add_argument('--gecmis',help='Optional completed historical match JSON: ESPN or standard schema')
    p.add_argument('--panel', help='Optional panel_tahminler.json for publication safety audit')
    p.add_argument('--ayarlar',help='Optional v18_sonuc_ayarlari.json')
    p.add_argument('--cikti',required=True,help='New output file (will never overwrite)')
    p.add_argument('--test-limit', type=int,default=500,help='Historical rolling test matches (default 500)')
    a=p.parse_args(argv)
    if a.test_limit<=0:p.error('--test-limit positive')
    out=Path(a.cikti)
    if out.exists():p.error('Output exists; no overwriting allowed')
    result={'modul':'TIPSTER_V19_BES_ASAMA_BAGIMSIZ_DENETIM','tarih_utc':datetime.now(timezone.utc).isoformat()}
    result['asama_1_veri']={'durum':'GECMIS_VERI_GIRILMEDI'}
    result['asama_2_gercek_test']={'durum':'GECMIS_VERI_GIRILMEDI'}
    if a.gecmis:
        history,issues=load_history(a.gecmis)
        result['asama_1_veri']={'veri_sayisi':len(history),'sorunlar':issues,'bilgi':'History records stored only in memory'}
        result['asama_2_gercek_test']=backtest(history,limit=a.test_limit)
    result['asama_3_arsiv_ve_hatalar']=archive_report(a.arsiv)
    if a.ayarlar:
        cfg=json.loads(Path(a.ayarlar).read_text(encoding='utf-8-sig'))
        result['asama_4_karar_denetimi']=decision_audit(result['asama_3_arsiv_ve_hatalar'],cfg)
    else:result['asama_4_karar_denetimi']={'durum':'AYAR_DOSYASI_GIRILMEDI'}
    if a.panel:result['asama_5_yayin_koruma']=publication_guard(a.arsiv,a.panel)
    else:result['asama_5_yayin_koruma']={'durum':'PANEL_DOSYASI_GIRILMEDI'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print('DENETIM_RAPORU:',out)
    print('BASARI:',result['asama_3_arsiv_ve_hatalar']['basari_yuzdesi'])
    return result

if __name__=='__main__':main()
