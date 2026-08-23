import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Ensure root dir is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ml.preprocess import TrafficDataPreprocessor, engineer_features


def evaluate_predictions(y_true, y_pred, model_name="Model", target_name="Target"):
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    print(f"[{model_name}] -> {target_name}:")
    print(f"  MAE:  {mae:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R²:   {r2:.4f}")
    return {"model": model_name, "target": target_name, "mae": mae, "rmse": rmse, "r2": r2}

def train_and_evaluate(data_npz_path: str, preprocessor_path: str, models_dir: str):
    print(f"Loading preprocessed data from {data_npz_path}...")
    data = np.load(data_npz_path)
    X_train = data["X_train"]
    X_test = data["X_test"]
    y_train_time = data["y_train_time"]
    y_test_time = data["y_test_time"]
    y_train_fuel = data["y_train_fuel"]
    y_test_fuel = data["y_test_fuel"]
    
    preprocessor = joblib.load(preprocessor_path)
    feature_names = preprocessor.feature_names
    
    print(f"Loaded {X_train.shape[0]} training samples with {X_train.shape[1]} features.")
    
    # -------------------------------------------------------------
    # Phase 4 & 5: Model Selection for Travel Time Prediction
    # -------------------------------------------------------------
    print("\n" + "="*50)
    print("--- EVALUATING TRAVEL TIME PREDICTION MODELS ---")
    print("="*50)
    
    models_time = {
        "Linear Regression (Baseline)": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=100, max_depth=16, random_state=42, n_jobs=-1),
        "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=120, max_depth=6, learning_rate=0.1, random_state=42)
    }
    
    time_results = []
    trained_time_models = {}
    
    for name, model in models_time.items():
        print(f"\nTraining {name} for Travel Time...")
        model.fit(X_train, y_train_time)
        preds = model.predict(X_test)
        metrics = evaluate_predictions(y_test_time, preds, model_name=name, target_name="Travel Time (min)")
        time_results.append(metrics)
        trained_time_models[name] = model
        
    # -------------------------------------------------------------
    # Model Selection for Fuel Consumption Prediction
    # -------------------------------------------------------------
    print("\n" + "="*50)
    print("--- EVALUATING FUEL CONSUMPTION PREDICTION MODELS ---")
    print("="*50)
    
    models_fuel = {
        "Linear Regression (Baseline)": LinearRegression(),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=100, max_depth=16, random_state=42, n_jobs=-1),
        "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=120, max_depth=6, learning_rate=0.1, random_state=42)
    }
    
    fuel_results = []
    trained_fuel_models = {}
    
    for name, model in models_fuel.items():
        print(f"\nTraining {name} for Fuel Consumption...")
        model.fit(X_train, y_train_fuel)
        preds = model.predict(X_test)
        metrics = evaluate_predictions(y_test_fuel, preds, model_name=name, target_name="Fuel Units (L/kWh)")
        fuel_results.append(metrics)
        trained_fuel_models[name] = model

    # Select Best Models (Highest R2)
    best_time_model_name = max(time_results, key=lambda x: x["r2"])["model"]
    best_time_model = trained_time_models[best_time_model_name]
    
    best_fuel_model_name = max(fuel_results, key=lambda x: x["r2"])["model"]
    best_fuel_model = trained_fuel_models[best_fuel_model_name]
    
    print("\n" + "="*50)
    print("--- FINAL MODEL SELECTION & COMPARISON ---")
    print("="*50)
    print(f"Best Travel Time Model: {best_time_model_name}")
    print(f"Best Fuel Model:        {best_fuel_model_name}")
    
    # Feature Importances for Best Travel Time Model (if tree-based)
    if hasattr(best_time_model, "feature_importances_"):
        importances = best_time_model.feature_importances_
        sorted_idx = np.argsort(importances)[::-1]
        print("\nTop 10 Most Important Features for Travel Time:")
        for rank, idx in enumerate(sorted_idx[:10], 1):
            feat = feature_names[idx] if idx < len(feature_names) else f"Feature {idx}"
            print(f"  {rank}. {feat:30s}: {importances[idx]:.4f}")
            
    # -------------------------------------------------------------
    # Phase 6: Save the Trained Inference Package
    # -------------------------------------------------------------
    os.makedirs(models_dir, exist_ok=True)
    
    model_artifact = {
        "time_model": best_time_model,
        "fuel_model": best_fuel_model,
        "time_model_name": best_time_model_name,
        "fuel_model_name": best_fuel_model_name,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "time_metrics": [r for r in time_results if r["model"] == best_time_model_name][0],
        "fuel_metrics": [r for r in fuel_results if r["model"] == best_fuel_model_name][0]
    }
    
    artifact_path = os.path.join(models_dir, "traffic_model.joblib")
    joblib.dump(model_artifact, artifact_path)
    print(f"\n[SUCCESS] Saved serialized production model artifact to:\n  -> {artifact_path}")
    
    # Save a CSV comparison table for PPT / Documentation
    metrics_df = pd.DataFrame(time_results + fuel_results)
    metrics_csv_path = os.path.join(models_dir, "model_comparison_metrics.csv")
    metrics_df.to_csv(metrics_csv_path, index=False)
    print(f"Saved model comparison table to:\n  -> {metrics_csv_path}")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    npz_path = os.path.join(base_dir, "data", "processed", "train_test_data.npz")
    preproc_path = os.path.join(base_dir, "data", "processed", "preprocessor.joblib")
    models_out = os.path.join(base_dir, "ml", "models")
    train_and_evaluate(npz_path, preproc_path, models_out)
