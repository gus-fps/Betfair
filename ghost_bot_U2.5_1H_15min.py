import betfairlightweight
from betfairlightweight.filters import market_filter, price_projection
import pandas as pd
import os
import json
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
# 2. STRATEGY CONFIGURATION (loaded from strategy_config.json)
# ==========================================
# See strategy_config.example.json for the expected format.
# Your real strategy_config.json is gitignored to keep your edge private.
with open(os.path.join(_script_dir, "strategy_config.json")) as f:
    _config = json.load(f)

PAPER_STAKE     = _config["paper_stake"]
MIN_ODDS        = _config["u25_1h_min_odds"]
MAX_ODDS        = _config["u25_1h_max_odds"]
ALLOWED_LEAGUES = _config["u25_1h_allowed_leagues"]
EXCLUDED_TEAMS  = _config["u25_1h_excluded_teams"]
EXCLUDED_TEAMS_SET = set(t.lower() for t in EXCLUDED_TEAMS)

# ==========================================
# 3. LEDGER INITIALIZATION
# ==========================================
CSV_FILE = os.path.join(_script_dir, "paper_trading_ledger_u25_1h.csv")

# Note: this ledger has an extra "Kickoff" column so we can calculate
# when 15 minutes have elapsed in-play and trigger the hedge.
if not os.path.exists(CSV_FILE):
    df_initial = pd.DataFrame(columns=[
        "Timestamp", "Market_ID", "Selection_ID", "League", "Match",
        "Selection", "Stake", "Matched_Odds", "Kickoff", "Kickoff_Odds", "Result", "Profit", "Running_Total"
    ])
    df_initial.to_csv(CSV_FILE, index=False)

trading = betfairlightweight.APIClient(username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS)
try:
    trading.login()
except Exception as e:
    print(f"Login failed: {e}")
    raise SystemExit(1)
print("✅ Logged in successfully. Firing up the strategy engine...\n")

def update_running_total(df):
    settled_profits = df['Profit'].where(df['Result'] != 'PENDING', 0)
    running = settled_profits.cumsum().round(2)
    df['Running_Total'] = running.where(df['Result'] != 'PENDING')
    return df

