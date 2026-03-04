import betfairlightweight
from betfairlightweight.filters import market_filter, price_projection
import os
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
# 2. STRATEGY CONFIGURATION (Your Backtest Edge)
# ==========================================
# CRITERIA 1: Allowed Leagues
# Paste the exact Competition IDs you found in your CSV. 
# (Note: These must be strings inside quotes, e.g., '10932509')
ALLOWED_LEAGUES = [
    '13',       # Brasilian Serie A
    '55',       # French Ligue 1
    '951',      # Portuguese Segunda Liga
    '81',       # Italian Serie A
    '12199689', # Italian Serie B
    '194215',   # Turkish Super Lig
    '12204313', # Spanish Segunda Division
    '843454',   # Uruguayan Primera Division
    '879931'    # Chinese Super League
   #'10932509', # Korean K League 1 - this is not available in the API
]

# CRITERIA 2: Excluded Teams
# The exact spelling from Betfair (case-sensitive). 
# We include the ones you mentioned earlier as examples!
EXCLUDED_TEAMS = [
    'Burgos', 
    'Cittadella',
    'Sport Recife', 
    'Malaga',
    'Cruzeiro MG',
    'Basaksehir',
    'Incheon',
    'Wanderers (Uru)',
    'Varzim',
    'Elche',
    'Fortaleza EC',
    'Reggina',
    'Fluminense',
    'Valladolid',
    'Empoli',
    'Frosinone',
    'Penarol',
    'Besiktas',
    'Cerro Largo',
    'Espanyol',
    'Mallorca',
    'Gwangju',
    'Perugia',
    'Reggiana',
    'Girona',
    'Inter',
    'Fiorentina',
    'Lecce',
    'Cuiaba',
    'Granada',
    'Tenerife',
    'Alcorcon',
    'Spezia',
    'Cerrito',
    'UD Logrones',
    'Pescara',
    'Pordenone',
    'Hatayspor',
    'Galatasaray',
    'Santa Clara',
    'Juventus',
    'Mafra',
    'Rennes',
    'Malatyaspor',
    'Arouca',
    'Clermont',
    'Casa Pia',
    'Leganes',
    'Os Belenenses',
    'Fatih Karagumruk',
    'Penafiel',
    'Ajaccio',
    'Qingdao Jonoon',
    'Centro Atletico Fenix',
    'Carrarese',
    'Guangzhou City',
    'Seongnam',
    'Nice',
    'CD Castellon',
    'Andorra',
    'Andorra CF', # Added a variation just to be safe
    'Man City'
    # Add the rest of your Excel list here...
]

# CRITERIA 3: The Odds Range
MIN_ODDS = 1.81
MAX_ODDS = 2.60


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