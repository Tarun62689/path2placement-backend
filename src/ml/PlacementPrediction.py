#!/usr/bin/env python3
# PlacementPrediction.py (CatBoost-based, JSON output)
import os
import sys
import json
import warnings
from typing import Optional

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from supabase import create_client, Client
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()  # reads .env in project root

# ---------------------------
# Environment variables (from your .env)
# ---------------------------
PORT = os.getenv("PORT")  # optional, not used in this script but kept for completeness
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # use service role key on server only
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(json.dumps({"error": "Missing Supabase credentials in environment variables (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required)"}))
    sys.exit(1)

# Security reminder (server-side only)
if SUPABASE_KEY and "public" in SUPABASE_KEY.lower():
    # small heuristic: if the key looks like an anon/public key (not service role), warn
    print(json.dumps({"warning": "Detected a non-service role key. Ensure you're using a service role key for server-side operations if your app needs privileged access."}))

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(json.dumps({"error": f"Failed to create Supabase client: {str(e)}"}))
    sys.exit(1)

# ---------------------------
# Load CatBoost model
# ---------------------------
MODEL_PATH = "ml/placement_model_production.cbm"
if not os.path.exists(MODEL_PATH):
    print(json.dumps({"error": f"Model file not found at {MODEL_PATH}"}))
    sys.exit(1)

model = CatBoostRegressor()
try:
    model.load_model(MODEL_PATH)
except Exception as e:
    print(json.dumps({"error": f"Failed to load CatBoost model: {str(e)}"}))
    sys.exit(1)