# ==========================================
# 4. THE CONTINUOUS EXECUTION ENGINE
# ==========================================
while True:
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] 📡 Scanning markets and checking hedges...")

    # Load the current ledger into Pandas
    try:
        df_ledger = pd.read_csv(CSV_FILE)
    except PermissionError:
        print("⚠️ ERROR: Please close the CSV file in Excel so the bot can read/write to it!")
        time.sleep(10)
        continue

    # Ensure new columns exist for CSVs created before this update
    if 'Kickoff_Odds' not in df_ledger.columns:
        df_ledger['Kickoff_Odds'] = None
    if 'Running_Total' not in df_ledger.columns:
        df_ledger['Running_Total'] = None

    # ---------------------------------------------------------
    # ROUTINE A: HEDGE PENDING BETS
    # Unlike other bots, we don't wait for the market to close.
    # At 15 min in-play we lay "Under 2.5" to lock equal profit
    # on both outcomes. The formula is:
    #   hedge_lay_stake = back_stake * back_odds / current_lay_odds
    #   locked_profit   = back_stake * (back_odds - lay_odds) / lay_odds
    # ---------------------------------------------------------
    pending_bets = df_ledger[df_ledger['Result'] == 'PENDING']

    for index, row in pending_bets.iterrows():
        market_id = str(row['Market_ID'])
        selection_id = int(float(row['Selection_ID']))
        stake = float(row['Stake'])
        back_odds = float(row['Matched_Odds'])

        # Calculate how many minutes have passed since kickoff
        kickoff = datetime.fromisoformat(str(row['Kickoff'])).replace(tzinfo=timezone.utc)
        minutes_elapsed = (datetime.now(timezone.utc) - kickoff).total_seconds() / 60

        try:
            market_book = trading.betting.list_market_book(
                market_ids=[market_id],
                price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
            )[0]

            if market_book.status == 'CLOSED':
                # Fallback: bot was down at the 15-min mark, settle the back bet normally
                for runner in market_book.runners:
                    if runner.selection_id == selection_id:
                        if runner.status == 'WINNER':
                            df_ledger.at[index, 'Result'] = 'WIN'
                            df_ledger.at[index, 'Profit'] = round(stake * (back_odds - 1), 2)
                            print(f"💰 SETTLED WIN (unhedged): {row['Match']} (+£{df_ledger.at[index, 'Profit']})")
                        elif runner.status == 'LOSER':
                            df_ledger.at[index, 'Result'] = 'LOSS'
                            df_ledger.at[index, 'Profit'] = -stake
                            print(f"📉 SETTLED LOSS (unhedged): {row['Match']} (-£{stake})")

            else:
                # Capture kickoff odds on the first cycle we see the market go in-play
                if market_book.inplay and pd.isna(df_ledger.at[index, 'Kickoff_Odds']):
                    for runner in market_book.runners:
                        if runner.selection_id == selection_id:
                            try:
                                if runner.ex.available_to_back:
                                    df_ledger.at[index, 'Kickoff_Odds'] = runner.ex.available_to_back[0].price
                            except Exception:
                                pass

                if market_book.inplay and minutes_elapsed >= 15:
                    # Time to hedge — find the current lay price for our selection
                    for runner in market_book.runners:
                        if runner.selection_id == selection_id:
                            if runner.ex.available_to_lay:
                                lay_odds = runner.ex.available_to_lay[0].price
                            elif runner.last_price_traded:
                                # No lay offers in the queue, use last traded as estimate
                                lay_odds = runner.last_price_traded
                            else:
                                # Can't hedge this cycle, will retry in 5 min
                                print(f"⚠️ No lay price available for {row['Match']}, will retry...")
                                break

                            # Hedge formula: lock equal profit on both outcomes
                            hedge_stake = round(stake * back_odds / lay_odds, 2)
                            locked_profit = round(stake * (back_odds - lay_odds) / lay_odds, 2)

                            df_ledger.at[index, 'Result'] = 'HEDGED'
                            df_ledger.at[index, 'Profit'] = locked_profit

                            direction = "+" if locked_profit >= 0 else ""
                            print(f"🔒 HEDGED: {row['Match']} | Backed @ {back_odds} → Lay @ {lay_odds} | Hedge Stake: £{hedge_stake} | Locked P&L: {direction}£{locked_profit}")

        except Exception as e:
            print(f"⚠️ Could not check market {market_id}: {e}")

    # Save the updated hedges back to the CSV
    df_ledger = update_running_total(df_ledger)
    df_ledger.to_csv(CSV_FILE, index=False)

    # Build deduplication set — cast Selection_ID to int to avoid "47972.0" vs "47972" mismatches
    placed_market_selection_ids = set(
        df_ledger['Market_ID'].astype(float).astype(str) + "_" + df_ledger['Selection_ID'].apply(lambda x: str(int(float(x))))
    )


    # ---------------------------------------------------------
    # ROUTINE B: FIND NEW BETS (pre-match, within 90 min of kickoff)
    # ---------------------------------------------------------
    strategy_filter = market_filter(
        event_type_ids=['1'],
        competition_ids=ALLOWED_LEAGUES,
        market_type_codes=['FIRST_HALF_GOALS_25']
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

            # Only act within 90 minutes of kick-off
            kickoff = market.market_start_time  # UTC datetime from Betfair
            minutes_to_kickoff = (kickoff - datetime.now(timezone.utc)).total_seconds() / 60
            if not (0 <= minutes_to_kickoff <= 90):
                continue

            if any(excl in runner.lower() or runner.lower() in excl
                   for runner in runners for excl in EXCLUDED_TEAMS_SET):
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
                if runner_name != "Under 2.5 Goals":
                    continue

                if runner.ex.available_to_back:
                    best_back_price = runner.ex.available_to_back[0].price

                    if MIN_ODDS <= best_back_price <= MAX_ODDS:
                        unique_id = f"{float(market.market_id)}_{runner.selection_id}"

                        if unique_id not in placed_market_selection_ids:

                            # Log the new bet — store Kickoff so Routine A knows when to hedge
                            new_row = {
                                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "Market_ID": market.market_id,
                                "Selection_ID": runner.selection_id,
                                "League": league_name,
                                "Match": match_name,
                                "Selection": runner_name,
                                "Stake": PAPER_STAKE,
                                "Matched_Odds": best_back_price,
                                "Kickoff": kickoff.strftime('%Y-%m-%d %H:%M:%S'),
                                "Kickoff_Odds": None,
                                "Result": "PENDING",
                                "Profit": 0.00
                            }

                            df_ledger = pd.concat([df_ledger, pd.DataFrame([new_row])], ignore_index=True)
                            placed_market_selection_ids.add(unique_id)
                            new_bets_found = True

                            print(f"🟢 [PAPER BET] {match_name} | Back Under 2.5 @ {best_back_price} | Stake: £{PAPER_STAKE} | Hedging at 15 min")

    if new_bets_found:
        df_ledger = update_running_total(df_ledger)
        df_ledger.to_csv(CSV_FILE, index=False)

    print("💤 Routine complete. Sleeping for 5 minutes...\n")
    time.sleep(300)
