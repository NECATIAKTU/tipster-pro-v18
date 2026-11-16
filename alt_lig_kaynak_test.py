
import json
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

URL = (
    "https://raw.githubusercontent.com/"
    "openfootball/football.json/master/"
    "2024-25/ch.2.json"
)

def main():
    print("TIPSTER PRO - ALT LIG KAYNAK TESTI")
    print("Lig: Isvicre Challenge League")
    print("Sezon: 2024-25")

    try:
        with urlopen(URL, timeout=20) as response:
            data = json.load(response)

        matches = data.get("matches", [])
        completed = [
            m for m in matches
            if isinstance(m.get("score"), dict)
            and isinstance(m["score"].get("ft"), list)
            and len(m["score"]["ft"]) == 2
        ]

        print("Toplam mac:", len(matches))
        print("Skoru bulunan mac:", len(completed))

        for m in completed[:3]:
            print(
                m.get("team1"),
                "-",
                m.get("team2"),
                m["score"]["ft"]
            )

    except (HTTPError, URLError, ValueError) as error:
        print("KAYNAK TEST HATASI:", error)

if __name__ == "__main__":
    main()
