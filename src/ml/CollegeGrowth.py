# src/ml/PlacementGrowth.py
import os
import pandas as pd
from collections import defaultdict
from supabase import create_client, Client
from dotenv import load_dotenv

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials! Add them to .env")

# --------------------------
# Supabase client
# --------------------------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------
# Fetch data
# --------------------------
response = supabase.table("College_Placements_Data").select("*").execute()
data = pd.DataFrame(response.data)

# Clean data
if "_id" in data.columns:
    data.drop("_id", axis=1, inplace=True)
data['Year'] = data['Year'].astype(str).str.strip().str.split('-').str[-1]

# --------------------------
# Placement Growth Comparison
# --------------------------
def placement_growth(top_n=5):
    college_data = defaultdict(list)

    for record in data.to_dict('records'):
        college = record.get('College Name', 'Unknown')
        year = str(record.get('Year', 'NA'))

        eligible = float(record.get("Total Students Eligible", 0))
        placed = float(record.get("Total Students Placed", 0))
        placement_pct = (placed / eligible) * 100 if eligible > 0 else 0

        college_data[college].append((year, placement_pct))

    results = []
    for college, trend in college_data.items():
        trend = sorted(trend, key=lambda x: x[0])  # sort by year
        if len(trend) >= 2:
            start_year, start_pct = trend[0]
            end_year, end_pct = trend[-1]
            growth = ((end_pct - start_pct) / start_pct * 100) if start_pct > 0 else 0
            arrow = "📈" if growth > 0 else ("📉" if growth < 0 else "➖")
            results.append({
                "College": college,
                "Start Year": start_year,
                "End Year": end_year,
                "Growth %": round(growth, 2),
                "Indicator": arrow,
                "Trend": trend
            })

    results = sorted(results, key=lambda x: x["Growth %"], reverse=True)

    # Display
    print(f"\n📊 Top {top_n} Colleges by Overall Placement Growth:")
    print("-" * 70)
    for i, res in enumerate(results[:top_n], 1):
        print(f"{i}. {res['College']} | {res['Start Year']} → {res['End Year']} | Growth: {res['Growth %']}% {res['Indicator']}")
        print("   Placement Trend:", " → ".join([f"{y}:{p:.1f}%" for y, p in res['Trend']]))

# --------------------------
# CLI
# --------------------------
def main():
    print("\n===== Path2Placement – Overall Placement Growth Comparison =====")
    try:
        top_n = int(input("\nHow many colleges? (default 5): ").strip() or 5)
    except:
        top_n = 5

    placement_growth(top_n)

if __name__ == "__main__":
    main()
