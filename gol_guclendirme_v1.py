"""TIPSTER PRO: güvenli, çevrimdışı gol olasılık motoru (opsiyonel).
Girdi: bitmiş maç kayıtları (UTC başlangıç), hedef maç başlangıcı.
Çıktı: kanıt yoksa RISKLI. Tahmin arşivlerine yazmaz.
"""
import math
from datetime import datetime, timezone, timedelta

def utc(value):
    if isinstance(value, datetime):
        d = value
    else:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Saat dilimi zorunlu")
    return d.astimezone(timezone.utc)

def valid_history(matches, league, kickoff, minimum_match_duration_minutes=120):
    cutoff = utc(kickoff)
    result = []
    seen = set()
    for m in matches:
        if m.get("league") != league or m.get("status") != "FT":
            continue
        try:
            start = utc(m["kickoff"])
            home, away = str(m["home"]).strip(), str(m["away"]).strip()
            hg, ag = m["home_goals"], m["away_goals"]
            if not isinstance(hg, int) or isinstance(hg, bool) or not isinstance(ag, int) or isinstance(ag, bool):
                continue
            if hg < 0 or ag < 0 or hg > 30 or ag > 30 or not home or not away or home == away:
                continue
            # FT sonucu ancak maç tamamlandıktan sonra tahmin için kullanılabilir.
            # Bitirme zamanı yoksa muhafazakâr 120 dakika güvenlik payı uygula.
            finished = m.get("finished_at") or m.get("completed_at")
            if finished is not None:
                if utc(finished) >= cutoff or utc(finished) < start:
                    continue
            elif start + timedelta(minutes=minimum_match_duration_minutes) >= cutoff:
                continue
            key = (start, home.casefold(), away.casefold())
            if key in seen:
                continue
            seen.add(key)
            result.append((start, home, away, hg, ag))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return sorted(result, key=lambda x: x[0])

def over_probability(lam, line):
    if not (math.isfinite(lam) and 0 <= lam <= 20):
        raise ValueError("Geçersiz gol beklentisi")
    if line not in (1.5, 2.5, 3.5, 4.5, 5.5, 6.5):
        raise ValueError("Desteklenmeyen çizgi")
    k = int(line)
    term = math.exp(-lam)
    cdf = term
    for n in range(1, k + 1):
        term *= lam / n
        cdf += term
    return max(0.0, min(1.0, 1.0 - cdf))

def predict(matches, league, home, away, kickoff, min_team_matches=5, prior_games=8):
    if not league or not home or not away or home == away:
        return {"decision":"RISKLI", "reason":"invalid_fixture"}
    history = valid_history(matches, league, kickoff)
    # En az 20 maçlık lig örneği ve takım başına 5 maç olmadan olasılık üretme.
    if len(history) < 20:
        return {"decision":"RISKLI", "reason":"insufficient_league_history", "league_games":len(history)}
    hg_avg = sum(m[3] for m in history) / len(history)
    ag_avg = sum(m[4] for m in history) / len(history)
    if hg_avg <= 0 or ag_avg <= 0:
        return {"decision":"RISKLI", "reason":"invalid_league_baseline"}
    home_games = [m for m in history if m[1] == home]
    away_games = [m for m in history if m[2] == away]
    if len(home_games) < min_team_matches or len(away_games) < min_team_matches:
        return {"decision":"RISKLI", "reason":"insufficient_team_history", "home_games":len(home_games),"away_games":len(away_games)}
    # Lig ortalamasına shrinkage: küçük örneklemde aşırı gol tahminlerini frenler.
    def smoothed(total, count, prior):
        return (total + prior_games * prior) / (count + prior_games)
    home_scored = smoothed(sum(m[3] for m in home_games), len(home_games), hg_avg)
    home_conceded = smoothed(sum(m[4] for m in home_games), len(home_games), ag_avg)
    away_scored = smoothed(sum(m[4] for m in away_games), len(away_games), ag_avg)
    away_conceded = smoothed(sum(m[3] for m in away_games), len(away_games), hg_avg)
    lam_home = hg_avg * (home_scored / hg_avg) * (away_conceded / hg_avg)
    lam_away = ag_avg * (away_scored / ag_avg) * (home_conceded / ag_avg)
    total = lam_home + lam_away
    if not math.isfinite(total) or total > 12 or total <= 0:
        return {"decision":"RISKLI", "reason":"implausible_expected_goals"}
    probs = {str(line): round(over_probability(total, line), 6) for line in (1.5,2.5,3.5,4.5,5.5,6.5)}
    return {"decision":"MODEL_OUTPUT_NOT_CALIBRATED", "league":league, "lambda_home":round(lam_home,4),"lambda_away":round(lam_away,4),"over_probabilities":probs,"home_games":len(home_games),"away_games":len(away_games),"league_games":len(history),"note":"Olasılıklar kalibre edilmedi; otomatik ÜST kararı verilmez."}
