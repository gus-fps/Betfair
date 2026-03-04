import pandas as pd
import matplotlib.pyplot as plt

print("Downloading match data...")

# 1. Load the Premier League data from the web
url = "https://www.football-data.co.uk/mmz4281/2324/E0.csv"
df = pd.read_csv(url)

# 2. Count the Full Time Results (FTR column: H=Home Win, A=Away Win, D=Draw)
results_count = df['FTR'].value_counts()
print("\nRaw Data Counts:")
print(results_count)

# 3. Create the Bar Chart
print("\nGenerating chart...")
results_count.plot(kind='bar', color=['#1f77b4', '#d62728', '#7f7f7f'], edgecolor='black')

# 4. Make it look professional with titles and labels
plt.title('English Premier League 23/24: Match Outcomes', fontsize=14, fontweight='bold')
plt.xlabel('Result (H = Home Win, A = Away Win, D = Draw)', fontsize=12)
plt.ylabel('Number of Matches', fontsize=12)
plt.xticks(rotation=0) # Keeps the H, A, and D labels straight

# 5. Display the window!
plt.show()