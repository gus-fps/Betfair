import betfairlightweight
from betfairlightweight.filters import market_filter
import os
import time
import csv
from dotenv import load_dotenv

# Loads credentials from a .env file in the same folder as this script
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Betfair.env"))

USERNAME = os.environ["BF_USERNAME"]
PASSWORD = os.environ["BF_PASSWORD"]
APP_KEY  = os.environ["BF_APP_KEY"]

# Certs resolved relative to this script's directory, not CWD
_script_dir = os.path.dirname(os.path.abspath(__file__))
MY_CERTS = (
    os.path.join(_script_dir, "certs", "client-2048.crt"),
    os.path.join(_script_dir, "certs", "client-2048.key"),
)

trading = betfairlightweight.APIClient(
    username=USERNAME, password=PASSWORD, app_key=APP_KEY, cert_files=MY_CERTS
)

try:
    trading.login()
except Exception as e:
    print(f"Login failed: {e}")
    raise SystemExit(1)

# ==========================================
# THE SNIPER SEARCH
# ==========================================
# Map each team name to its Betfair competition ID.
# Run list_competitions.py first to discover IDs, then fill them in here.
# Leave as None to fall back to a plain text search (less precise).
search_terms = {
    # --- Spanish (Segunda División / La Liga) ---
    "Burgos":               None,
    "Malaga":               None,
    "Elche":                None,
    "Valladolid":           None,
    "Espanyol":             None,
    "Mallorca":             None,
    "Girona":               None,
    "Granada":              None,
    "Tenerife":             None,
    "Alcorcon":             None,
    "UD Logrones":          None,
    "Leganes":              None,
    "CD Castellon":         None,
    "Andorra CF":           None,
    # --- Italian (Serie A / Serie B) ---
    "Cittadella":           None,
    "Reggina":              None,
    "Empoli":               None,
    "Frosinone":            None,
    "Perugia":              None,
    "Reggiana":             None,
    "Inter":                None,
    "Fiorentina":           None,
    "Lecce":                None,
    "Spezia":               None,
    "Pescara":              None,
    "Pordenone":            None,
    "Carrarese":            None,
    "Juventus":             None,
    # --- Brazilian (Brasileirao / Serie B) ---
    "Sport Recife":         None,
    "Cruzeiro MG":          None,
    "Fortaleza EC":         None,
    "Fluminense":           None,
    "Cuiaba":               None,
    # --- Turkish (Süper Lig) ---
    "Basaksehir":           None,
    "Besiktas":             None,
    "Hatayspor":            None,
    "Galatasaray":          None,
    "Malatyaspor":          None,
    "Fatih Karagumruk":     None,
    # --- South Korean (K League) ---
    "Incheon":              None,
    "Gwangju":              None,
    "Seongnam":             None,
    # --- Uruguayan ---
    "Wanderers (Uru)":      None,
    "Penarol":              None,
    "Cerro Largo":          None,
    "Cerrito":              None,
    "Centro Atletico Fenix": None,
    # --- Portuguese (Primeira Liga / Liga 2) ---
    "Varzim":               None,
    "Santa Clara":          None,
    "Mafra":                None,
    "Arouca":               None,
    "Casa Pia":             None,
    "Os Belenenses":        None,
    "Penafiel":             None,
    # --- French (Ligue 1 / Ligue 2) ---
    "Rennes":               None,
    "Clermont":             None,
    "Ajaccio":              None,
    "Nice":                 None,
    # --- Chinese (CSL) ---
    "Qingdao Jonoon":       None,
    "Guangzhou City":       None,
}

csv_path = os.path.join(_script_dir, "sniper_results.csv")

print("\n🔍 Sniping the global Betfair database...\n")

with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Search Term", "Betfair Event Name"])

    for term, comp_id in search_terms.items():
        print(f"--- Searching for: '{term}' ---")

        filter_kwargs = {"event_type_ids": ["1"], "text_query": term}
        if comp_id:
            filter_kwargs["competition_ids"] = [comp_id]

        target_filter = market_filter(**filter_kwargs)

        try:
            events = trading.betting.list_events(filter=target_filter)
        except Exception as e:
            print(f"⚠️  API error for '{term}': {e}")
            print("")
            continue

        if not events:
            print(
                f"❌ No active markets found for '{term}'. "
                "(Odds likely not up yet for their next match.)"
            )
        else:
            for event_result in events:
                name = event_result.event.name
                print(f"✅ Found Match: {name}")
                writer.writerow([term, name])

        print("")
        time.sleep(0.3)  # Respect Betfair rate limits (~3 req/s)

print(f"📄 Results saved to: {csv_path}")
