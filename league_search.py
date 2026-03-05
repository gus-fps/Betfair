import betfairlightweight, os
from betfairlightweight.filters import market_filter
from dotenv import load_dotenv

load_dotenv('Betfair.env')
t = betfairlightweight.APIClient(os.environ['BF_USERNAME'], os.environ['BF_PASSWORD'], app_key=os.environ['BF_APP_KEY'], cert_files=('certs/client-2048.crt','certs/client-2048.key'))
t.login()

query = 'Chinese League 1'  # change this to search for different leagues
comps = t.betting.list_competitions(filter=market_filter(event_type_ids=['1'], text_query=query))
for c in comps:
    print(c.competition.id, c.competition.name)
