"""Read-only, chronological backtest for normalized FT history; no claims of calibration.
Usage: python gol_geriye_donuk_test.py --input normalized_matches.json --output backtest_report.json
Input rows: league,home,away,kickoff,status=FT,home_goals,away_goals.
"""
import argparse,json,math
from pathlib import Path
from gol_guclendirme_v1 import predict,utc

def backtest(rows):
    matches=sorted((m for m in rows if m.get("status")=="FT" and m.get("kickoff")),key=lambda m:utc(m["kickoff"]))
    scored={str(x):[] for x in (1.5,2.5,3.5,4.5,5.5,6.5)}
    skipped={}
    for m in matches:
        try:
            pred=predict(matches,m["league"],m["home"],m["away"],m["kickoff"])
            if pred["decision"]!="MODEL_OUTPUT_NOT_CALIBRATED":
                reason=pred.get("reason","unknown");skipped[reason]=skipped.get(reason,0)+1;continue
            goals=int(m["home_goals"])+int(m["away_goals"])
            for line,prob in pred["over_probabilities"].items():
                scored[line].append((prob,float(goals>float(line))))
        except (KeyError,TypeError,ValueError,OverflowError) as e:
            skipped["invalid_row"]=skipped.get("invalid_row",0)+1
    return {"warning":"Retrospective diagnostic only; no model calibration or guarantee.","matches":len(matches),"skipped":skipped,"markets":{k:{"n":len(v),"brier":round(sum((p-y)**2 for p,y in v)/len(v),5) if v else None,"actual_over_rate":round(sum(y for _,y in v)/len(v),5) if v else None,"mean_probability":round(sum(p for p,_ in v)/len(v),5) if v else None} for k,v in scored.items()}}

def main():
    a=argparse.ArgumentParser();a.add_argument("--input",required=True);a.add_argument("--output",required=True);args=a.parse_args()
    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(data,list):raise ValueError("Input must be a list of normalized FT matches")
    result=backtest(data)
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
