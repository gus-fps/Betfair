import betfairlightweight
from betfairlightweight.filters import market_filter, price_projection
import pandas as pd
import os
import time
from datetime import datetime, timezone
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
# 2. STRATEGY CONFIGURATION 
# ==========================================
PAPER_STAKE = 10.00  # The flat amount you want to "paper bet"
MIN_ODDS = 1.81
MAX_ODDS = 2.60

# CRITERIA 1: Allowed Leagues
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
EXCLUDED_TEAMS = [
    'Burgos', 'Cittadella', 'Sport Recife', 'Malaga', 'Cruzeiro MG', 'Basaksehir',
    'Incheon', 'Wanderers (Uru)', 'Varzim', 'Elche', 'Fortaleza EC', 'Reggina',
    'Fluminense', 'Valladolid', 'Empoli', 'Frosinone', 'Penarol', 'Besiktas',
    'Cerro Largo', 'Espanyol', 'Mallorca', 'Gwangju', 'Perugia', 'Reggiana',
    'Girona', 'Inter', 'Fiorentina', 'Lecce', 'Cuiaba', 'Granada', 'Tenerife',
    'Alcorcon', 'Spezia', 'Cerrito', 'UD Logrones', 'Pescara', 'Pordenone',
    'Hatayspor', 'Galatasaray', 'Santa Clara', 'Juventus', 'Mafra', 'Rennes',
    'Malatyaspor', 'Arouca', 'Clermont', 'Casa Pia', 'Leganes', 'Os Belenenses',
    'Fatih Karagumruk', 'Penafiel', 'Ajaccio', 'Qingdao Jonoon', 'Centro Atletico Fenix',
    'Carrarese', 'Guangzhou City', 'Seongnam', 'Nice', 'CD Castellon', 'Andorra',
    'Andorra CF', 'Man City'
]
EXCLUDED_TEAMS_SET = set(EXCLUDED_TEAMS)

# ==========================================
# 3. LEDGER INITIALIZATION
# ==========================================
CSV_FILE = os.path.join(_script_dir, "paper_trading_ledger.csv")

# If the ledger doesn't exist, create it with our new advanced columns
if not os.path.exists(CSV_FILE):
    df_initial = pd.DataFrame(columns=[
        "Timestamp", "Market_ID", "Selection_ID", "League", "Match", 
        "Selection", "Stake", "Matched_Odds", "Result", "Profit"
    ])
    df_initial.to_csv(CSV_FILE, index=False)

trading = betfairlightweight.APIClient(username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS)
try:
    trading.login()
except Exception as e:
    print(f"Login failed: {e}")
    raise SystemExit(1)
print("✅ Logged in successfully. Firing up the strategy engine...\n")

