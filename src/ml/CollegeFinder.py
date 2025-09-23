# src/ml/CollegeFinder.py
import os
import sys
import json
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
    print(json.dumps({"error": "Missing Supabase credentials"}))
    sys.exit(1)

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

# Allowed courses
courses = ['CSE', 'ECE', 'ME', 'EEE', 'OVERALL']

# --------------------------
# Helper Functions
# --------------------------
def clean_salary(salary):
    try:
        salary = str(salary).replace(' LPA', '').replace('LPA', '').strip()
        return float(salary)
    except (ValueError, TypeError):
        return 0.0

def get_recruiters(recruiters):
    try:
        return set(str(recruiters).split(','))
    except:
        return set()

def process_college_data(location, course, top_n=5):
    overall = course.lower() == 'overall'
    data_records = data.to_dict('records')

    # Filter by location
    if location.lower() != "all":
        loc = location.lower()
        data_records = [
            record for record in data_records
            if (record.get('City', '').lower() == loc or record.get('State', '').lower() == loc)
        ]
        if not data_records:
            return []

    # Aggregate college info
    college_data = defaultdict(lambda: {
        'placement_pcts': [], 'placement_trend': [],
        'salaries': [], 'highest_packages': [],
        'recruiters': set(), 'nirf_rank': float('inf')
    })

    for record in data_records:
        try:
            college = record['College Name']
            year = str(record['Year'])
        except KeyError:
            continue

        # Placement %
        try:
            if overall:
                eligible = float(record.get('Total Students Eligible', 0))
                placed = float(record.get('Total Students Placed', 0))
            else:
                eligible = float(record.get(f'{course}(Eligible)', 0))
                placed = float(record.get(f'{course}(Placed)', 0))
            placement_pct = (placed / eligible) * 100 if eligible > 0 else 0
        except:
            placement_pct = 0

        college_data[college]['placement_pcts'].append(placement_pct)
        college_data[college]['placement_trend'].append((year, placement_pct))
        college_data[college]['salaries'].append(clean_salary(record.get('Median Salary (LPA)', 0)))
        college_data[college]['highest_packages'].append(clean_salary(record.get('Highest Package', 0)))
        college_data[college]['recruiters'].update(get_recruiters(record.get('Top Recruiters', '')))
        college_data[college]['nirf_rank'] = min(college_data[college]['nirf_rank'], float(record.get('NIRF Rank', float('inf'))))

    # Prepare results
    results = []
    for college, info in college_data.items():
        avg_placement = sum(info['placement_pcts']) / len(info['placement_pcts']) if info['placement_pcts'] else 0
        avg_salary = sum(info['salaries']) / len(info['salaries']) if info['salaries'] else 0
        max_package = max(info['highest_packages']) if info['highest_packages'] else 0
        placement_trend = sorted(info['placement_trend'], key=lambda x: x[0])
        recruiters = ', '.join(sorted(info['recruiters'] - {''}))[:100]

        results.append({
            'College': college,
            'Average Placement (%)': round(avg_placement, 2),
            'NIRF Rank': info['nirf_rank'],
            'Average Salary (LPA)': round(avg_salary, 2),
            'Highest Package (LPA)': round(max_package, 2),
            'Placement Trend': placement_trend,
            'Top Recruiters': recruiters
        })

    # Sort results
    results = sorted(results, key=lambda x: (x['Average Placement (%)'], -x['NIRF Rank']), reverse=True)
    return results[:top_n]

# --------------------------
# Main: read sys.argv
# --------------------------
if __name__ == "__main__":
    try:
        location = sys.argv[1] if len(sys.argv) > 1 else "all"
        course = sys.argv[2] if len(sys.argv) > 2 else "OVERALL"
        top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    try:
        results = process_college_data(location, course, top_n)
        print(json.dumps(results))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
