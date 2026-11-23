"""CLI: creates new V19 reports; never changes V18 source or archive files."""
import argparse,json
from pathlib import Path
from .engine import recover,write_new_json
from .preview import html_preview

def main(argv=None):
    parser=argparse.ArgumentParser(description='TIPSTER V19 read-only recovery and independent panel preview')
    parser.add_argument('--fikstur',required=True)
    parser.add_argument('--v18',required=True)
    parser.add_argument('--arsiv',required=True)
    parser.add_argument('--cikti-klasor',required=True)
    parser.add_argument('--gecmis-gun',type=int,default=180)
    args=parser.parse_args(argv)
    out=Path(args.cikti_klasor)
    if out.exists():parser.error('Cikti klasoru zaten var; kayitlarin uzerine yazilmaz')
    fixture=json.loads(Path(args.fikstur).read_text(encoding='utf-8-sig'))
    v18=json.loads(Path(args.v18).read_text(encoding='utf-8-sig'))
    archive=json.loads(Path(args.arsiv).read_text(encoding='utf-8-sig'))
    recovered,panel,report=recover(fixture,v18,archive,history_days=args.gecmis_gun)
    out.mkdir(parents=True,exist_ok=False)
    write_new_json(out/'v19_kurtarilan_tahminler.json',recovered)
    write_new_json(out/'panel_tahminler_v19_onizleme.json',panel)
    write_new_json(out/'v19_kurtarma_raporu.json',report)
    with (out/'v19_kurtarma_panel.html').open('x',encoding='utf-8') as f:f.write(html_preview(panel,report))
    print('KURTARILAN:',report['kurtarilan'],'PANEL_ONIZLEME:',report['panel_onizleme_mac'])
    print('NEDENLER:',report['nedenler'])
    print('DOSYALAR:',out)

if __name__=='__main__':main()
