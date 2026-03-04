import betfairlightweight
from betfairlightweight.filters import market_filter, price_projection
import os
import json
from dotenv import load_dotenv

# ==========================================
# 1. CREDENTIALS (Keep these secure!)
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
# 2. STRATEGY CONFIGURATION (loaded from strategy_config.json)
# ==========================================
# See strategy_config.example.json for the expected format.
# Your real strategy_config.json is gitignored to keep your edge private.
with open(os.path.join(_script_dir, "strategy_config.json")) as f:
    _config = json.load(f)

ALLOWED_LEAGUES = _config["allowed_leagues"]
EXCLUDED_TEAMS  = _config["excluded_teams"]
MIN_ODDS        = _config["min_odds"]
MAX_ODDS        = _config["max_odds"]


# ==========================================
# 3. INITIALIZE & LOGIN
# ==========================================
trading = betfairlightweight.APIClient(
    username=USERNAME, 
    password=PASSWORD, 
    app_key=APP_KEY, 
    cert_files=MY_CERTS
)
trading.login()
print("✅ Logged in successfully. Firing up the strategy engine...\n")


# ==========================================
# 4. THE EXECUTION ENGINE
# ==========================================
print(f"📊 Filtering for {len(ALLOWED_LEAGUES)} specific leagues...")

# 1. Ask Betfair ONLY for matches in your specific leagues
strategy_filter = market_filter(
    event_type_ids=['1'],
    competition_ids=ALLOWED_LEAGUES,
    market_type_codes=['MATCH_ODDS']
)

# Pull the upcoming matches that fit the league filter
catalogue = trading.betting.list_market_catalogue(
    filter=strategy_filter,
    max_results=100, # Adjust this if you have hundreds of matches a day
    market_projection=['RUNNER_DESCRIPTION', 'COMPETITION', 'EVENT']
)

if not catalogue:
    print("No matches scheduled in your selected leagues right now.")
else:
    print(f"🔍 Found {len(catalogue)} matches in your leagues. Checking criteria...\n")

for market in catalogue:
    match_name = market.event.name
    league_name = market.competition.name if market.competition else "Unknown League"
    
    # Get the names of the teams playing
    runners = [runner.runner_name for runner in market.runners]
    
    # --- CRITERIA 2 CHECK: Excluded Teams ---
    # Does this match contain any team from your blacklist?
    if any(banned_team in runners for banned_team in EXCLUDED_TEAMS):
        print(f"🚫 SKIPPED: {match_name} (Reason: Blacklisted team playing)")
        continue # Skip the rest of the code and move to the next match
        
    # --- CRITERIA 3 CHECK: Live Odds Range ---
    # If the match survives the blacklist, we pull the live order book
    price_filter = price_projection(price_data=['EX_BEST_OFFERS'])
    
    try:
        market_book = trading.betting.list_market_book(
            market_ids=[market.market_id],
            price_projection=price_filter
        )[0]
    except Exception as e:
        continue # If the market is temporarily suspended, skip it securely
    
    # Look at the live prices for the Home and Away teams
    for runner in market_book.runners:
        # Ignore "The Draw"
        runner_name = next((r.runner_name for r in market.runners if r.selection_id == runner.selection_id), "Unknown")
        if runner_name == "The Draw":
            continue

        # Check if there is actual money waiting to be matched on the Back side
        if runner.ex.available_to_back:
            best_back_price = runner.ex.available_to_back[0].price
            
            # Does the price fit perfectly into your backtested range?
            if MIN_ODDS <= best_back_price <= MAX_ODDS:
                print(f"🟢 [GHOST BET TRIGGERED]")
                print(f"   League: {league_name}")
                print(f"   Match : {match_name}")
                print(f"   Action: Back {runner_name} @ {best_back_price}")
                print("-" * 45)

print("\n🏁 Strategy scan complete.")