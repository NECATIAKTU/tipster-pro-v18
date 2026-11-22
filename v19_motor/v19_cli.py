#!/usr/bin/env python3
"""Independent read-only TIPSTER V19 lab, no V18 writes or live publication."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from v19_core.engine import sanitize,forecast,select,utc,walk_forward
from v19_core.audit import archive_audit
from v19_core.loaders import read_csv

def get_events(ns):
    if ns.csv:
        events,bad=read_csv(ns.csv)
        return events,{'csv_gecersiz':bad}
    obj=json.loads(Path(ns.events).read_text(encoding='utf-8'))
    return obj.get('maclar',[]) if isinstance(obj,dict) else obj,{}

def write_new(path,data):
    dest=Path(path)
    if dest.exists():raise FileExistsError('Mevcut rapor korunuyor; farkli cikti adi verin: '+str(dest))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('RAPOR:',dest)

def main(argv=None):
    ap=argparse.ArgumentParser(description='V19 shadow-only: V18 tahmin, panel veya arşivini değiştirmez')
    sub=ap.add_subparsers(dest='command',required=True)
    a=sub.add_parser('arsiv');a.add_argument('--arsiv',required=True);a.add_argument('--cikti',required=True)
    for task in ('test','tahmin'):
        b=sub.add_parser(task);source=b.add_mutually_exclusive_group(required=True)
        source.add_argument('--events');source.add_argument('--csv',nargs='+')
        b.add_argument('--cikti',required=True)
        if task=='tahmin':b.add_argument('--fikstur',required=True)
    ns=ap.parse_args(argv)
    if ns.command=='arsiv':
        obj=json.loads(Path(ns.arsiv).read_text(encoding='utf-8'))
        rows=obj if isinstance(obj,list) else obj.get('kayitlar',obj.get('tahminler',[]))
        out=archive_audit(rows)
    else:
        events,issues=get_events(ns)
        if ns.command=='test':out=walk_forward(events);out['yukleyici']=issues
        else:
            clean,problems=sanitize(events)
            obj=json.loads(Path(ns.fikstur).read_text(encoding='utf-8'))
            fixtures=obj if isinstance(obj,list) else obj.get('maclar',[])
            now=datetime.now(timezone.utc)
            out={'model':'TIPSTER_V19_GOL_MOTORU_DENEYSEL','olusturulma_utc':now.isoformat(),
                 'veri_kalitesi':problems,'yukleyici':issues,'tahminler':[]}
            for fix in fixtures:
                try:
                    kickoff=utc(fix['tarih'])
                    if kickoff<=now:continue
                    # Hard cutoff at run time and match start, preventing future information use
                    prior=[m for m in clean if m['tarih']<now and m['tarih']<kickoff]
                    model=forecast(prior,fix)
                    out['tahminler'].append({'mac':fix,'hesaplama_utc':now.isoformat(),
                                             'model':model,'secim':select(model)})
                except (KeyError,TypeError,ValueError) as exc:
                    out['tahminler'].append({'mac':fix,'secim':{'karar':'PAS','neden':'GECERSIZ_FIKSTUR'},'hata':str(exc)})
    write_new(ns.cikti,out)
if __name__=='__main__':main()
