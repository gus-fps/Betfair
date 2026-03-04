# Betfair Automated Betting Bot

A Python-based automated sports betting system that connects to the Betfair Exchange API to scan soccer markets, apply data-driven filtering strategies, and track results via paper trading.

## What It Does

This project implements a multi-criteria betting strategy pipeline:

1. **Market Scanning** - Connects to Betfair's API and pulls live soccer match odds across configured leagues
2. **Strategy Filtering** - Filters matches by allowed leagues, excluded teams (from backtesting), odds range, and time-to-kickoff
3. **Paper Trading** - Logs simulated bets to a CSV ledger with automatic settlement tracking (WIN/LOSS/PENDING)
4. **Data Export** - Utility scripts to extract leagues, teams, and competition IDs from Betfair for strategy research

## Scripts

| Script | Purpose |
|--------|---------|
| `ghost_bot_BTTS_v2.py` | Main bot - continuous loop that scans markets, places paper bets, and auto-settles results |
| `ghost_bot_BTTS.py` | Earlier version - single-pass scan with the same filtering logic (no settlement) |
| `find_matches.py` | Quick scan of all live/upcoming soccer events on Betfair |
| `list_competitions.py` | Exports all active soccer league IDs and names to CSV |
| `export_betfair_ids.py` | Exports leagues and teams to separate CSV files |
| `export_betfair_ids_comp+team.py` | Enhanced export mapping each team to its league |
| `team_sniper.py` | Searches Betfair for specific teams across all markets |
| `betfair_api_call_test.py` | Minimal connection test to verify API credentials work |
| `data_pull.py` | Pulls historical Premier League match data from football-data.co.uk |
| `visualize_odds.py` | Generates a bar chart of match outcome distributions |

## Setup

### Prerequisites

- Python 3.8+
- A [Betfair Developer](https://developer.betfair.com/) account with API access
- SSL certificates for non-interactive login ([guide](https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Non-Interactive+%28bot%29+login))

### Installation

```bash
pip install betfairlightweight python-dotenv pandas matplotlib
```

### Configuration

1. Copy the example environment file and fill in your credentials:
   ```bash
   cp .env.example Betfair.env
   ```

2. Place your Betfair SSL certificates in a `certs/` folder:
   ```
   certs/
   ├── client-2048.crt
   └── client-2048.key
   ```

3. Test your connection:
   ```bash
   python betfair_api_call_test.py
   ```

### Running the Bot

```bash
python ghost_bot_BTTS_v2.py
```

The bot will scan every 5 minutes, log paper bets to `paper_trading_ledger.csv`, and auto-settle them when markets close.

## Strategy Configuration

Edit the constants at the top of `ghost_bot_BTTS_v2.py`:

- **`ALLOWED_LEAGUES`** - Betfair competition IDs to monitor (use `list_competitions.py` to find IDs)
- **`EXCLUDED_TEAMS`** - Teams to skip based on backtesting (use `team_sniper.py` to verify names)
- **`MIN_ODDS` / `MAX_ODDS`** - Back price range (default: 1.81 - 2.60)
- **`PAPER_STAKE`** - Simulated bet amount per selection

## Data Files

| File | Description |
|------|-------------|
| `paper_trading_ledger.csv` | Auto-generated log of all paper bets and their outcomes |
| `BTTS_competitions.csv` | League IDs for the BTTS strategy |
| `competitions.csv` | Full list of Betfair soccer competitions |
| `betfair_leagues.csv` | Exported league names and IDs |
| `betfair_teams.csv` | Exported team names and IDs |

## Security

Credentials are loaded from a `Betfair.env` file that is excluded from version control via `.gitignore`. See `.env.example` for the required format. Never commit credentials or certificates to git.
