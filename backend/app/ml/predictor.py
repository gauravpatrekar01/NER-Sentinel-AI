import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Define directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")

# Global variables for model and scaler
model = None
scaler = None
feature_names = [
    "rainfall",
    "terrain_risk",
    "historical_incidents",
    "road_condition",
    "traffic",
    "flood_risk",
    "landslide_history",
    "field_incident_severity"
]

feature_display_names = {
    "rainfall": "Rainfall",
    "terrain_risk": "Terrain Risk",
    "historical_incidents": "Historical Incidents",
    "road_condition": "Road Condition",
    "traffic": "Traffic",
    "flood_risk": "Flood Risk",
    "landslide_history": "Landslide History",
    "field_incident_severity": "Field Incident"
}

# Baseline means for factor analysis
feature_means = {
    "rainfall": 60.0,
    "terrain_risk": 30.0,
    "historical_incidents": 2.0,
    "road_condition": 7.0,
    "traffic": 40.0,
    "flood_risk": 20.0,
    "landslide_history": 25.0,
    "field_incident_severity": 0.0
}

def load_model():
    global model, scaler
    model_path = os.path.join(MODEL_DIR, "road_risk_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
            print("ML model and scaler loaded successfully.")
        except Exception as e:
            print(f"Error loading ML model: {e}")
            model = None
            scaler = None
    else:
        print("ML model files not found. Run train_models.py first.")

# Try loading on import
load_model()

def predict_road_risk(
    rainfall: float,
    terrain_risk: float,
    historical_incidents: int,
    road_condition: float,
    traffic: float,
    flood_risk: float,
    landslide_history: float,
    field_incident_severity: int  # 0 to 4
) -> Dict[str, Any]:
    global model, scaler
    
    # Fallback to deterministic model if files are not loaded yet
    if model is None or scaler is None:
        load_model()
        if model is None or scaler is None:
            # Fallback mathematical model
            logit = (
                0.015 * rainfall +
                0.012 * terrain_risk +
                0.06 * historical_incidents -
                0.3 * road_condition +
                0.005 * traffic +
                0.01 * flood_risk +
                0.012 * landslide_history +
                1.4 * field_incident_severity -
                1.2
            )
            prob = 1 / (1 + np.exp(-logit))
            prob = float(np.clip(prob, 0.0, 1.0))
            
            # Simple factors
            factors = [
                {"name": "Rainfall", "impact": round(rainfall * 0.25)},
                {"name": "Historical Incidents", "impact": round(historical_incidents * 8)},
                {"name": "Terrain Risk", "impact": round(terrain_risk * 0.15)},
                {"name": "Road Condition", "impact": round((10 - road_condition) * 3)}
            ]
            factors = sorted(factors, key=lambda x: x["impact"], reverse=True)
            
            acc_score = round(100.0 * (1.0 - prob))
            risk_level = "LOW"
            if prob >= 0.8:
                risk_level = "CRITICAL"
            elif prob >= 0.5:
                risk_level = "HIGH"
            elif prob >= 0.2:
                risk_level = "MODERATE"
                
            return {
                "accessibility_score": acc_score,
                "disruption_probability": round(prob, 2),
                "risk_level": risk_level,
                "factors": factors
            }
            
    # Format input data
    input_data = pd.DataFrame([[
        rainfall,
        terrain_risk,
        historical_incidents,
        road_condition,
        traffic,
        flood_risk,
        landslide_history,
        field_incident_severity
    ]], columns=feature_names)
    
    # Scale input
    input_scaled = scaler.transform(input_data)
    
    # Predict probability of disruption (class 1)
    prob = float(model.predict_proba(input_scaled)[0][1])
    
    # Accessibility Score
    acc_score = int(round(100.0 * (1.0 - prob)))
    
    # Determine risk level
    risk_level = "LOW"
    if prob >= 0.8:
        risk_level = "CRITICAL"
    elif prob >= 0.5:
        risk_level = "HIGH"
    elif prob >= 0.2:
        risk_level = "MODERATE"
        
    # Explainability factors (Feature contributions)
    # RF feature importances
    importances = model.feature_importances_
    
    raw_contributions = {}
    for idx, name in enumerate(feature_names):
        val = input_data.iloc[0][name]
        mean = feature_means[name]
        importance = importances[idx]
        
        if name == "road_condition":
            # For road condition, a LOWER value than mean increases risk
            contrib = (mean - val) * importance * 10
        else:
            # For others, a HIGHER value than mean increases risk
            contrib = (val - mean) * importance * 10
            
        raw_contributions[name] = max(0.0, contrib)
        
    # Scale raw contributions to sum to something meaningful, e.g. proportional to risk probability
    total_contrib = sum(raw_contributions.values())
    factors_list = []
    
    if total_contrib > 0:
        # Scale to match disruption probability out of 100
        multiplier = (prob * 100) / total_contrib
        for name, contrib in raw_contributions.items():
            impact_score = round(contrib * multiplier)
            if impact_score > 0:
                factors_list.append({
                    "name": feature_display_names[name],
                    "impact": impact_score
                })
    else:
        # Default distribution based on importances if total contrib is 0
        for name, importance in zip(feature_names, importances):
            impact_score = round(importance * prob * 100)
            if impact_score > 0:
                factors_list.append({
                    "name": feature_display_names[name],
                    "impact": impact_score
                })
                
    # Sort factors by impact
    factors_list = sorted(factors_list, key=lambda x: x["impact"], reverse=True)
    
    # Cap factors list to top 5
    factors_list = factors_list[:5]
    
    return {
        "accessibility_score": acc_score,
        "disruption_probability": round(prob, 2),
        "risk_level": risk_level,
        "factors": factors_list
    }
