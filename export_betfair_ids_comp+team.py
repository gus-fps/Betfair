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
# 3. EXPORT TEAMS (WITH LEAGUE NAMES)
# ==========================================
print("\n⚽ Downloading active Teams and their Leagues...")

# Notice we added 'COMPETITION' to the market_projection list!
catalogue = trading.betting.list_market_catalogue(
    filter=market_filter(event_type_ids=['1'], market_type_codes=['MATCH_ODDS']),
    max_results=1000,
    market_projection=['RUNNER_DESCRIPTION', 'COMPETITION'] 
)

team_list = []
# We will use a 'set' to track combinations of Team + League to avoid endless duplicates
seen_combos = set() 

for market in catalogue:
    # Safely grab the league name (sometimes obscure friendlies don't have one attached)
    league_name = market.competition.name if market.competition else "Unknown/Friendly"
    
    for runner in market.runners:
        if runner.runner_name != "The Draw":
            
            # Create a unique pairing of Team Name and League Name
            unique_combo = (runner.runner_name, league_name)
            
            # Only add it if we haven't seen this exact team + league combo yet
            if unique_combo not in seen_combos:
                seen_combos.add(unique_combo)
                team_list.append({
                    "League Name": league_name,
                    "Team Name": runner.runner_name,
                    "Team ID": runner.selection_id
                })

# Convert to Pandas, sort first by League, then by Team Name for perfect Excel readability
df_teams = pd.DataFrame(team_list).sort_values(by=["League Name", "Team Name"])

# Save the updated file
df_teams.to_csv("betfair_teams.csv", index=False)
print(f"✅ Saved {len(df_teams)} unique Team/League combos to 'betfair_teams.csv'")
print("🏁 Export Complete! Check your new CSV file.")