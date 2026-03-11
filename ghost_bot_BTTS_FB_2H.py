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
MIN_ODDS        = _config["btts_fb_min_odds"]    # 8.20
MAX_ODDS        = _config["btts_fb_max_odds"]    # 11.00
ALLOWED_LEAGUES = _config["btts_fb_allowed_leagues"]
EXCLUDED_TEAMS  = _config["btts_fb_excluded_teams"]
EXCLUDED_TEAMS_SET = set(t.lower() for t in EXCLUDED_TEAMS)

# ==========================================
# TIMING & STRATEGY NOTES
# ==========================================
# Entry window: in-play, 2nd half, game minutes 55–70.
# Betfair's API has no live clock, so we estimate from clock time since kickoff.
# The halftime break adds ~15 minutes of clock time that is not game time:
#   55 game min ≈ 55 + 15 = 70 clock min since kickoff
#   70 game min ≈ 70 + 15 = 85 clock min since kickoff
#
# SCORE DETECTION (0-0 at entry):
# BTTS Yes odds of 8.2–11 at 55–70 game minutes strongly imply a 0-0 score.
# If one team had already scored (e.g., 1-0 at min 55), BTTS Yes would
# be much shorter (~2.5–4.5) since only one more goal is needed.
# If it were already 1-1, the market would be settled (BTTS Yes = WINNER).
# So the odds range filter acts as an implicit 0-0 score detector.
#
# FREEBET EXIT:
# Once a goal is scored in a previously 0-0 game, BTTS Yes odds DROP
# sharply (only one more goal needed). If the new lay odds (L) are below
# the original back odds (B), we "freebet out":
#   freebet_stake = back_stake * (back_odds - 1) / (lay_odds - 1)
# This creates a position where:
#   - If BTTS Yes WINS (both teams score): back wins, lay loses → net = 0 (break even)
#   - If BTTS Yes LOSES (not both score): lay wins, back loses → net profit
#     = back_stake * (back_odds - lay_odds) / (lay_odds - 1)
# The freebet is only placed when lay odds < back odds (odds shortened
# after the goal), guaranteeing that the worst case is break-even.
# If lay_odds >= back_odds (no goal, odds drifting further), we hold.

CLOCK_ENTRY_MIN = 70    # ≈ game minute 55
CLOCK_ENTRY_MAX = 85    # ≈ game minute 70

# ==========================================
# 3. LEDGER INITIALIZATION
# ==========================================
CSV_FILE = os.path.join(_script_dir, "paper_trading_ledger_btts_fb.csv")

LEDGER_COLS = [
    "Timestamp", "League", "Match", "Selection",
    "Back_Stake", "Back_Odds",
    "Freebet_Stake", "Freebet_Odds", "Freebet_Profit",
    "Profit", "Result", "Running_Total",
    "Market_ID", "Selection_ID"
]

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=LEDGER_COLS).to_csv(CSV_FILE, index=False)

trading = betfairlightweight.APIClient(username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS)
try:
    trading.login()
except Exception as e:
    print(f"Login failed: {e}")
    raise SystemExit(1)
print("✅ Logged in successfully. Firing up the BTTS Freebet 2H strategy engine...\n")

def update_running_total(df):
    unsettled = df['Result'].isin(['PENDING_FREEBET', 'FREEBET_PLACED'])
    settled_profit = df['Profit'].where(~unsettled, 0)
    running = settled_profit.cumsum().round(2)
    df['Running_Total'] = running.where(~unsettled)
    return df

# ==========================================
# SESSION MANAGEMENT
# ==========================================
last_keepalive = datetime.now(timezone.utc)

def refresh_session():
    """Keep Betfair session alive. Tries keep_alive() first; falls back to full re-login."""
    try:
        trading.keep_alive()
        print("🔄 Session refreshed (keep-alive).")
    except Exception:
        print("⚠️ Keep-alive failed — attempting full re-login...")
        try:
            trading.login()
            print("✅ Re-login successful.")
        except Exception as login_err:
            print(f"❌ Re-login failed: {login_err}")

