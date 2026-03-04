import betfairlightweight
from betfairlightweight.filters import market_filter
import pandas as pd
import os
from dotenv import load_dotenv

# ==========================================
# 1. CREDENTIALS & LOGIN SETUP
# ==========================================
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Betfair.env"))

USERNAME = os.environ["BF_USERNAME"]
PASSWORD = os.environ["BF_PASSWORD"]
APP_KEY  = os.environ["BF_APP_KEY"]

_script_dir = os.path.dirname(os.path.abspath(__file__))
MY_CERTS = (
    os.path.join(_script_dir, "certs", "client-2048.crt"),
    os.path.join(_script_dir, "certs", "client-2048.key"),
)

# ==========================================
# 2. INITIALIZE & LOGIN
# ==========================================
trading = betfairlightweight.APIClient(username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS)
trading.login()
print("✅ Logged in successfully!")

# ==========================================
# 3. EXPORT LEAGUES (COMPETITIONS)
# ==========================================
print("\n📊 Downloading all active Soccer Leagues...")
# Ask Betfair for every competition inside Event Type '1' (Soccer)
competitions_req = trading.betting.list_competitions(
    filter=market_filter(event_type_ids=['1'])
)

# Extract the names and IDs into a list
league_list = []
for comp in competitions_req:
    league_list.append({
        "League Name": comp.competition.name,
        "League ID": comp.competition.id
    })

# Use Pandas to magically turn that list into a CSV
df_leagues = pd.DataFrame(league_list)
df_leagues.to_csv("betfair_leagues.csv", index=False)
print(f"✅ Saved {len(df_leagues)} leagues to 'betfair_leagues.csv'")


# ==========================================
# 4. EXPORT TEAMS (RUNNERS)
# ==========================================
print("\n⚽ Downloading active Teams (This takes a few seconds)...")
# To get teams, we have to look at actual matches. We will pull the next 1000 Match Odds markets.
catalogue = trading.betting.list_market_catalogue(
    filter=market_filter(event_type_ids=['1'], market_type_codes=['MATCH_ODDS']),
    max_results=1000,
    market_projection=['RUNNER_DESCRIPTION'] # This tells Betfair to include the team names
)

team_list = []
seen_teams = set() # We use a 'set' to easily avoid adding the same team twice

for market in catalogue:
    for runner in market.runners:
        # Ignore "The Draw" as a team
        if runner.runner_name != "The Draw" and runner.runner_name not in seen_teams:
            seen_teams.add(runner.runner_name)
            team_list.append({
                "Team Name": runner.runner_name,
                "Team ID": runner.selection_id
            })

# Convert to Pandas, sort alphabetically so it's easy for you to read, and save
df_teams = pd.DataFrame(team_list).sort_values(by="Team Name")
df_teams.to_csv("betfair_teams.csv", index=False)
print(f"✅ Saved {len(df_teams)} unique teams to 'betfair_teams.csv'")

print("\n🏁 Export Complete! You can now open these CSV files in Excel.")