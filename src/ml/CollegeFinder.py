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

# Allowed courses
courses = ['CSE', 'ECE', 'ME', 'EEE', 'OVERALL']

# Extract unique cities and states
cities = sorted(data['City'].dropna().unique())
states = sorted(data['State'].dropna().unique())

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
            raise ValueError(f"No colleges found in location: {location}")

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
# Interactive CLI
# --------------------------
def main():
    print("\n===== Path2Placement College Finder =====")

    # Location selection
    print("\nChoose a location type:")
    print("1. All India")
    print("2. By City")
    print("3. By State")
    loc_choice = input("Enter choice: ").strip()

    if loc_choice == "1":
        location = "all"
    elif loc_choice == "2":
        print("\nAvailable Cities:")
        for i, city in enumerate(cities, 1):
            print(f"{i}. {city}")
        try:
            city_choice = int(input("Enter city number: "))
            location = cities[city_choice - 1]
        except:
            print("Invalid choice, defaulting to All India.")
            location = "all"
    elif loc_choice == "3":
        print("\nAvailable States:")
        for i, state in enumerate(states, 1):
            print(f"{i}. {state}")
        try:
            state_choice = int(input("Enter state number: "))
            location = states[state_choice - 1]
        except:
            print("Invalid choice, defaulting to All India.")
            location = "all"
    else:
        print("Invalid choice, defaulting to All India.")
        location = "all"

    # Course selection
    print("\nChoose a course:")
    for i, c in enumerate(courses, 1):
        print(f"{i}. {c}")
    try:
        course_choice = int(input("Enter choice: "))
        course = courses[course_choice - 1]
    except:
        print("Invalid choice, defaulting to OVERALL.")
        course = "OVERALL"

    # Top N
    try:
        top_n = int(input("\nHow many top colleges? (default 5): ").strip() or 5)
    except:
        top_n = 5

    # Process
    results = process_college_data(location, course, top_n)

    # Display table
    print(f"\n🏆 Top {len(results)} Colleges for {course} in {location if location!='all' else 'India'}")
    print("-" * 85)
    print(f"{'Rank':<6} {'College':<35} {'NIRF':<6} {'Avg Placement':<15} {'Avg Salary':<12} {'Max Package':<12}")
    print("-" * 85)
    for i, college in enumerate(results, 1):
        print(f"{i:<6} {college['College'][:34]:<35} {college['NIRF Rank']:<6.0f} "
              f"{college['Average Placement (%)']:<15.2f} {college['Average Salary (LPA)']:<12.2f} "
              f"{college['Highest Package (LPA)']:<12.2f}")
    print("-" * 85)

    # Detailed info
    for i, college in enumerate(results, 1):
        print(f"\n📌 Details for Rank {i}: {college['College']}")
        print("📈 Placement Trend (Year → %):")
        for year, pct in college['Placement Trend']:
            print(f"  {year}: {pct:.2f}%")
        print(f"🏢 Top Recruiters: {college['Top Recruiters']}")

if __name__ == "__main__":
    main()
