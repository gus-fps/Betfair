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

PAPER_STAKE       = _config["paper_stake"]
PREMATCH_MIN_ODDS = _config["lth_prematch_min_odds"]   # 1.38 — home team must be favourite
PREMATCH_MAX_ODDS = _config["lth_prematch_max_odds"]   # 2.15
LAY_MIN_ODDS      = _config["lth_lay_min_odds"]        # 2.5  — in-play lay odds range
LAY_MAX_ODDS      = _config["lth_lay_max_odds"]        # 5.09
ALLOWED_LEAGUES   = _config["lth_allowed_leagues"]
EXCLUDED_TEAMS    = _config["lth_excluded_teams"]
EXCLUDED_TEAMS_SET = set(t.lower() for t in EXCLUDED_TEAMS)

# ==========================================
# TIMING NOTES
# ==========================================
# Entry window: in-play, 1st half only (including stoppage time).
# Represented as clock minutes elapsed since the scheduled kickoff.
#   0–52 clock min ≈ 1st half + up to 7 min of stoppage time.
#   The market.status == 'OPEN' check provides an additional safeguard
#   against accidentally entering during the halftime break or 2nd half
#   (Betfair suspends the market at halftime and during goals).
#
# Hedge: 15 minutes after the lay bet is placed, the bot backs the home
# team at the current market price to lock in an equal profit/loss on
# both outcomes, regardless of the final score.
#   hedge_stake = lay_stake * lay_odds / current_back_odds
#   locked_profit = lay_stake - hedge_stake
# A positive locked_profit means odds drifted (home less likely to win).
# A negative locked_profit means odds shortened (a small loss is locked in).
# If no back price is available at the 15-min mark, the bot retries each
# subsequent cycle. If the market closes before the hedge is placed, the
# bet is settled as a standard lay (WIN if home didn't win, LOSS if home won).

HEDGE_MINUTES    = 15
FIRST_HALF_MAX   = 52   # max clock minutes since kickoff for 1st half entry

# ==========================================
# 3. LEDGER INITIALIZATION
# ==========================================
CSV_FILE = os.path.join(_script_dir, "paper_trading_ledger_lth.csv")

