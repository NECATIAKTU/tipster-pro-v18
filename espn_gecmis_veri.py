
"""TIPSTER PRO - ESPN geçmiş maç veri toplayıcı."""

import json
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LEAGUES = [
    "nor.1", "swe.1", "den.1", "aut.1",
    "usa.1", "mex.1", "bra.1", "arg.1",
    "col.1", "jpn.1", "chn.1", "aus.1",
    "rsa.1", "sui.1", "irl.1", "tur.2",
]

    


DAYS_BACK = 120
WINDOW_DAYS = 1



REQUEST_TIMEOUT = 18


def get_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "TIPSTER-PRO/2.0",
                    "Accept": "application/json",
                },
            )
            with urlopen(
                req, timeout=REQUEST_TIMEOUT
            ) as response:
                return json.load(response)

        except (
            HTTPError, URLError, TimeoutError,
            ValueError, OSError
        ) as exc:
            if attempt == retries - 1:
                print(
                    print(
    "REQUEST_FAILED",
    type(exc).__name__,
    getattr(exc, "code", ""),
    str(exc),
    url,
    flush=True,
)
                    
                    
                )
                return None

            time.sleep(1.5 * (attempt + 1))

    return None


def parse_completed(event, league):
    competition = (
        event.get("competitions") or [{}]
    )[0]

    completed = (
        competition.get("status", {})
        .get("type", {})
        .get("completed")
        or event.get("status", {})
        .get("type", {})
        .get("completed")
    )

    if not completed:
        return None

    competitors = (
        competition.get("competitors") or []
    )

    if len(competitors) != 2:
        return None

    home = next(
        (
            x for x in competitors
            if x.get("homeAway") == "home"
        ),
        None,
    )

    away = next(
        (
            x for x in competitors
            if x.get("homeAway") == "away"
        ),
        None,
    )

    if not home or not away:
        return None

    try:
        hs = int(home["score"])
        aws = int(away["score"])
    except (ValueError, TypeError, KeyError):
        return None

    return {
        "id": str(event.get("id", "")),
        "lig": league,
        "tarih": event.get("date"),
        "ev_id": str(
            home.get("team", {}).get("id", "")
        ),
        "dep_id": str(
            away.get("team", {}).get("id", "")
        ),
        "ev": home.get(
            "team", {}
        ).get("displayName", ""),
        "dep": away.get(
            "team", {}
        ).get("displayName", ""),
        "ev_gol": hs,
        "dep_gol": aws,
    }


def write_json(filename, obj):
    temp = Path(filename + ".tmp")
    temp.write_text(
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temp.replace(filename)


def main():
    now = datetime.now(timezone.utc)

    end_day = (
        now - timedelta(days=1)
    ).date()

    start_day = (
        end_day - timedelta(
            days=DAYS_BACK - 1
        )
    )

    matches = {}
    stats = {}

    for league in LEAGUES:
        counts = Counter()
        cursor = start_day

        while cursor <= end_day:
            last = min(
                cursor + timedelta(
                    days=WINDOW_DAYS - 1
                ),
                end_day,
            )

            date_range = f"{cursor:%Y%m%d}"
                
                
            

            params = urlencode({
                "dates": date_range,
                "limit": 500,
            })

            url = (
                "https://site.api.espn.com/"
                "apis/site/v2/sports/soccer/"
                f"{league}/scoreboard?{params}"
            )

            payload = get_json(url)
            counts["windows"] += 1

            if payload is None:
                counts["failed_windows"] += 1

            else:
                events = payload.get(
                    "events", []
                )

                counts["events_returned"] += (
                    len(events)
                )

                for event in events:
                    record = parse_completed(
                        event, league
                    )

                    if (
                        record
                        and record["id"]
                    ):
                        key = (
                            f"{league}|"
                            f"{record['id']}"
                        )
                        matches[key] = record

            cursor = last + timedelta(days=1)
            time.sleep(0.15)

        counts["completed_unique"] = sum(
            1 for m in matches.values()
            if m["lig"] == league
        )

        stats[league] = dict(counts)

        print(
            league,
            stats[league],
            flush=True,
        )

    records = sorted(
        matches.values(),
        key=lambda m: (
            m["tarih"] or "",
            m["lig"],
            m["id"],
        ),
    )

    write_json(
        "espn_gecmis_maclar.json",
        {
            "created_at_utc": now.isoformat(),
            "matches": records,
        },
    )

    write_json(
        "espn_gecmis_rapor.json",
        {
            "created_at_utc": now.isoformat(),
            "start": str(start_day),
            "end": str(end_day),
            "total": len(records),
            "leagues": stats,
        },
    )

    print("TOTAL_COMPLETED", len(records))
    print(
        "Check report for failed windows "
        "and unsupported date ranges."
    )


if __name__ == "__main__":
    main()