# ==========================================
# 4. THE CONTINUOUS EXECUTION ENGINE
# ==========================================
while True:
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] 📡 Scanning markets and checking settlements...")

    # Load the current ledger into Pandas
    try:
        df_ledger = pd.read_csv(CSV_FILE)
    except PermissionError:
        print("⚠️ ERROR: Please close the CSV file in Excel so the bot can read/write to it!")
        time.sleep(10)
        continue

    # ---------------------------------------------------------
    # ROUTINE A: SETTLE PENDING BETS
    # ---------------------------------------------------------
    pending_bets = df_ledger[df_ledger['Result'] == 'PENDING']
    
    for index, row in pending_bets.iterrows():
        market_id = str(row['Market_ID'])
        selection_id = int(float(row['Selection_ID']))  # int(float()) handles "47972.0" from CSV
        stake = float(row['Stake'])
        odds = float(row['Matched_Odds'])

        try:
            # Ask Betfair for the current status of this specific market
            settlement_check = trading.betting.list_market_book(market_ids=[market_id])[0]
            
            if settlement_check.status == 'CLOSED':
                # The match is over. Let's find out who won.
                for runner in settlement_check.runners:
                    if runner.selection_id == selection_id:
                        if runner.status == 'WINNER':
                            df_ledger.at[index, 'Result'] = 'WIN'
                            df_ledger.at[index, 'Profit'] = round(stake * (odds - 1), 2)
                            print(f"💰 SETTLED WIN: {row['Match']} (+£{df_ledger.at[index, 'Profit']})")
                        elif runner.status == 'LOSER':
                            df_ledger.at[index, 'Result'] = 'LOSS'
                            df_ledger.at[index, 'Profit'] = -stake
                            print(f"📉 SETTLED LOSS: {row['Match']} (-£{stake})")
        except Exception as e:
            print(f"⚠️ Could not check settlement for market {market_id}: {e}")
            
    # Save the updated settlements back to the CSV
    df_ledger.to_csv(CSV_FILE, index=False)

    # Build deduplication set — cast Selection_ID to int to avoid "47972.0" vs "47972" mismatches
    placed_market_selection_ids = set(
        df_ledger['Market_ID'].astype(str) + "_" + df_ledger['Selection_ID'].apply(lambda x: str(int(float(x))))
    )


    # ---------------------------------------------------------
    # ROUTINE B: FIND NEW BETS
    # ---------------------------------------------------------
    strategy_filter = market_filter(
        event_type_ids=['1'],
        competition_ids=ALLOWED_LEAGUES,
        market_type_codes=['MATCH_ODDS']
    )

    catalogue = trading.betting.list_market_catalogue(
        filter=strategy_filter,
        max_results=100, 
        market_projection=['RUNNER_DESCRIPTION', 'COMPETITION', 'EVENT', 'MARKET_START_TIME']
    )

    new_bets_found = False

    if catalogue:
        for market in catalogue:
            match_name = market.event.name
            league_name = market.competition.name if market.competition else "Unknown"
            runners = {runner.runner_name for runner in market.runners}  # set for O(1) lookup

            # CRITERIA 3: Only act within 90 minutes of kick-off
            kickoff = market.market_start_time  # UTC datetime from Betfair
            minutes_to_kickoff = (kickoff - datetime.now(timezone.utc)).total_seconds() / 60
            if not (0 <= minutes_to_kickoff <= 90):
                continue

            if runners & EXCLUDED_TEAMS_SET:
                continue
                
            try:
                market_book = trading.betting.list_market_book(
                    market_ids=[market.market_id],
                    price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
                )[0]
            except Exception:
                continue 
            
            for runner in market_book.runners:
                runner_name = next((r.runner_name for r in market.runners if r.selection_id == runner.selection_id), "Unknown")
                if runner_name == "The Draw":
                    continue

                if runner.ex.available_to_back:
                    best_back_price = runner.ex.available_to_back[0].price
                    
                    if MIN_ODDS <= best_back_price <= MAX_ODDS:
                        unique_id = f"{market.market_id}_{runner.selection_id}"
                        
                        if unique_id not in placed_market_selection_ids:
                            
                            # Log the new bet!
                            new_row = {
                                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "Market_ID": market.market_id,
                                "Selection_ID": runner.selection_id,
                                "League": league_name,
                                "Match": match_name,
                                "Selection": runner_name,
                                "Stake": PAPER_STAKE,
                                "Matched_Odds": best_back_price,
                                "Result": "PENDING",
                                "Profit": 0.00
                            }
                            
                            # Add the row to our dataframe
                            df_ledger = pd.concat([df_ledger, pd.DataFrame([new_row])], ignore_index=True)
                            placed_market_selection_ids.add(unique_id)
                            new_bets_found = True
                            
                            print(f"🟢 [PAPER BET] {match_name} | Back {runner_name} @ {best_back_price} | Stake: £{PAPER_STAKE}")

    if new_bets_found:
        df_ledger.to_csv(CSV_FILE, index=False)

    print("💤 Routine complete. Sleeping for 5 minutes...\n")
    time.sleep(300)