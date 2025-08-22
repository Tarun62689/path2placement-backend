# src/ml/CollegeInsights.py
import os
import sys
import json
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials! Add them to .env")

# Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch data
response = supabase.table("College_Placements_Data").select("*").execute()
data = pd.DataFrame(response.data)

# Clean data
if "_id" in data.columns:
    data.drop("_id", axis=1, inplace=True)

# Normalize year column
data['Year'] = data['Year'].astype(str).str.strip().str.split('-').str[-1]

def get_college_insights(college_name: str):
    college_data = data[data['College Name'].str.lower() == college_name.lower()]
    if college_data.empty:
        return {"error": f"College '{college_name}' not found"}

    college_data['Year'] = college_data['Year'].astype(int)

    # ✅ Get image (if exists in the dataset)
    college_image = None
    if "College Image" in college_data.columns:
        # take the first non-null image for the college
        college_image = college_data["College Image"].dropna().values[0] if not college_data["College Image"].isnull().all() else None

    # Year-wise Placement %
    placement_trends = {
        str(row["Year"]): row["Placement Percentage"]
        for _, row in college_data.iterrows()
    }

    # Average placement across all years
    avg_placement = round(college_data['Placement Percentage'].mean(), 2)

    # Salary Trends
    salary_trends = {
        str(row["Year"]): {
            "highest": str(row["Highest Package"]),
            "median": str(row["Median Salary (LPA)"])
        }
        for _, row in college_data.iterrows()
    }

    # Top recruiters (latest year only)
    latest_year = college_data["Year"].max()
    latest_row = college_data[college_data["Year"] == latest_year]
    top_recruiters = []
    if not latest_row.empty:
        recruiters_data = latest_row["Top Recruiters"].values[0]
        if isinstance(recruiters_data, str):
            top_recruiters = [r.strip() for r in recruiters_data.split(",")]

    return {
        "college": college_name,
        "collegeImage": college_image,   
        "placementTrends": placement_trends,
        "averagePlacement": avg_placement,
        "salaryTrends": salary_trends,
        "topRecruiters": top_recruiters,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No college name provided"}))
        sys.exit(1)

    college_name = sys.argv[1]
    result = get_college_insights(college_name)
    print(json.dumps(result))
