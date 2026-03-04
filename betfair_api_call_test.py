import betfairlightweight
import os
from dotenv import load_dotenv

# 1. CREDENTIALS & LOGIN SETUP
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Betfair.env"))

USERNAME = os.environ["BF_USERNAME"]
PASSWORD = os.environ["BF_PASSWORD"]
APP_KEY  = os.environ["BF_APP_KEY"]

_script_dir = os.path.dirname(os.path.abspath(__file__))
MY_CERTS = (
    os.path.join(_script_dir, "certs", "client-2048.crt"),
    os.path.join(_script_dir, "certs", "client-2048.key"),
)

print("Initializing Betfair Client...")

# 2. Build the Client object
trading = betfairlightweight.APIClient(
    username=USERNAME,
    password=PASSWORD,
    app_key=APP_KEY,
    cert_files=MY_CERTS
)

# 4. Attempt to log in
try:
    print("Attempting to log into Betfair API...")
    trading.login()
    
    # If it works, it will print this success message!
    print("\n✅ SUCCESS: You are officially logged into the Betfair API!")
    print(f"Session Token: {trading.session_token[:10]}... (Hidden for security)")
    
except betfairlightweight.exceptions.LoginError as e:
    # If it fails, it will catch the error and tell you exactly why
    print("\n❌ ERROR: Login Failed.")
    print(e)