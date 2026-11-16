"""Conservative team matcher: exact or explicitly approved aliases only.
No fuzzy auto-accept; ambiguity blocks prediction. Offline-safe and read-only.
"""
import json, unicodedata, re
from pathlib import Path

def norm(s):
    s=unicodedata.normalize("NFKD", str(s)).casefold()
    s="".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+",s))

def match_team(name, teams, league, aliases=None):
    if not league or not name:
        return {"status":"unmatched", "team":None, "reason":"missing_input"}
    teams=list(teams)
    idx={}
    for t in teams:
        idx.setdefault(norm(t),[]).append(t)
    key=norm(name)
    candidates=idx.get(key,[])
    if len(candidates)==1:
        return {"status":"matched", "team":candidates[0],"reason":"exact_normalized"}
    if len(candidates)>1:
        return {"status":"ambiguous","team":None,"reason":"duplicate_normalized"}
    aliases=aliases or {}
    approved=aliases.get(league,{})
    targets={norm(v) for k,v in approved.items() if norm(k)==key}
    if len(targets)!=1:
        return {"status":"unmatched" if not targets else "ambiguous","team":None,"reason":"no_approved_alias" if not targets else "conflicting_alias"}
    target=next(iter(targets))
    candidates=idx.get(target,[])
    if len(candidates)==1:
        return {"status":"matched","team":candidates[0],"reason":"approved_alias"}
    return {"status":"unmatched" if not candidates else "ambiguous","team":None,"reason":"alias_target_missing" if not candidates else "alias_target_ambiguous"}

def match_fixture(home,away,teams,league,aliases=None):
    a=match_team(home,teams,league,aliases)
    b=match_team(away,teams,league,aliases)
    status="matched" if a['status']==b['status']=="matched" and a['team']!=b['team'] else "review"
    return {"status":status,"home":a,"away":b}

def load_approved(path=None):
    p=Path(path) if path else Path(__file__).with_name('dogrulanmis_aliaslar.json')
    return json.loads(p.read_text(encoding='utf-8'))
