"""V18 independent enhancement research module. Never changes V18 picks or archives.

Input: ESPN completed events (list) for one league and a list of fixtures with
matching ESPN team displayNames. Output: independent candidate probabilities.
No network access, no file writes, no threshold or betting selection logic.
"""
from collections import defaultdict
from datetime import datetime, timezone
import math

LINES = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


def _utc(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None


def completed_games(events, cutoff=None):
    """Deduplicate by ESPN event id; never use games at/after cutoff."""
    unique = {}
    for event in events:
        try:
            if event['status']['type']['completed'] is not True:
                continue
            start = _utc(event['date'])
            if start is None or (cutoff is not None and start >= cutoff):
                continue
            competitors = event['competitions'][0]['competitors']
            home = next(c for c in competitors if c['homeAway'] == 'home')
            away = next(c for c in competitors if c['homeAway'] == 'away')
            h, a = home['team']['displayName'], away['team']['displayName']
            hg, ag = int(home['score']), int(away['score'])
            if not h or not a or h == a or min(hg, ag) < 0:
                continue
            key = str(event['id'])
            if key:
                unique[key] = (start, key, h, a, hg, ag)
        except (KeyError, IndexError, TypeError, ValueError, StopIteration):
            continue
    return sorted(unique.values(), key=lambda x: (x[0], x[1]))


def poisson_over(expected_goals, line):
    if not math.isfinite(expected_goals) or expected_goals < 0:
        raise ValueError('Invalid expected goals')
    kmax = int(line - 0.5)
    term = math.exp(-expected_goals)
    cdf = term
    for k in range(1, kmax + 1):
        term *= expected_goals / k
        cdf += term
    return max(0.0, min(100.0, 100.0 * (1.0 - cdf)))


def estimate(games, home_name, away_name, min_games=5):
    """Shrink team rates to league mean; add home/away and recency information.

    Candidate research model, NOT validated or calibrated. All games must be
    strictly earlier than the fixture being predicted.
    """
    teams = defaultdict(lambda: {'all': [], 'home': [], 'away': []})
    total_home = total_away = 0
    for start, event_id, home, away, hg, ag in games:
        teams[home]['all'].append((start, hg, ag))
        teams[home]['home'].append((start, hg, ag))
        teams[away]['all'].append((start, ag, hg))
        teams[away]['away'].append((start, ag, hg))
        total_home += hg
        total_away += ag
    n = len(games)
    if n < 10 or home_name not in teams or away_name not in teams:
        return {'durum': 'YETERSIZ_VERI'}
    home, away = teams[home_name], teams[away_name]
    if min(len(home['all']), len(away['all'])) < min_games:
        return {'durum': 'YETERSIZ_VERI'}
    league_home = max(0.2, total_home / n)
    league_away = max(0.2, total_away / n)
    league_team = (total_home + total_away) / (2 * n)

    def rate(rows, index, prior, strength=5):
        return (sum(row[index] for row in rows) + strength * prior) / (len(rows) + strength)

    def recent(rows, index, prior):
        last = rows[-5:]
        weights = range(1, len(last) + 1)
        return (sum(row[index] * w for row, w in zip(last, weights)) + 5 * prior) / (sum(weights) + 5)

    # Separate home/away rates, shrunk toward league venue-specific baselines.
    h_attack = rate(home['home'], 1, league_home)
    h_defense = rate(home['home'], 2, league_away)
    a_attack = rate(away['away'], 1, league_away)
    a_defense = rate(away['away'], 2, league_home)
    # Relative strengths avoid conflating a high-scoring league with a strong team.
    expected_home = league_home * (h_attack / league_home) * (a_defense / league_home)
    expected_away = league_away * (a_attack / league_away) * (h_defense / league_away)
    # Limited recent-form correction, regularized to the league baseline.
    h_form = (recent(home['all'], 1, league_team) + recent(away['all'], 2, league_team)) / 2
    a_form = (recent(away['all'], 1, league_team) + recent(home['all'], 2, league_team)) / 2
    expected_home = 0.85 * expected_home + 0.15 * h_form
    expected_away = 0.85 * expected_away + 0.15 * a_form
    expected_total = min(8.0, max(0.0, expected_home + expected_away))
    return {
        'durum': 'ARASTIRMA_TAHMINI',
        'beklenen_gol': round(expected_total, 3),
        'lig_ev_gol_ort': round(league_home, 3),
        'lig_dep_gol_ort': round(league_away, 3),
        'takim_mac_sayilari': {'ev': len(home['all']), 'dep': len(away['all'])},
        'model': 'V18_GUCLENDIRME_V1_ADAY',
        'uyari': 'Kalibre edilmemis arastirma olasiliklari; V18 kilitli secimlerini degistirmez.',
        'olasiliklar': {f'{line}_ust': round(poisson_over(expected_total, line), 1) for line in LINES},
    }


def predict_before_fixture(events, fixture):
    kickoff = _utc(fixture.get('tarih'))
    if kickoff is None:
        return {'durum': 'TARIH_GECERSIZ'}
    games = completed_games(events, cutoff=kickoff)
    return estimate(games, fixture.get('ev_sahibi'), fixture.get('deplasman'))
