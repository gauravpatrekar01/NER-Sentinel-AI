"""
XGBoost disruption prediction model.
Uses synthetic training data when no real dataset is available.
"""

from __future__ import annotations

import os
import pickle
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "disruption_xgb.pkl")

_disruption_model = None
_feature_names = [
    "rainfall",
    "traffic",
    "road_condition",
    "road_risk",
    "historical_incidents",
    "incident_count",
    "terrain_risk",
    "vehicle_speed",
    "distance",
    "historical_travel_time",
]


def generate_synthetic_disruption_data(n_samples: int = 3000) -> pd.DataFrame:
    """Small documented synthetic dataset for prototype disruption prediction."""
    np.random.seed(42)
    rainfall = np.random.uniform(0, 250, n_samples)
    traffic = np.random.uniform(0, 100, n_samples)
    road_condition = np.random.uniform(1, 10, n_samples)
    road_risk = np.random.uniform(0, 100, n_samples)
    historical_incidents = np.random.poisson(3, n_samples)
    incident_count = np.random.poisson(1, n_samples)
    terrain_risk = np.random.uniform(0, 100, n_samples)
    vehicle_speed = np.random.uniform(20, 70, n_samples)
    distance = np.random.uniform(30, 300, n_samples)
    historical_travel_time = distance / np.random.uniform(30, 60, n_samples)

    logit = (
        0.012 * rainfall
        + 0.008 * traffic
        - 0.25 * road_condition
        + 0.01 * road_risk
        + 0.15 * historical_incidents
        + 0.35 * incident_count
        + 0.006 * terrain_risk
        - 0.01 * vehicle_speed
        + 0.002 * distance
        - 1.8
    )
    prob = 1 / (1 + np.exp(-logit))
    disrupted = (prob + np.random.normal(0, 0.05, n_samples) > 0.5).astype(int)

    return pd.DataFrame({
        "rainfall": rainfall,
        "traffic": traffic,
        "road_condition": road_condition,
        "road_risk": road_risk,
        "historical_incidents": historical_incidents,
        "incident_count": incident_count,
        "terrain_risk": terrain_risk,
        "vehicle_speed": vehicle_speed,
        "distance": distance,
        "historical_travel_time": historical_travel_time,
        "disrupted": disrupted,
    })


def train_disruption_model() -> None:
    """Train and persist XGBoost disruption model."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("XGBoost not installed; disruption model will use fallback.")
        return

    df = generate_synthetic_disruption_data()
    X = df[_feature_names]
    y = df["disrupted"]

    model = XGBClassifier(
        n_estimators=80,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric="logloss",
    )
    model.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": _feature_names}, f)
    print(f"Disruption XGBoost model saved to {MODEL_PATH}")


def load_disruption_model() -> bool:
    global _disruption_model
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                data = pickle.load(f)
            _disruption_model = data
            return True
        except Exception as e:
            print(f"Error loading disruption model: {e}")
    return False


def _fallback_disruption(features: Dict[str, float]) -> Dict[str, Any]:
    logit = (
        0.012 * features.get("rainfall", 0)
        + 0.008 * features.get("traffic", 0)
        - 0.25 * features.get("road_condition", 5)
        + 0.01 * features.get("road_risk", 0)
        + 0.15 * features.get("historical_incidents", 0)
        + 0.35 * features.get("incident_count", 0)
        + 0.006 * features.get("terrain_risk", 0)
        - 1.5
    )
    prob = float(1 / (1 + np.exp(-logit)))
    prob = max(0.0, min(1.0, prob))
    risk_score = round(prob * 100)
    risk_level = "LOW"
    if prob >= 0.81:
        risk_level = "CRITICAL"
    elif prob >= 0.61:
        risk_level = "HIGH"
    elif prob >= 0.31:
        risk_level = "MODERATE"
    return {
        "probability": round(prob, 2),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "model": "fallback",
    }


def predict_disruption(features: Dict[str, float]) -> Dict[str, Any]:
    """Predict route disruption probability."""
    global _disruption_model
    if _disruption_model is None:
        load_disruption_model()

    if _disruption_model is None:
        return _fallback_disruption(features)

    model = _disruption_model["model"]
    feat_names = _disruption_model["features"]
    row = [[features.get(f, 0.0) for f in feat_names]]
    prob = float(model.predict_proba(row)[0][1])
    risk_score = round(prob * 100)
    risk_level = "LOW"
    if prob >= 0.81:
        risk_level = "CRITICAL"
    elif prob >= 0.61:
        risk_level = "HIGH"
    elif prob >= 0.31:
        risk_level = "MODERATE"

    return {
        "probability": round(prob, 2),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "model": "xgboost",
    }
