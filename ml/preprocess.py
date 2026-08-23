"""
ML Preprocessing Pipeline for Delhi Traffic & Weather Dataset.
Processes raw data, encodes categorical/temporal features, splits into train/test,
and saves preprocessed datasets and feature schema.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Categorical column definitions
CATEGORICAL_COLS = ["road_type", "weather_condition", "vehicle_type"]
NUMERICAL_COLS = [
    "distance_km",
    "base_speed_limit_kmh",
    "traffic_density_index",
    "temperature_c",
    "visibility_km",
    "precipitation_mm",
    "wind_speed_kmh",
    "road_gradient_percent",
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "is_weekend"
]
TARGET_TIME = "travel_time_minutes"
TARGET_FUEL = "fuel_consumption_units"

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer cyclical time features and derived indicators."""
    df = df.copy()
    
    # Cyclical hour features
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24.0)
    
    # Cyclical day features
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7.0)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7.0)
    
    # Weekend indicator
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    
    return df

class TrafficDataPreprocessor:
    def __init__(self):
        self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_fitted = False

    def fit(self, df: pd.DataFrame):
        df_eng = engineer_features(df)
        
        # Fit One-Hot Encoder on categoricals
        self.encoder.fit(df_eng[CATEGORICAL_COLS])
        cat_feature_names = list(self.encoder.get_feature_names_out(CATEGORICAL_COLS))
        
        # All feature names
        self.feature_names = NUMERICAL_COLS + cat_feature_names
        
        # Transform full matrix and fit scaler
        cat_encoded = self.encoder.transform(df_eng[CATEGORICAL_COLS])
        num_data = df_eng[NUMERICAL_COLS].values
        combined_features = np.hstack([num_data, cat_encoded])
        
        self.scaler.fit(combined_features)
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Preprocessor has not been fitted yet.")
        df_eng = engineer_features(df)
        cat_encoded = self.encoder.transform(df_eng[CATEGORICAL_COLS])
        num_data = df_eng[NUMERICAL_COLS].values
        combined = np.hstack([num_data, cat_encoded])
        return self.scaler.transform(combined)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        return self.fit(df).transform(df)

def run_preprocessing(raw_csv_path: str, output_dir: str):
    print(f"Loading raw dataset from {raw_csv_path}...")
    df = pd.read_csv(raw_csv_path)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Checking for null values: {df.isnull().sum().to_dict()}")
    
    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42, shuffle=True)
    print(f"Train split: {len(train_df)} rows | Test split: {len(test_df)} rows")
    
    preprocessor = TrafficDataPreprocessor()
    X_train = preprocessor.fit_transform(train_df)
    X_test = preprocessor.transform(test_df)
    
    y_train_time = train_df[TARGET_TIME].values
    y_test_time = test_df[TARGET_TIME].values
    
    y_train_fuel = train_df[TARGET_FUEL].values
    y_test_fuel = test_df[TARGET_FUEL].values
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save preprocessor artifact
    preprocessor_path = os.path.join(output_dir, "preprocessor.joblib")
    joblib.dump(preprocessor, preprocessor_path)
    print(f"Saved preprocessor to {preprocessor_path}")
    print(f"Total processed feature dimensions: {X_train.shape[1]}")
    print(f"Feature names: {preprocessor.feature_names}")
    
    # Save train/test numpy arrays
    np.savez_compressed(
        os.path.join(output_dir, "train_test_data.npz"),
        X_train=X_train,
        X_test=X_test,
        y_train_time=y_train_time,
        y_test_time=y_test_time,
        y_train_fuel=y_train_fuel,
        y_test_fuel=y_test_fuel
    )
    print(f"Saved processed train/test arrays to {os.path.join(output_dir, 'train_test_data.npz')}")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_path = os.path.join(base_dir, "data", "raw", "delhi_traffic.csv")
    processed_dir = os.path.join(base_dir, "data", "processed")
    run_preprocessing(raw_path, processed_dir)
