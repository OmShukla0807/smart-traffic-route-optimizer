"""
Model Training and Serialization Script.
Trains:
- Linear Regression (Baseline)
- Ridge Regression
- Random Forest Regressor
- Gradient Boosting Regressor (Final Selected Model)

Evaluates on:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R² Score

Serializes the production bundle to `ml/models/traffic_model.joblib`.
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml.preprocess import TrafficDataPreprocessor

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "ml" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def train_and_evaluate():
    print("="*70)
    print("STARTING MODEL TRAINING & COMPARATIVE BENCHMARKING (WITH AQI & ROAD NETWORK)")
    print("="*70)

    npz_path = PROCESSED_DIR / "train_test_data.npz"
    if not npz_path.exists():
        raise FileNotFoundError(f"Processed dataset not found at {npz_path}. Run ml/preprocess.py first.")

    data = np.load(npz_path)
    X_train = data["X_train"]
    X_test = data["X_test"]
    y_train_time = data["y_train_time"]
    y_test_time = data["y_test_time"]
    y_train_fuel = data["y_train_fuel"]
    y_test_fuel = data["y_test_fuel"]

    preprocessor = joblib.load(PROCESSED_DIR / "preprocessor.joblib")
    feature_names = preprocessor.feature_names

    print(f"X_train shape: {X_train.shape} | X_test shape: {X_test.shape}")
    print(f"Training features ({len(feature_names)}): {feature_names}\n")

    # 1. Models to evaluate for Travel Time
    models_to_test = {
        "Linear Regression (Baseline)": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=60, max_depth=12, n_jobs=-1, random_state=42),
        "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=120, max_depth=6, learning_rate=0.1, random_state=42)
    }

    metrics_records = []
    trained_time_models = {}

    print("--- EVALUATING TRAVEL TIME PREDICTION MODELS ---")
    for name, model in models_to_test.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train_time)
        preds = model.predict(X_test)
        
        mae = mean_absolute_error(y_test_time, preds)
        rmse = np.sqrt(mean_squared_error(y_test_time, preds))
        r2 = r2_score(y_test_time, preds)
        
        trained_time_models[name] = model
        metrics_records.append({
            "Target": "Travel Time (min)",
            "Model": name,
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "R2_Score": round(r2, 4)
        })
        print(f"  --> MAE: {mae:.3f} min | RMSE: {rmse:.3f} | R²: {r2:.4f}")

    # 2. Train Fuel/Energy Model (Gradient Boosting)
    print("\n--- TRAINING FUEL & ENERGY CONSUMPTION MODEL ---")
    fuel_model = GradientBoostingRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    fuel_model.fit(X_train, y_train_fuel)
    fuel_preds = fuel_model.predict(X_test)

    fuel_mae = mean_absolute_error(y_test_fuel, fuel_preds)
    fuel_rmse = np.sqrt(mean_squared_error(y_test_fuel, fuel_preds))
    fuel_r2 = r2_score(y_test_fuel, fuel_preds)

    metrics_records.append({
        "Target": "Fuel/Energy (Units)",
        "Model": "Gradient Boosting Regressor",
        "MAE": round(fuel_mae, 4),
        "RMSE": round(fuel_rmse, 4),
        "R2_Score": round(fuel_r2, 4)
    })
    print(f"  --> Fuel Model MAE: {fuel_mae:.4f} units | RMSE: {fuel_rmse:.4f} | R²: {fuel_r2:.4f}")

    # 3. Save metrics summary table
    metrics_df = pd.DataFrame(metrics_records)
    metrics_csv = MODELS_DIR / "model_comparison_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)
    print(f"\nSaved benchmark comparison table to: {metrics_csv}")
    print("\n" + metrics_df.to_string(index=False))

    # 4. Serialize production model bundle
    best_time_model = trained_time_models["Gradient Boosting Regressor"]
    
    bundle = {
        "time_model": best_time_model,
        "fuel_model": fuel_model,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "time_model_name": "Gradient Boosting Regressor",
        "time_model_r2": round(r2_score(y_test_time, best_time_model.predict(X_test)), 4),
        "fuel_model_r2": round(fuel_r2, 4)
    }

    model_out_path = MODELS_DIR / "traffic_model.joblib"
    joblib.dump(bundle, model_out_path)
    print(f"\n[OK] Serialized production bundle to: {model_out_path}")

    # 5. Print top feature importances
    gb_importances = best_time_model.feature_importances_
    sorted_idx = np.argsort(gb_importances)[::-1]
    print("\n--- TOP 10 FEATURE IMPORTANCES (TRAVEL TIME MODEL) ---")
    for rank, idx in enumerate(sorted_idx[:10], 1):
        print(f" {rank:2d}. {feature_names[idx]:30s} : {gb_importances[idx]:.4f}")

if __name__ == "__main__":
    train_and_evaluate()
