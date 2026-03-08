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
MIN_ODDS        = _config["o15f_min_odds"]
MAX_ODDS        = _config["o15f_max_odds"]
ALLOWED_LEAGUES = _config["o15f_allowed_leagues"]
EXCLUDED_TEAMS  = _config["o15f_excluded_teams"]
EXCLUDED_TEAMS_SET = set(t.lower() for t in EXCLUDED_TEAMS)

# ==========================================
# TIMING & SCORE DETECTION NOTES
# ==========================================
# Betfair's REST API does not expose the live score or exact game minute.
# We approximate both using these methods:
#
# GAME TIME: Betfair provides the scheduled kickoff (market_start_time in UTC).
#   Clock time since kickoff = now - market_start_time.
#   Subtracting ~15 min for halftime gives an approximate game minute:
#     70 game min ≈ 70 + 15 = 85 clock min since kickoff
#     75 game min ≈ 75 + 15 = 90 clock min since kickoff
#   A ±3 min buffer is added to account for late kickoffs and stoppage time.
#
# SCORE (0-1 or 1-0): We verify exactly 1 goal has been scored indirectly:
#   1. "Under 1.5 Goals" runner status == 'ACTIVE' → confirms ≤1 goal total
#      (if 2+ goals were scored, this runner would be LOSER and market settled)
#   2. Odds on "Over 1.5 Goals" in range 1.61–2.20 → at 70+ min with 0 goals
#      scored, odds would typically be ~3.5–6.0+. Odds in this range strongly
#      imply exactly 1 goal, matching the 0-1 or 1-0 score requirement.
#
# This indirect approach avoids external score APIs while remaining reliable.

CLOCK_WINDOW_MIN = 83   # clock min since kickoff ≈ game minute 68
CLOCK_WINDOW_MAX = 93   # clock min since kickoff ≈ game minute 78

# ==========================================
# 3. LEDGER INITIALIZATION
# ==========================================
CSV_FILE = os.path.join(_script_dir, "paper_trading_ledger_o15f.csv")

if not os.path.exists(CSV_FILE):
    df_initial = pd.DataFrame(columns=[
        "Timestamp", "League", "Match", "Selection", "Stake",
        "Matched_Odds", "Kickoff_Odds", "Delta", "Result", "Profit", "Running_Total",
        "Market_ID", "Selection_ID"
    ])
    df_initial.to_csv(CSV_FILE, index=False)

trading = betfairlightweight.APIClient(username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS)
try:
    trading.login()
except Exception as e:
    print(f"Login failed: {e}")
    raise SystemExit(1)
print("✅ Logged in successfully. Firing up the O1.5 Final strategy engine...\n")

def update_running_total(df):
    df['Delta'] = (df['Matched_Odds'] - df['Kickoff_Odds']).round(2)
    settled_profits = df['Profit'].where(df['Result'] != 'PENDING', 0)
    running = settled_profits.cumsum().round(2)
    df['Running_Total'] = running.where(df['Result'] != 'PENDING')
    return df