LEDGER_COLS = [
    "Timestamp", "League", "Match", "Selection",
    "Lay_Stake", "Lay_Odds", "Prematch_Odds", "Liability",
    "Hedge_Stake", "Hedge_Odds", "Locked_Profit",
    "Result", "Running_Total",
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
print("✅ Logged in successfully. Firing up the Lay Home Team (1st Half) strategy engine...\n")

# ==========================================
# IN-MEMORY STATE: pre-match approved markets
# ==========================================
# Populated each cycle from pre-match scans. Lost on bot restart (safe
# default — in-play markets with no pre-match record are simply skipped).
# key: market_id (str)
# value: {home_selection_id, home_name, prematch_odds, kickoff, match_name, league_name}
prematch_approved = {}

def update_running_total(df):
    settled = df['Locked_Profit'].where(df['Result'] != 'PENDING_HEDGE', 0)
    running = settled.cumsum().round(2)
    df['Running_Total'] = running.where(df['Result'] != 'PENDING_HEDGE')
    return df

# ==========================================
# 4. THE CONTINUOUS EXECUTION ENGINE
# ==========================================
while True:
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] 📡 Scanning markets and checking hedges...")

    try:
        df_ledger = pd.read_csv(CSV_FILE)
    except PermissionError:
        print("⚠️ ERROR: Please close the CSV file in Excel so the bot can read/write to it!")
        time.sleep(10)
        continue

    # Ensure all columns exist for CSVs created before any future updates
    for col in LEDGER_COLS:
        if col not in df_ledger.columns:
            df_ledger[col] = None

    # ---------------------------------------------------------
    # ROUTINE A: HEDGE PENDING BETS / SETTLE CLOSED MARKETS
    # ---------------------------------------------------------
    pending = df_ledger[df_ledger['Result'] == 'PENDING_HEDGE']
    changes_made = False

    for index, row in pending.iterrows():
        market_id    = str(row['Market_ID'])
        selection_id = int(float(row['Selection_ID']))
        lay_stake    = float(row['Lay_Stake'])
        lay_odds     = float(row['Lay_Odds'])

        bet_time       = datetime.strptime(str(row['Timestamp']), '%Y-%m-%d %H:%M:%S')
        minutes_elapsed = (datetime.now() - bet_time).total_seconds() / 60

        try:
            market_book = trading.betting.list_market_book(
                market_ids=[market_id],
                price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
            )[0]

            # Case 1: Market closed before hedge was placed — settle as unhedged lay
            if market_book.status == 'CLOSED':
                for runner in market_book.runners:
                    if runner.selection_id == selection_id:
                        if runner.status == 'WINNER':
                            # Home team won — lay loses
                            loss = round(lay_stake * (lay_odds - 1), 2)
                            df_ledger.at[index, 'Result']        = 'LOSS'
                            df_ledger.at[index, 'Locked_Profit'] = -loss
                            print(f"📉 SETTLED LOSS (unhedged): {row['Match']} (-£{loss})")
                        elif runner.status == 'LOSER':
                            # Home team didn't win — lay wins
                            df_ledger.at[index, 'Result']        = 'WIN'
                            df_ledger.at[index, 'Locked_Profit'] = lay_stake
                            print(f"💰 SETTLED WIN (unhedged): {row['Match']} (+£{lay_stake})")
                        changes_made = True
                        break
                continue

            # Case 2: 15+ minutes elapsed and market is open — place hedge
            if minutes_elapsed >= HEDGE_MINUTES and market_book.status == 'OPEN':
                for runner in market_book.runners:
                    if runner.selection_id == selection_id:
                        if runner.ex.available_to_back:
                            back_price    = runner.ex.available_to_back[0].price
                            hedge_stake   = round(lay_stake * lay_odds / back_price, 2)
                            locked_profit = round(lay_stake - hedge_stake, 2)
                            df_ledger.at[index, 'Hedge_Stake']   = hedge_stake
                            df_ledger.at[index, 'Hedge_Odds']    = back_price
                            df_ledger.at[index, 'Locked_Profit'] = locked_profit
                            df_ledger.at[index, 'Result']        = 'HEDGED'
                            changes_made = True
                            sign = "+" if locked_profit >= 0 else ""
                            print(f"🔒 HEDGED: {row['Match']} | Back @ {back_price} | Locked: {sign}£{locked_profit:.2f}")
                        else:
                            print(f"⚠️ No back price for {row['Match']} — retrying next cycle")
                        break

        except Exception as e:
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
    # ROUTINE B: SCAN ALL MATCH ODDS MARKETS
    # (pre-match → record approval; in-play 1st half → lay entry)
    # ---------------------------------------------------------
    strategy_filter = market_filter(
        event_type_ids=['1'],
        competition_ids=ALLOWED_LEAGUES,
        market_type_codes=['MATCH_ODDS']
    )

    catalogue = trading.betting.list_market_catalogue(
        filter=strategy_filter,
        max_results=200,
        market_projection=['RUNNER_DESCRIPTION', 'COMPETITION', 'EVENT', 'MARKET_START_TIME']
    )

    new_bets_found = False
    markets_to_remove = []   # collect prematch_approved keys to clean up after the loop

    if catalogue:
        for market in catalogue:
            match_name  = market.event.name
            league_name = market.competition.name if market.competition else "Unknown"
            kickoff     = market.market_start_time
            clock_minutes = (datetime.now(timezone.utc) - kickoff).total_seconds() / 60

            # Skip excluded teams (checked against event name "Home v Away")
            if any(excl in match_name.lower() for excl in EXCLUDED_TEAMS_SET):
                continue

            # Identify home team runner from catalogue (sort_priority 1 = home)
            home_cat = min(market.runners, key=lambda r: r.sort_priority)

            try:
                market_book = trading.betting.list_market_book(
                    market_ids=[market.market_id],
                    price_projection=price_projection(price_data=['EX_BEST_OFFERS'])
                )[0]
            except Exception:
                continue

            if not market_book.inplay:
                # ---- PRE-MATCH: record if home team odds are in approval range ----
                if market.market_id in prematch_approved:
                    continue

                minutes_to_kickoff = (kickoff - datetime.now(timezone.utc)).total_seconds() / 60
                if not (0 <= minutes_to_kickoff <= 90):
                    continue

                for runner in market_book.runners:
                    if runner.selection_id == home_cat.selection_id:
                        if runner.ex.available_to_back:
                            home_odds = runner.ex.available_to_back[0].price
                            if PREMATCH_MIN_ODDS <= home_odds <= PREMATCH_MAX_ODDS:
                                prematch_approved[market.market_id] = {
                                    'home_selection_id': home_cat.selection_id,
                                    'home_name':        home_cat.runner_name,
                                    'prematch_odds':    home_odds,
                                    'kickoff':          kickoff,
                                    'match_name':       match_name,
                                    'league_name':      league_name,
                                }
                                print(f"📋 PRE-MATCH APPROVED: {match_name} | Home ({home_cat.runner_name}) @ {home_odds}")
                        break

            else:
                # ---- IN-PLAY: lay if approved, 1st half, odds in range ----
                if market.market_id not in prematch_approved:
                    continue

                # Past the 1st half window — clean up and skip
                if clock_minutes > FIRST_HALF_MAX:
                    markets_to_remove.append(market.market_id)
                    continue

                if clock_minutes < 0:
                    continue

                # Market must be active (not suspended during goals/halftime)
                if market_book.status != 'OPEN':
                    continue

                info = prematch_approved[market.market_id]
                unique_id = f"{float(market.market_id)}_{info['home_selection_id']}"
                if unique_id in placed_market_ids:
                    continue

                for runner in market_book.runners:
                    if runner.selection_id == info['home_selection_id']:
                        if runner.ex.available_to_lay:
                            lay_price = runner.ex.available_to_lay[0].price
                            if LAY_MIN_ODDS <= lay_price <= LAY_MAX_ODDS:
                                liability = round(PAPER_STAKE * (lay_price - 1), 2)
                                new_row = {
                                    "Timestamp":    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    "League":       info['league_name'],
                                    "Match":        info['match_name'],
                                    "Selection":    f"Lay {info['home_name']}",
                                    "Lay_Stake":    PAPER_STAKE,
                                    "Lay_Odds":     lay_price,
                                    "Prematch_Odds": info['prematch_odds'],
                                    "Liability":    liability,
                                    "Hedge_Stake":  None,
                                    "Hedge_Odds":   None,
                                    "Locked_Profit": None,
                                    "Result":       "PENDING_HEDGE",
                                    "Running_Total": None,
                                    "Market_ID":    market.market_id,
                                    "Selection_ID": info['home_selection_id'],
                                }
                                df_ledger = pd.concat([df_ledger, pd.DataFrame([new_row])], ignore_index=True)
                                placed_market_ids.add(unique_id)
                                new_bets_found = True
                                game_min_est = round(clock_minutes)
                                print(f"🔴 [PAPER LAY] {info['match_name']} | Lay {info['home_name']} @ {lay_price} | ~{game_min_est}' | Liability: £{liability} | Pre-match: {info['prematch_odds']}")
                        break

    # Clean up approved markets that have passed the 1st half window
    for mid in markets_to_remove:
        prematch_approved.pop(mid, None)

    if new_bets_found:
        df_ledger = update_running_total(df_ledger)
        df_ledger.to_csv(CSV_FILE, index=False, columns=LEDGER_COLS)

    print("💤 Routine complete. Sleeping for 5 minutes...\n")
    time.sleep(300)
