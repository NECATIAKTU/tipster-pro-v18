from collections import defaultdict
from datetime import datetime, timedelta
from gol_modeli import bos_takim


SURUM = "GELISTIRME VERI V1"

FINAL_STATUS = {
    "STATUS_FINAL",
    "STATUS_FULL_TIME",
    "STATUS_FT",
}


def historical_stats(lig, now, days, fetch):
    if now.tzinfo is None or days < 1:
        raise ValueError("Gecersiz tarih araligi")

    events = {}
    conflicts = set()
    errors = 0
    rejected = 0

    earliest = now - timedelta(days=days)
    cutoff = now - timedelta(hours=6)

    for i in range(1, days + 1):
        try:
            date = (now - timedelta(days=i)).date()
            payload = fetch(lig, date)

            if not isinstance(payload, dict):
                raise ValueError("Gecersiz veri")

            if not isinstance(payload.get("events"), list):
                raise ValueError("Mac listesi eksik")

        except (OSError, ValueError, KeyError, TypeError):
            errors += 1
            continue

        for event in payload["events"]:
            try:
                status = event["status"]["type"]

                if status.get("completed") is not True:
                    continue

                name = status.get("name")

                if name and name not in FINAL_STATUS:
                    raise ValueError("Gecersiz mac durumu")

                raw_id = event["id"]

                if not isinstance(raw_id, (str, int)):
                    raise ValueError("Gecersiz kimlik")

                if isinstance(raw_id, bool):
                    raise ValueError("Gecersiz kimlik")

                key = str(raw_id).strip()

                dt = datetime.fromisoformat(
                    event["date"].replace("Z", "+00:00")
                )

                if not key or dt.tzinfo is None:
                    raise ValueError("Gecersiz tarih")

                if not earliest <= dt <= cutoff:
                    raise ValueError("Tarih araligi disinda")

                competitors = event["competitions"][0]["competitors"]

                homes = [
                    x for x in competitors
                    if x["homeAway"] == "home"
                ]

                aways = [
                    x for x in competitors
                    if x["homeAway"] == "away"
                ]

                if (
                    len(competitors) != 2
                    or len(homes) != 1
                    or len(aways) != 1
                ):
                    raise ValueError("Takim hatasi")

                home = homes[0]
                away = aways[0]

                hn = home["team"]["displayName"]
                an = away["team"]["displayName"]

                if not all(
                    isinstance(n, str) and n.strip()
                    for n in (hn, an)
                ) or hn == an:
                    raise ValueError("Takim adi hatasi")

                scores = [home["score"], away["score"]]

                if not all(
                    str(v).isascii() and str(v).isdigit()
                    for v in scores
                ):
                    raise ValueError("Skor hatasi")

                hg, ag = map(int, scores)

                row = (dt, key, hn, an, hg, ag)

                if key in events and events[key] != row:
                    conflicts.add(key)

                events[key] = row

            except (
                KeyError,
                IndexError,
                AttributeError,
                ValueError,
                TypeError,
            ):
                rejected += 1

    rows = sorted(
        row for key, row in events.items()
        if key not in conflicts
    )

    teams = defaultdict(bos_takim)

    for _, _, home, away, hg, ag in rows:

        for name, side, goals, conceded in [
            (home, "ev", hg, ag),
            (away, "dep", ag, hg),
        ]:
            team = teams[name]

            team["mac"] += 1
            team["attigi"] += goals
            team["yedigi"] += conceded

            team[side + "_mac"] += 1
            team[side + "_attigi"] += goals
            team[side + "_yedigi"] += conceded

            team["son_maclar"].append(
                (goals, conceded)
            )

    report = {
        "tamamlanmis_mac": len(rows),
        "hata_gunu": errors,
        "sorgu_gunu": days,
        "gecersiz_kayit": rejected,
        "celiskili_mac": len(conflicts),
    }

    return dict(teams), report