# ==========================================
# 4. THE CONTINUOUS EXECUTION ENGINE
# ==========================================
while True:
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] 📡 Scanning in-play markets...")

    try:
        df_ledger = pd.read_csv(CSV_FILE)
    except PermissionError:
        print("⚠️ ERROR: Please close the CSV file in Excel so the bot can read/write to it!")
        time.sleep(10)
        continue

    # Ensure new columns exist for CSVs created before this update
    if 'Kickoff_Odds' not in df_ledger.columns:
        df_ledger['Kickoff_Odds'] = None
    if 'Delta' not in df_ledger.columns:
        df_ledger['Delta'] = None
    if 'Running_Total' not in df_ledger.columns:
        df_ledger['Running_Total'] = None

    # ---------------------------------------------------------
    # ROUTINE A: SETTLE PENDING BETS
    # ---------------------------------------------------------
    pending_bets = df_ledger[df_ledger['Result'] == 'PENDING']

    for index, row in pending_bets.iterrows():
        market_id = str(row['Market_ID'])
        selection_id = int(float(row['Selection_ID']))
        stake = float(row['Stake'])
        odds = float(row['Matched_Odds'])

        try:
            market_book = trading.betting.list_market_book(
                market_ids=[market_id],
                price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
            )[0]

            if market_book.status == 'CLOSED':
                for runner in market_book.runners:
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
            print(f"⚠️ Could not check market {market_id}: {e}")

    df_ledger = update_running_total(df_ledger)
    df_ledger.to_csv(CSV_FILE, index=False, columns=["Timestamp", "League", "Match", "Selection", "Stake", "Matched_Odds", "Kickoff_Odds", "Delta", "Result", "Profit", "Running_Total", "Market_ID", "Selection_ID"])

    # Build deduplication set
    placed_market_selection_ids = set(
        df_ledger['Market_ID'].astype(float).astype(str) + "_" + df_ledger['Selection_ID'].apply(lambda x: str(int(float(x))))
    )

    # ---------------------------------------------------------
    # ROUTINE B: FIND NEW BETS (in-play, ~70-75 game minutes)
    # ---------------------------------------------------------
    strategy_filter = market_filter(
        event_type_ids=['1'],
        competition_ids=ALLOWED_LEAGUES,
        market_type_codes=['OVER_UNDER_15']
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

            # Estimate game minute from clock time since scheduled kickoff
            kickoff = market.market_start_time  # UTC datetime from Betfair
            clock_minutes = (datetime.now(timezone.utc) - kickoff).total_seconds() / 60

            if not (CLOCK_WINDOW_MIN <= clock_minutes <= CLOCK_WINDOW_MAX):
                continue

            if any(excl in match_name.lower() for excl in EXCLUDED_TEAMS_SET):
                continue

            try:
                market_book = trading.betting.list_market_book(
                    market_ids=[market.market_id],
                    price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
                )[0]
            except Exception:
                continue

            # Must be in-play and market still open
            if not market_book.inplay or market_book.status != 'OPEN':
                continue

            over_runner = None
            under_runner = None

            for runner in market_book.runners:
                runner_name = next(
                    (r.runner_name for r in market.runners if r.selection_id == runner.selection_id),
                    "Unknown"
                )
                if runner_name == "Over 1.5 Goals":
                    over_runner = runner
                elif runner_name == "Under 1.5 Goals":
                    under_runner = runner

            # Under 1.5 must be ACTIVE: confirms at most 1 goal scored so far.
            # If 2+ goals had been scored this runner would be LOSER and market closed.
            if under_runner is None or under_runner.status != 'ACTIVE':
                continue

            if over_runner is None or not over_runner.ex.available_to_back:
                continue

            best_back_price = over_runner.ex.available_to_back[0].price

            # Odds in range 1.61–2.20 at this stage strongly implies exactly 1 goal
            # (0-goal games at 70+ min would price Over 1.5 at ~3.5–6.0+)
            if not (MIN_ODDS <= best_back_price <= MAX_ODDS):
                continue

            unique_id = f"{float(market.market_id)}_{over_runner.selection_id}"
            if unique_id in placed_market_selection_ids:
                continue

            game_min_est = round(clock_minutes - 15)
            new_row = {
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Market_ID": market.market_id,
                "Selection_ID": over_runner.selection_id,
                "League": league_name,
                "Match": match_name,
                "Selection": "Over 1.5 Goals",
                "Stake": PAPER_STAKE,
                "Matched_Odds": best_back_price,
                "Kickoff_Odds": None,
                "Result": "PENDING",
                "Profit": 0.00
            }

            df_ledger = pd.concat([df_ledger, pd.DataFrame([new_row])], ignore_index=True)
            placed_market_selection_ids.add(unique_id)
            new_bets_found = True

            print(f"🟢 [PAPER BET] {match_name} | Over 1.5 Goals @ {best_back_price} | ⏱ ~{game_min_est}' (est)")

    if new_bets_found:
        df_ledger = update_running_total(df_ledger)
        df_ledger.to_csv(CSV_FILE, index=False, columns=["Timestamp", "League", "Match", "Selection", "Stake", "Matched_Odds", "Kickoff_Odds", "Delta", "Result", "Profit", "Running_Total", "Market_ID", "Selection_ID"])

    # Adaptive sleep: only poll every minute when matches are near the entry window.
    # Otherwise fall back to 5-minute cycles to keep API calls low.
    # Window check uses the same catalogue already fetched above (no extra API call).
    near_window = any(
        68 <= (datetime.now(timezone.utc) - m.market_start_time).total_seconds() / 60 <= 98
        for m in (catalogue or [])
    )
    if near_window:
        print("💤 Matches near window. Sleeping for 1 minute...\n")
        time.sleep(60)
    else:
        print("💤 No matches near window. Sleeping for 5 minutes...\n")
        time.sleep(300)
