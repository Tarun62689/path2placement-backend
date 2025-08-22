# PlacementPrediction.py
import os
import sys
import json
import pandas as pd
from supabase import create_client, Client
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
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

data['Year'] = data['Year'].astype(str).str.strip().str.split('-').str[-1]

# Features & Targets
features = [
    'NIRF Rank', 'Total Students Eligible', 'Total Students Placed',
    'CSE(Eligible)', 'CSE(Placed)', 'ECE(Eligible)', 'ECE(Placed)',
    'ME(Eligible)', 'ME(Placed)', 'EEE(Eligible)', 'EEE(Placed)'
]
target_placement = 'Placement Percentage'
target_salary = 'Median Salary (LPA)'


def get_college_data(college_name: str):
    college_data_filtered = data[data['College Name'] == college_name].copy()
    if college_data_filtered.empty:
        return None, None, None

    college_data_filtered['Year'] = college_data_filtered['Year'].astype(int)
    X = college_data_filtered[features].fillna(0)
    y_placement = college_data_filtered[target_placement]
    y_salary = (
        college_data_filtered[target_salary]
        .astype(str)
        .str.replace(' LPA', '', regex=False)
        .astype(float)
    )
    return X, y_placement, y_salary


def train_and_predict(X, y_placement, y_salary, college_name):
    # Train/test split
    X_train, X_test, y_train_p, y_test_p = train_test_split(
        X, y_placement, test_size=0.2, random_state=42
    )
    X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
        X, y_salary, test_size=0.2, random_state=42
    )

    # Scaling
    scaler_p, scaler_s = StandardScaler(), StandardScaler()
    X_train_p, X_test_p = scaler_p.fit_transform(X_train), scaler_p.transform(X_test)
    X_train_s, X_test_s = scaler_s.fit_transform(X_train_s), scaler_s.transform(X_test_s)

    # Models
    model_p = RandomForestRegressor(n_estimators=100, random_state=42)
    model_s = RandomForestRegressor(n_estimators=100, random_state=42)

    model_p.fit(X_train_p, y_train_p)
    model_s.fit(X_train_s, y_train_s)

    # Predict future years
    X_future = X.iloc[[-1]]
    pred_p_2024 = model_p.predict(scaler_p.transform(X_future))[0]
    pred_s_2024 = model_s.predict(scaler_s.transform(X_future))[0]

    pred_p_2025 = pred_p_2024 * 1.02
    pred_s_2025 = pred_s_2024 * 1.05

    # Return JSON instead of print
    return {
        "college": college_name,
        "predictions": {
            "2024": {"placement": round(pred_p_2024, 2), "salary": round(pred_s_2024, 2)},
            "2025": {"placement": round(pred_p_2025, 2), "salary": round(pred_s_2025, 2)}
        }
    }


if __name__ == "__main__":
    # Get college name from Node.js (argument)
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No college name provided"}))
        sys.exit(1)

    college_name = sys.argv[1]
    X, y_p, y_s = get_college_data(college_name)
    if X is None:
        print(json.dumps({"error": f"College '{college_name}' not found"}))
    else:
        result = train_and_predict(X, y_p, y_s, college_name)
        print(json.dumps(result))
