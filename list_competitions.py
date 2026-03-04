import betfairlightweight
from betfairlightweight.filters import market_filter
import os
import csv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Betfair.env"))

USERNAME = os.environ["BF_USERNAME"]
PASSWORD = os.environ["BF_PASSWORD"]
APP_KEY  = os.environ["BF_APP_KEY"]

_script_dir = os.path.dirname(os.path.abspath(__file__))
MY_CERTS = (
    os.path.join(_script_dir, "certs", "client-2048.crt"),
    os.path.join(_script_dir, "certs", "client-2048.key"),
)

trading = betfairlightweight.APIClient(
    username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS
)

try:
    trading.login()
except Exception as e:
    print(f"Login failed: {e}")
    raise SystemExit(1)

competitions = trading.betting.list_competitions(
    filter=market_filter(event_type_ids=["1"])
)

competitions_sorted = sorted(competitions, key=lambda x: x.competition.name)

csv_path = os.path.join(_script_dir, "competitions.csv")

print(f"\n{'ID':>12}  {'Name'}")
print("-" * 50)

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Competition ID", "Competition Name", "Region"])
    for c in competitions_sorted:
        region = getattr(c, "competition_region", "")
        print(f"{c.competition.id:>12}  {c.competition.name}")
        writer.writerow([c.competition.id, c.competition.name, region])

print(f"\n📄 Full list saved to: {csv_path}")
