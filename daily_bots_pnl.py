import os
import glob
import pandas as pd

def check_portfolio_pnl():
    # Find all CSV files that have 'ledger' in the name, anchored to the script's folder
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_files = glob.glob(os.path.join(_script_dir, '*ledger*.csv'))
    
    if not csv_files:
        print("❌ No ledger CSV files found in this directory.")
        return

    rows = []

    for file in csv_files:
        try:
            df = pd.read_csv(file)

            # Lowercase column names to make matching foolproof
            df.columns = [str(col).lower().strip() for col in df.columns]

            # Dynamically hunt for the Profit and Stake columns
            # locked_profit  → LTH bot (lay + hedge strategy)
            # profit         → all standard bots and BTTS FB
            profit_col = next((col for col in df.columns if col in ['locked_profit', 'profit/loss', 'pnl', 'profit', 'pl']), None)
            # lay_stake / back_stake → LTH and BTTS FB bots respectively
            stake_col = next((col for col in df.columns if col in ['lay_stake', 'back_stake', 'stake', 'paper_stake', 'staked', 'liability']), None)

            if not profit_col or not stake_col:
                print(f"⚠️ Skipping {file}: Couldn't find 'Profit' or 'Stake' columns.")
                continue

            # Clean up the data (Strips out R$ signs, commas, and converts to pure math numbers)
            df[profit_col] = pd.to_numeric(df[profit_col].astype(str).str.replace(r'[R\$£€, ]', '', regex=True), errors='coerce').fillna(0)
            df[stake_col] = pd.to_numeric(df[stake_col].astype(str).str.replace(r'[R\$£€, ]', '', regex=True), errors='coerce').fillna(0)

            # Calculate strategy-specific metrics
            strat_profit = df[profit_col].sum()
            strat_staked = df[stake_col].sum()
            strat_greens = len(df[df[profit_col] > 0])
            strat_reds = len(df[df[profit_col] < 0])
            strat_yield = (strat_profit / strat_staked * 100) if strat_staked > 0 else 0
            strat_name = os.path.basename(file).replace('paper_trading_ledger_', '').replace('.csv', '')

            rows.append((strat_profit, strat_staked, strat_greens, strat_reds, strat_yield, strat_name))

        except Exception as e:
            print(f"⚠️ Error reading {file}: {e}")

    # Sort by PnL, highest first
    rows.sort(key=lambda r: r[0], reverse=True)

    print(f"\n{'='*70}")
    print(f"📊 PORTFOLIO PNL SUMMARY ({len(rows)} Strategies)")
    print(f"{'='*70}")

    total_staked = 0.0
    total_profit = 0.0
    total_greens = 0
    total_reds = 0

    for strat_profit, strat_staked, strat_greens, strat_reds, strat_yield, strat_name in rows:
        print(f"🔹 {strat_name[:20].ljust(20)} | PnL: {strat_profit:>7.2f} | Staked: {strat_staked:>7.2f} | Yield: {strat_yield:>6.2f}% | (W: {strat_greens} / L: {strat_reds})")
        total_profit += strat_profit
        total_staked += strat_staked
        total_greens += strat_greens
        total_reds += strat_reds

    # Calculate Master Yield
    master_yield = (total_profit / total_staked * 100) if total_staked > 0 else 0

    print(f"{'='*70}")
    print(f"🏆 MASTER PORTFOLIO TOTALS")
    print(f"{'='*70}")
    print(f"💰 Total Profit : {total_profit:+.2f}")
    print(f"💸 Total Staked : {total_staked:.2f}")
    print(f"📈 Master Yield : {master_yield:+.2f}%")
    print(f"✅ Total Greens : {total_greens}")
    print(f"❌ Total Reds   : {total_reds}")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    check_portfolio_pnl()