import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Define directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def generate_synthetic_data(n_samples=2000):
    np.random.seed(42)
    
    # Generate features
    rainfall = np.random.uniform(0, 200, n_samples)  # 0 to 200 mm
    terrain_risk = np.random.uniform(0, 100, n_samples)  # hilly/steep slope
    historical_incidents = np.random.poisson(2, n_samples)  # number of past events
    road_condition = np.random.uniform(1, 10, n_samples)  # 1 (bad) to 10 (good)
    traffic = np.random.uniform(0, 100, n_samples)
    flood_risk = np.random.uniform(0, 100, n_samples)
    landslide_history = np.random.uniform(0, 100, n_samples)
    
    # field_incident_severity: 0=None, 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL
    field_incident_severity = np.random.choice([0, 1, 2, 3, 4], size=n_samples, p=[0.75, 0.1, 0.08, 0.05, 0.02])
    
    # Calculate score using a logit model
    # Positive values increase disruption risk
    logit = (
        0.018 * rainfall +
        0.015 * terrain_risk +
        0.08 * historical_incidents -
        0.35 * road_condition +
        0.005 * traffic +
        0.012 * flood_risk +
        0.016 * landslide_history +
        1.5 * field_incident_severity -
        1.5  # Bias / intercept
    )
    
    # Sigmoid function to get probability
    disruption_prob = 1 / (1 + np.exp(-logit))
    # Add minor noise
    disruption_prob = np.clip(disruption_prob + np.random.normal(0, 0.05, n_samples), 0.0, 1.0)
    
    # Binary target
    is_disrupted = (disruption_prob > 0.5).astype(int)
    
    df = pd.DataFrame({
        "rainfall": rainfall,
        "terrain_risk": terrain_risk,
        "historical_incidents": historical_incidents,
        "road_condition": road_condition,
        "traffic": traffic,
        "flood_risk": flood_risk,
        "landslide_history": landslide_history,
        "field_incident_severity": field_incident_severity,
        "is_disrupted": is_disrupted
    })
    
    return df

def train():
    print("Generating synthetic data...")
    df = generate_synthetic_data()
    
    X = df.drop(columns=["is_disrupted"])
    y = df["is_disrupted"]
    
    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    model.fit(X_scaled, y)
    
    # Save the model, scaler, and feature names
    model_path = os.path.join(MODEL_DIR, "road_risk_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
        
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
        
    print(f"Model successfully saved to: {model_path}")
    print(f"Scaler successfully saved to: {scaler_path}")
    
    # Print feature importances
    importances = model.feature_importances_
    features = X.columns
    print("\nFeature Importances:")
    for f, imp in zip(features, importances):
        print(f"  {f}: {imp:.4f}")

if __name__ == "__main__":
    train()
