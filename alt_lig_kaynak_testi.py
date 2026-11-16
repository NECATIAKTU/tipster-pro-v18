
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Bunlar test edilecek aday kodlardir.
# ESPN tarafindan desteklendikleri henuz dogrulanmadi.
LEAGUES = {
    "Isvicre Challenge League": "sui.2",
    "Danimarka 1st Division": "den.2",
    "Belcika Challenger Pro League": "bel.2",
    "Avusturya 2. Liga": "aut.2",
}

BASE = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/soccer/{league}/scoreboard"
)

def main():
    for name, code in LEAGUES.items():
        url = BASE.format(league=code)
        url += "?dates=20261109-20261116&limit=500"

        print("\nLIG:", name, "| KOD:", code)

        try:
            req = Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urlopen(req, timeout=20) as response:
                data = json.load(response)

            events = data.get("events", [])
            league_info = data.get("leagues", [])

            print("HTTP: 200")
            print("API lig bilgisi:", league_info)
            print("Bulunan mac:", len(events))

            if not league_info and not events:
                print("DURUM: DESTEK BELIRSIZ")
            else:
                print("DURUM: VERI DONDU")

        except HTTPError as exc:
            print("HTTP HATASI:", exc.code)
        except URLError as exc:
            print("BAGLANTI HATASI:", exc.reason)
        except (ValueError, TypeError) as exc:
            print("VERI HATASI:", str(exc))

if __name__ == "__main__":
    main()
