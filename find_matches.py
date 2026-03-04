import betfairlightweight
from betfairlightweight.filters import market_filter
import os
from dotenv import load_dotenv

# 1. CREDENTIALS & LOGIN SETUP
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Betfair.env"))

USERNAME = os.environ["BF_USERNAME"]
PASSWORD = os.environ["BF_PASSWORD"]
APP_KEY  = os.environ["BF_APP_KEY"]

_script_dir = os.path.dirname(os.path.abspath(__file__))
MY_CERTS = (
    os.path.join(_script_dir, "certs", "client-2048.crt"),
    os.path.join(_script_dir, "certs", "client-2048.key"),
)

# 3. Initialize and Login (Notice the new 'cert_files' parameter)
trading = betfairlightweight.APIClient(
    username=USERNAME, 
    password=PASSWORD, 
    app_key=APP_KEY, 
    cert_files=MY_CERTS
)

trading.login()

print("✅ Logged in successfully!")
print("🔍 Scanning Betfair for live and upcoming Soccer matches...\n")

# 4. Create a filter for Soccer (Event Type '1')
soccer_filter = market_filter(event_type_ids=['1'])

# 5. Ask the API to list all events matching our filter
soccer_events = trading.betting.list_events(filter=soccer_filter)

# 6. Print out the results
print(f"Total soccer events found right now: {len(soccer_events)}")
print("-" * 40)

for idx, event_result in enumerate(soccer_events[:10], start=1):
    match_name = event_result.event.name
    country = event_result.event.country_code
    print(f"{idx}. {match_name} (Location: {country})")

print("-" * 40)