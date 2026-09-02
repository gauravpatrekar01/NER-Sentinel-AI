"""
XGBoost delivery delay prediction model.
"""

from __future__ import annotations

import os
import pickle
from typing import Any, Dict

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "delay_xgb.pkl")

_delay_model = None
_feature_names = [
    "rainfall",
    "traffic",
    "road_risk",
    "distance",
    "vehicle_speed",
    "historical_travel_time",
    "incident_count",
    "terrain_risk",
]


def generate_synthetic_delay_data(n_samples: int = 3000) -> pd.DataFrame:
    np.random.seed(43)
    rainfall = np.random.uniform(0, 250, n_samples)
    traffic = np.random.uniform(0, 100, n_samples)
    road_risk = np.random.uniform(0, 100, n_samples)
    distance = np.random.uniform(30, 350, n_samples)
    vehicle_speed = np.random.uniform(20, 65, n_samples)
    historical_travel_time = distance / np.random.uniform(35, 55, n_samples)
    incident_count = np.random.poisson(1, n_samples)
    terrain_risk = np.random.uniform(0, 100, n_samples)

    base_delay = (
        0.05 * rainfall
        + 0.03 * traffic
        + 0.08 * road_risk
        + 0.01 * distance
        - 0.15 * vehicle_speed
        + 8.0 * incident_count
        + 0.02 * terrain_risk
        - 5.0
    )
    delay_minutes = np.clip(base_delay + np.random.normal(0, 5, n_samples), 0, 180)
    delay_probability = np.clip(delay_minutes / 120.0, 0, 1)

    return pd.DataFrame({
        "rainfall": rainfall,
        "traffic": traffic,
        "road_risk": road_risk,
        "distance": distance,
        "vehicle_speed": vehicle_speed,
        "historical_travel_time": historical_travel_time,
        "incident_count": incident_count,
        "terrain_risk": terrain_risk,
        "delay_minutes": delay_minutes,
        "delay_probability": delay_probability,
    })


def train_delay_model() -> None:
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        from xgboost import XGBRegressor
    except ImportError:
        print("XGBoost not installed; delay model will use fallback.")
        return

    df = generate_synthetic_delay_data()
    X = df[_feature_names]
    y = df["delay_minutes"]

    model = XGBRegressor(
        n_estimators=80,
        max_depth=5,
        learning_rate=0.1,
        random_state=43,
    )
    model.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": _feature_names}, f)
    print(f"Delay XGBoost model saved to {MODEL_PATH}")


def load_delay_model() -> bool:
    global _delay_model
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                _delay_model = pickle.load(f)
            return True
        except Exception as e:
            print(f"Error loading delay model: {e}")
    return False


def _fallback_delay(features: Dict[str, float]) -> Dict[str, Any]:
    delay = (
        0.05 * features.get("rainfall", 0)
        + 0.03 * features.get("traffic", 0)
        + 0.08 * features.get("road_risk", 0)
        + 0.01 * features.get("distance", 0)
        - 0.15 * features.get("vehicle_speed", 40)
        + 8.0 * features.get("incident_count", 0)
    )
    delay = max(0.0, min(180.0, delay))
    prob = min(1.0, delay / 90.0)
    return {
        "predicted_delay_minutes": round(delay, 1),
        "delay_probability": round(prob, 2),
        "model": "fallback",
    }


def predict_delay(features: Dict[str, float]) -> Dict[str, Any]:
    global _delay_model
    if _delay_model is None:
        load_delay_model()

    if _delay_model is None:
        return _fallback_delay(features)

    model = _delay_model["model"]
    feat_names = _delay_model["features"]
    row = [[features.get(f, 0.0) for f in feat_names]]
    delay = float(model.predict(row)[0])
    delay = max(0.0, min(180.0, delay))
    prob = min(1.0, delay / 90.0)

    return {
        "predicted_delay_minutes": round(delay, 1),
        "delay_probability": round(prob, 2),
        "model": "xgboost",
    }