# ==========================================
# 4. THE CONTINUOUS EXECUTION ENGINE
# ==========================================
while True:
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] 📡 Scanning markets and checking freebet exits...")

    # Keep session alive — ping Betfair every 2 hours to prevent token expiry
    if (datetime.now(timezone.utc) - last_keepalive).total_seconds() > 7200:
        refresh_session()
        last_keepalive = datetime.now(timezone.utc)

    try:
        df_ledger = pd.read_csv(CSV_FILE)
    except PermissionError:
        print("⚠️ ERROR: Please close the CSV file in Excel so the bot can read/write to it!")
        time.sleep(10)
        continue

    # Ensure all columns exist
    for col in LEDGER_COLS:
        if col not in df_ledger.columns:
            df_ledger[col] = None

    changes_made = False

    # ---------------------------------------------------------
    # ROUTINE A: FREEBET EXIT + SETTLEMENT
    # ---------------------------------------------------------

    # --- A1: PENDING_FREEBET → check for goal (lay odds < back odds) or settlement ---
    pending_freebet = df_ledger[df_ledger['Result'] == 'PENDING_FREEBET']

    for index, row in pending_freebet.iterrows():
        market_id    = str(row['Market_ID'])
        selection_id = int(float(row['Selection_ID']))
        back_stake   = float(row['Back_Stake'])
        back_odds    = float(row['Back_Odds'])

        try:
            market_book = trading.betting.list_market_book(
                market_ids=[market_id],
                price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
            )[0]

            # Market closed before freebet was placed
            if market_book.status == 'CLOSED':
                for runner in market_book.runners:
                    if runner.selection_id == selection_id:
                        if runner.status == 'WINNER':
                            # Both teams scored — back bet wins (rare unhedged win)
                            profit = round(back_stake * (back_odds - 1), 2)
                            df_ledger.at[index, 'Result'] = 'WIN_UNHEDGED'
                            df_ledger.at[index, 'Profit'] = profit
                            print(f"💰 WIN (unhedged): {row['Match']} (+£{profit})")
                        elif runner.status == 'LOSER':
                            # No both-team score — back bet loses
                            df_ledger.at[index, 'Result'] = 'LOSS'
                            df_ledger.at[index, 'Profit'] = -back_stake
                            print(f"📉 LOSS (no freebet placed): {row['Match']} (-£{back_stake})")
                        changes_made = True
                        break
                continue

            # Market still open — check for goal trigger: lay odds < back odds
            for runner in market_book.runners:
                if runner.selection_id == selection_id:
                    if runner.ex.available_to_lay:
                        lay_odds = runner.ex.available_to_lay[0].price
                        if lay_odds < back_odds:
                            # Goal scored — freebet condition met
                            freebet_stake  = round(back_stake * (back_odds - 1) / (lay_odds - 1), 2)
                            freebet_profit = round(back_stake * (back_odds - lay_odds) / (lay_odds - 1), 2)
                            df_ledger.at[index, 'Freebet_Stake']  = freebet_stake
                            df_ledger.at[index, 'Freebet_Odds']   = lay_odds
                            df_ledger.at[index, 'Freebet_Profit'] = freebet_profit
                            df_ledger.at[index, 'Result']         = 'FREEBET_PLACED'
                            changes_made = True
                            print(f"🔓 FREEBET OUT: {row['Match']} | Lay Yes @ {lay_odds} | "
                                  f"Stake: £{freebet_stake} | Locked if BTTS fails: +£{freebet_profit}")
                    break

        except Exception as e:
            if 'INVALID_SESSION_INFORMATION' in str(e):
                print("⚠️ Session expired — re-logging in...")
                refresh_session()
                last_keepalive = datetime.now(timezone.utc)
            else:
                print(f"⚠️ Error checking market {market_id}: {e}")

    # --- A2: FREEBET_PLACED → wait for final settlement ---
    freebet_placed = df_ledger[df_ledger['Result'] == 'FREEBET_PLACED']

    for index, row in freebet_placed.iterrows():
        market_id    = str(row['Market_ID'])
        selection_id = int(float(row['Selection_ID']))
        back_stake   = float(row['Back_Stake'])
        freebet_profit = float(row['Freebet_Profit'])

        try:
            market_book = trading.betting.list_market_book(
                market_ids=[market_id],
                price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
            )[0]

            if market_book.status == 'CLOSED':
                for runner in market_book.runners:
                    if runner.selection_id == selection_id:
                        if runner.status == 'WINNER':
                            # Both teams scored — back wins, lay loses → net = 0
                            df_ledger.at[index, 'Result'] = 'BREAK_EVEN'
                            df_ledger.at[index, 'Profit'] = 0.00
                            print(f"🟰 BREAK EVEN: {row['Match']} (BTTS won, freebet covered)")
                        elif runner.status == 'LOSER':
                            # Not both scored — lay wins, back loses → locked profit
                            df_ledger.at[index, 'Result'] = 'WIN'
                            df_ledger.at[index, 'Profit'] = freebet_profit
                            print(f"💰 WIN (freebet): {row['Match']} (+£{freebet_profit})")
                        changes_made = True
                        break
        except Exception as e:
            if 'INVALID_SESSION_INFORMATION' in str(e):
                print("⚠️ Session expired — re-logging in...")
                refresh_session()
                last_keepalive = datetime.now(timezone.utc)
            else:
                print(f"⚠️ Error checking market {market_id}: {e}")

    if changes_made:
        df_ledger = update_running_total(df_ledger)
        df_ledger.to_csv(CSV_FILE, index=False, columns=LEDGER_COLS)

    # Build deduplication set
    placed_market_ids = set(
        df_ledger['Market_ID'].astype(float).astype(str) + "_" +
        df_ledger['Selection_ID'].apply(lambda x: str(int(float(x))))
    )

    # ---------------------------------------------------------
    # ROUTINE B: FIND NEW BETS (in-play, 2nd half, 55–70 game min)
    # ---------------------------------------------------------
    strategy_filter = market_filter(
        event_type_ids=['1'],
        competition_ids=ALLOWED_LEAGUES,
        market_type_codes=['BOTH_TEAMS_TO_SCORE']
    )

    try:
        catalogue = trading.betting.list_market_catalogue(
            filter=strategy_filter,
            max_results=200,
            market_projection=['RUNNER_DESCRIPTION', 'COMPETITION', 'EVENT', 'MARKET_START_TIME']
        )
    except Exception as e:
        if 'INVALID_SESSION_INFORMATION' in str(e):
            print("⚠️ Session expired — re-logging in...")
            refresh_session()
            last_keepalive = datetime.now(timezone.utc)
        else:
            print(f"⚠️ Could not fetch market catalogue: {e}")
        print("💤 Routine complete. Sleeping for 5 minutes...\n")
        time.sleep(300)
        continue

    new_bets_found = False

    if catalogue:
        for market in catalogue:
            match_name  = market.event.name
            league_name = market.competition.name if market.competition else "Unknown"
            kickoff     = market.market_start_time
            clock_minutes = (datetime.now(timezone.utc) - kickoff).total_seconds() / 60

            if not (CLOCK_ENTRY_MIN <= clock_minutes <= CLOCK_ENTRY_MAX):
                continue

            if any(excl in match_name.lower() for excl in EXCLUDED_TEAMS_SET):
                continue

            try:
                market_book = trading.betting.list_market_book(
                    market_ids=[market.market_id],
                    price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
                )[0]
            except Exception as e:
                if 'INVALID_SESSION_INFORMATION' in str(e):
                    refresh_session()
                    last_keepalive = datetime.now(timezone.utc)
                continue

            if not market_book.inplay or market_book.status != 'OPEN':
                continue

            for runner in market_book.runners:
                runner_name = next(
                    (r.runner_name for r in market.runners if r.selection_id == runner.selection_id),
                    "Unknown"
                )
                if runner_name != "Yes":
                    continue

                if runner.ex.available_to_back:
                    best_back_price = runner.ex.available_to_back[0].price

                    if MIN_ODDS <= best_back_price <= MAX_ODDS:
                        unique_id = f"{float(market.market_id)}_{runner.selection_id}"

                        if unique_id not in placed_market_ids:
                            game_min_est = round(clock_minutes - 15)
                            new_row = {
                                "Timestamp":      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "League":         league_name,
                                "Match":          match_name,
                                "Selection":      "BTTS Yes",
                                "Back_Stake":     PAPER_STAKE,
                                "Back_Odds":      best_back_price,
                                "Freebet_Stake":  None,
                                "Freebet_Odds":   None,
                                "Freebet_Profit": None,
                                "Profit":         0.00,
                                "Result":         "PENDING_FREEBET",
                                "Running_Total":  None,
                                "Market_ID":      market.market_id,
                                "Selection_ID":   runner.selection_id,
                            }
                            df_ledger = pd.concat([df_ledger, pd.DataFrame([new_row])], ignore_index=True)
                            placed_market_ids.add(unique_id)
                            new_bets_found = True
                            print(f"🟢 [PAPER BET] {match_name} | Back BTTS Yes @ {best_back_price} "
                                  f"| ~{game_min_est}' | Stake: £{PAPER_STAKE}")
                break

    if new_bets_found:
        df_ledger = update_running_total(df_ledger)
        df_ledger.to_csv(CSV_FILE, index=False, columns=LEDGER_COLS)

    print("💤 Routine complete. Sleeping for 5 minutes...\n")
    time.sleep(300)
