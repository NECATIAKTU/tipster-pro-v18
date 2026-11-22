"""CSV loader uses completed football-data.co.uk style scores; no internet calls."""
import csv
from datetime import datetime,timezone

def read_csv(paths,league_codes=None):
    events=[]; bad=0
    for file in paths:
        code=(league_codes or {}).get(file) or file.rsplit('/',1)[-1].rsplit('.',1)[0]
        with open(file,encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                try:
                    date=(r.get('Date') or '').strip()
                    t=None
                    for fmt in ('%d/%m/%Y','%d/%m/%y','%Y-%m-%d'):
                        try:t=datetime.strptime(date,fmt).replace(tzinfo=timezone.utc);break
                        except ValueError:continue
                    if t is None:raise ValueError('date')
                    home=(r.get('HomeTeam') or '').strip();away=(r.get('AwayTeam') or '').strip()
                    hg=int(r['FTHG']);ag=int(r['FTAG'])
                    if not home or not away or min(hg,ag)<0:raise ValueError('score')
                    # Dates only: backtests may see same-day results only after the next day.
                    events.append({'tarih':t.isoformat(),'lig_kodu':code,'ev_sahibi':home,
                                   'deplasman':away,'ev_gol':hg,'dep_gol':ag})
                except (ValueError,TypeError,KeyError):bad+=1
    return events,bad