# ---------------------------
# Helpers
# ---------------------------
def to_numeric_safe(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

def get_scalar(df: pd.DataFrame, col: str, default=np.nan):
    """
    Safely extract a scalar from a single-column, single-row DataFrame
    (or from the first row if more rows exist).
    """
    if col not in df.columns:
        return default
    s = df[col]
    if s.empty:
        return default
    val = s.iloc[0]
    if pd.isna(val):
        return default
    return val

# ---------------------------
# Fetch dataset from Supabase
# ---------------------------
try:
    resp = supabase.table("placement_data").select("*").execute()
    df_master = pd.DataFrame(resp.data)
except Exception as e:
    print(json.dumps({"error": f"Failed to fetch data from Supabase: {str(e)}"}))
    sys.exit(1)

if df_master.empty:
    print(json.dumps({"error": "No data returned from Supabase table 'placement_data'"}))
    sys.exit(1)

# Standardize column names a bit (strip)
df_master.columns = [c.strip() for c in df_master.columns]

# Convert commonly numeric fields
numeric_cols = [
    "calendar_year", "placement_rate", "placed_students", "graduating_students",
    "median_salary", "gdp_growth_rate", "unemployment_rate", "it_hiring_index",
    "avg_fresher_salary_lakhs"
]
to_numeric_safe(df_master, numeric_cols)

# Ensure we have an institute_code
if "institute_code" not in df_master.columns:
    if "institute_id" in df_master.columns:
        df_master = df_master.rename(columns={"institute_id": "institute_code"})
    elif "institute_name" in df_master.columns:
        df_master["institute_code"] = df_master["institute_name"].astype(str).str[:80]
    else:
        df_master["institute_code"] = "UNKNOWN"

df_master = df_master.sort_values(["institute_code", "calendar_year"])

# Create lagged features
df_master["prev_1yr_placement_rate"] = df_master.groupby("institute_code")["placement_rate"].shift(1)
df_master["prev_1yr_placed_count"] = df_master.groupby("institute_code")["placed_students"].shift(1)
df_master["prev_2yr_placement_rate"] = df_master.groupby("institute_code")["placement_rate"].shift(2)
df_master["prev_3yr_placement_rate"] = df_master.groupby("institute_code")["placement_rate"].shift(3)
df_master["placement_trend_1yr"] = df_master["placement_rate"] - df_master["prev_1yr_placement_rate"]
df_master["placement_avg_2yr"] = (df_master["prev_1yr_placement_rate"] + df_master["prev_2yr_placement_rate"]) / 2
df_master["placement_avg_3yr"] = (
    df_master["prev_1yr_placement_rate"] +
    df_master["prev_2yr_placement_rate"] +
    df_master["prev_3yr_placement_rate"]
) / 3
df_master["placement_volatility"] = (
    df_master.groupby("institute_code")["placement_rate"]
    .rolling(3)
    .std()
    .reset_index(0, drop=True)
)

# Economic patterns from recent years (2021-2023) — fallback if missing
recent_mask = df_master["calendar_year"].isin([2021, 2022, 2023])
recent_years = df_master[recent_mask]
economic_features = {}
for col in ["gdp_growth_rate", "unemployment_rate", "it_hiring_index", "avg_fresher_salary_lakhs"]:
    if col in recent_years.columns and not recent_years[col].dropna().empty:
        economic_features[col] = float(recent_years[col].dropna().mean())
    else:
        economic_features[col] = 0.0

economic_features.update({
    "covid_flag": 0,
    "tech_layoffs_flag": 1,
    "demonetization_flag": 1,
    "major_event": "Normal"
})

# ---------------------------
# CLI argument: college name or institute code
# ---------------------------
if len(sys.argv) < 2:
    print(json.dumps({"error": "No college name or institute code provided as argument"}))
    sys.exit(1)

query = sys.argv[1].strip()
mask = (
    (df_master["institute_code"].astype(str).str.lower() == query.lower())
    if "institute_code" in df_master.columns else False
)
if ("institute_name" in df_master.columns) and (
    df_master[~mask]["institute_name"].astype(str).str.lower().str.contains(query.lower()).any()
):
    mask = mask | df_master["institute_name"].astype(str).str.lower().str.contains(query.lower())

selected_rows = df_master[mask].copy()
if selected_rows.empty:
    if "institute_name" in df_master.columns:
        mask2 = df_master["institute_name"].astype(str).str.lower() == query.lower()
        selected_rows = df_master[mask2].copy()

if selected_rows.empty:
    print(json.dumps({"error": f"College '{query}' not found"}))
    sys.exit(1)

# Baseline and historical selection
latest_row = selected_rows.sort_values("calendar_year", ascending=False).iloc[0]
college_code = latest_row.get("institute_code")
selected_college_name = latest_row.get("institute_name") or college_code

hist_mask = (
    (df_master["institute_code"] == college_code) &
    (df_master["calendar_year"].isin([2019, 2020, 2021, 2022, 2023]))
)
historical_college = df_master[hist_mask].sort_values("calendar_year")

# Prefer the 2023-24 row where possible — ensure we have a 1-row DataFrame afterwards
if "academic_year" in df_master.columns:
    college_2023_candidates = df_master[
        (df_master["institute_code"] == college_code) &
        (df_master["academic_year"].astype(str).str.contains("2023"))
    ]
    if not college_2023_candidates.empty:
        college_2023 = college_2023_candidates.sort_values("calendar_year", ascending=False).iloc[0].copy()
    else:
        college_2023 = selected_rows.sort_values("calendar_year", ascending=False).iloc[0].copy()
else:
    college_2023 = selected_rows.sort_values("calendar_year", ascending=False).iloc[0].copy()

# Normalize to 1-row DataFrame (consistent throughout the script)
if isinstance(college_2023, pd.Series):
    college_2023 = college_2023.to_frame().T.copy()
else:
    college_2023 = college_2023.copy()

# Ensure expected numeric fields exist
for col in ["graduating_students", "median_salary", "placement_rate", "placed_students"]:
    if col not in college_2023.columns:
        college_2023[col] = np.nan

# ---------------------------
# Build future rows (2024 & 2025)
# ---------------------------
def build_future_row_from_base(base_row, year: int, prev_rate: Optional[float], prev_placed: Optional[int], prev2_rate: Optional[float], prev3_rate: Optional[float]):
    """
    base_row: can be a Series (one row) or a 1-row DataFrame.
    This function converts to a dict of scalars, fills computed fields, and returns a 1-row DataFrame.
    """
    # Convert base_row to a scalar dict
    if isinstance(base_row, pd.DataFrame):
        if base_row.shape[0] == 0:
            base_series = pd.Series(dtype=object)
        else:
            base_series = base_row.iloc[0]
    elif isinstance(base_row, pd.Series):
        base_series = base_row
    else:
        base_series = pd.Series(base_row)

    row_dict = base_series.to_dict()

    # Set/override computed fields as scalars
    row_dict["academic_year"] = f"{year}-{str(year+1)[-2:]}"
    row_dict["calendar_year"] = int(year)
    row_dict["prev_1yr_placement_rate"] = float(prev_rate) if not pd.isna(prev_rate) else np.nan
    row_dict["prev_1yr_placed_count"] = int(prev_placed) if prev_placed is not None and not pd.isna(prev_placed) else np.nan
    row_dict["prev_2yr_placement_rate"] = float(prev2_rate) if not pd.isna(prev2_rate) else np.nan
    row_dict["prev_3yr_placement_rate"] = float(prev3_rate) if not pd.isna(prev3_rate) else np.nan

    # Derived scalars
    if (not pd.isna(row_dict.get("prev_1yr_placement_rate"))) and (not pd.isna(row_dict.get("prev_2yr_placement_rate"))):
        row_dict["placement_trend_1yr"] = row_dict["prev_1yr_placement_rate"] - row_dict["prev_2yr_placement_rate"]
        row_dict["placement_avg_2yr"] = (row_dict["prev_1yr_placement_rate"] + row_dict["prev_2yr_placement_rate"]) / 2
    else:
        row_dict["placement_trend_1yr"] = np.nan
        row_dict["placement_avg_2yr"] = np.nan

    # placement_avg_3yr (might have some NaNs — keep numeric)
    p1 = row_dict.get("prev_1yr_placement_rate", np.nan)
    p2 = row_dict.get("prev_2yr_placement_rate", np.nan)
    p3 = row_dict.get("prev_3yr_placement_rate", np.nan)
    row_dict["placement_avg_3yr"] = np.nan
    try:
        arr = [x for x in (p1, p2, p3) if not pd.isna(x)]
        if arr:
            row_dict["placement_avg_3yr"] = sum(arr) / len(arr)
    except Exception:
        row_dict["placement_avg_3yr"] = np.nan

    # placement_volatility can't be computed here reliably — default to NaN (df_master computed rolling volatility already)
    row_dict["placement_volatility"] = row_dict.get("placement_volatility", np.nan)

    # Attach economic defaults
    for k, v in economic_features.items():
        row_dict[k] = v

    # Return a single-row DataFrame
    return pd.DataFrame([row_dict])

# Use safe scalars from college_2023
prev1 = get_scalar(college_2023, "placement_rate", np.nan)
prev1_placed_val = get_scalar(college_2023, "placed_students", np.nan)
prev1_placed = int(prev1_placed_val) if not pd.isna(prev1_placed_val) else None
prev2 = get_scalar(college_2023, "prev_1yr_placement_rate", np.nan)
prev3 = get_scalar(college_2023, "prev_2yr_placement_rate", np.nan)

college_2024 = build_future_row_from_base(college_2023, 2024, prev1, prev1_placed, prev2, prev3)
college_2025 = build_future_row_from_base(
    college_2024,
    2025,
    None,
    None,
    get_scalar(college_2024, "prev_1yr_placement_rate", np.nan),
    get_scalar(college_2024, "prev_2yr_placement_rate", np.nan),
)

# ---------------------------
# Feature list (must match training)
# ---------------------------
feature_cols = [
    "graduating_students", "median_salary", "college_type", "state", "tier",
    "specialization", "reputation", "autonomous", "calendar_year",
    "gdp_growth_rate", "unemployment_rate", "it_hiring_index",
    "avg_fresher_salary_lakhs", "covid_flag", "tech_layoffs_flag",
    "demonetization_flag", "major_event",
    "prev_1yr_placement_rate", "prev_1yr_placed_count",
    "prev_2yr_placement_rate", "placement_trend_1yr",
    "placement_avg_2yr", "placement_avg_3yr", "placement_volatility",
]

categorical_features = [
    "college_type", "state", "specialization",
    "reputation", "autonomous", "major_event", "tier",
]

# ---------------------------
# Prepare X_2024
# ---------------------------
row_2024 = college_2024.iloc[0]
X_2024 = pd.DataFrame([ {col: row_2024.get(col, np.nan) for col in feature_cols} ])

for col in categorical_features:
    if col in X_2024.columns:
        X_2024[col] = X_2024[col].fillna("Unknown").astype(str)

numeric_cols_in_X = X_2024.select_dtypes(include=[np.number]).columns.tolist()
for col in numeric_cols_in_X:
    if X_2024[col].isna().all():
        if col in df_master.columns and pd.to_numeric(df_master[col], errors="coerce").notna().any():
            X_2024[col] = float(pd.to_numeric(df_master[col], errors="coerce").median())
        else:
            X_2024[col] = 0.0
    else:
        X_2024[col] = X_2024[col].fillna(X_2024[col].median())

if "autonomous" in X_2024.columns:
    X_2024["autonomous"] = X_2024["autonomous"].astype(str)

# Predict 2024
try:
    pred_2024 = float(model.predict(X_2024)[0])
except Exception as e:
    print(json.dumps({"error": f"Model prediction failed for 2024: {str(e)}"}))
    sys.exit(1)

grad_students_2024 = get_scalar(college_2024, "graduating_students", get_scalar(college_2023, "graduating_students", 0))
grad_students_2024 = int(grad_students_2024 or 0)
placed_2024 = int(round(grad_students_2024 * pred_2024 / 100.0))

# ---------------------------
# Prepare 2025 using 2024 prediction
# ---------------------------
# college_2025 is a DataFrame; update scalar fields via iloc[0]
college_2025.at[college_2025.index[0], "prev_1yr_placement_rate"] = pred_2024
college_2025.at[college_2025.index[0], "prev_1yr_placed_count"] = placed_2024
college_2025.at[college_2025.index[0], "prev_2yr_placement_rate"] = get_scalar(college_2024, "prev_1yr_placement_rate", np.nan)
college_2025.at[college_2025.index[0], "prev_3yr_placement_rate"] = get_scalar(college_2024, "prev_2yr_placement_rate", np.nan)

p1 = college_2025.at[college_2025.index[0], "prev_1yr_placement_rate"]
p2 = college_2025.at[college_2025.index[0], "prev_2yr_placement_rate"]
p3 = college_2025.at[college_2025.index[0], "prev_3yr_placement_rate"]

college_2025.at[college_2025.index[0], "placement_trend_1yr"] = (p1 - p2) if (not pd.isna(p1) and not pd.isna(p2)) else np.nan
college_2025.at[college_2025.index[0], "placement_avg_2yr"] = ((p1 + p2) / 2) if (not pd.isna(p1) and not pd.isna(p2)) else np.nan
college_2025.at[college_2025.index[0], "placement_avg_3yr"] = np.nan
arr = [x for x in (p1, p2, p3) if not pd.isna(x)]
if arr:
    college_2025.at[college_2025.index[0], "placement_avg_3yr"] = sum(arr) / len(arr)

# Prepare X_2025
row_2025 = college_2025.iloc[0]
X_2025 = pd.DataFrame([ {col: row_2025.get(col, np.nan) for col in feature_cols} ])

for col in categorical_features:
    if col in X_2025.columns:
        X_2025[col] = X_2025[col].fillna("Unknown").astype(str)

numeric_cols_in_X5 = X_2025.select_dtypes(include=[np.number]).columns.tolist()
for col in numeric_cols_in_X5:
    if X_2025[col].isna().all():
        if col in df_master.columns and pd.to_numeric(df_master[col], errors="coerce").notna().any():
            X_2025[col] = float(pd.to_numeric(df_master[col], errors="coerce").median())
        else:
            X_2025[col] = 0.0
    else:
        X_2025[col] = X_2025[col].fillna(X_2025[col].median())

if "autonomous" in X_2025.columns:
    X_2025["autonomous"] = X_2025["autonomous"].astype(str)

# Predict 2025
try:
    pred_2025 = float(model.predict(X_2025)[0])
except Exception as e:
    print(json.dumps({"error": f"Model prediction failed for 2025: {str(e)}"}))
    sys.exit(1)

grad_students_2025 = get_scalar(college_2025, "graduating_students", grad_students_2024)
grad_students_2025 = int(grad_students_2025 or 0)
placed_2025 = int(round(grad_students_2025 * pred_2025 / 100.0))

# ---------------------------
# Median salary prediction (kept internal, not used in JSON)
# ---------------------------
hist_salary = historical_college[["calendar_year", "median_salary"]].dropna().copy()
pred_median_2024 = None
pred_median_2025 = None
if len(hist_salary) >= 2:
    try:
        xs = hist_salary["calendar_year"].astype(float).values
        ys = hist_salary["median_salary"].astype(float).values
        coeffs = np.polyfit(xs, ys, 1)
        pred_median_2024 = float(np.polyval(coeffs, 2024))
        pred_median_2025 = float(np.polyval(coeffs, 2025))
    except Exception:
        pred_median_2024 = float(ys[-1])
        pred_median_2025 = float(ys[-1])
else:
    last_known = get_scalar(college_2023, "median_salary", np.nan)
    if not pd.isna(last_known):
        pred_median_2024 = float(last_known)
        pred_median_2025 = float(last_known)
    else:
        proxy = get_scalar(college_2023, "avg_fresher_salary_lakhs", np.nan)
        if not pd.isna(proxy):
            pred_median_2024 = float(proxy)
            pred_median_2025 = float(proxy)
        else:
            pred_median_2024 = 0.0
            pred_median_2025 = 0.0

pred_median_2024 = round(float(pred_median_2024), 2)
pred_median_2025 = round(float(pred_median_2025), 2)

# ---------------------------
# Build JSON output (predictions only)
# ---------------------------
output = {
    "college": str(selected_college_name),
    "predictions": {
        "2024-25": {
            "placement_rate": round(float(pred_2024), 2),
            "placed_students": int(placed_2024),
        },
        "2025-26": {
            "placement_rate": round(float(pred_2025), 2),
            "placed_students": int(placed_2025),
        },
    },
}

print(json.dumps(output))
# Exit successfully
