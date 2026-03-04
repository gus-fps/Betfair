import pandas as pd

# URL for the English Premier League 2023/2024 historical match data
url = "https://www.football-data.co.uk/mmz4281/2324/E0.csv"

# Load the CSV data directly into a pandas DataFrame
df = pd.read_csv(url)

# Print the total number of matches (number of rows in the DataFrame)
print(f"Total number of matches: {len(df)}")

# Print the first 5 rows to inspect the structure of the data
print(df.head())