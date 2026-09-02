import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import roads, vehicles, deliveries, incidents, weather, simulation, alerts, reset, routes, intelligence
from app.services.risk_service import recalculate_all_roads_risk
from app.ml.predictor import load_model
from app.ml.disruption_model import load_disruption_model, train_disruption_model
from app.ml.delay_model import load_delay_model, train_delay_model

app = FastAPI(
    title="NER-Sentinel AI API",
    description="AI-Powered Logistics, Accessibility & Emergency Response Intelligence Platform Backend",
    version="1.0.0"
)

# Allow CORS for React frontend (Vite defaults to localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(roads.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(deliveries.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(reset.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    # Load ML models (train XGBoost if missing)
    load_model()
    if not load_disruption_model():
        try:
            train_disruption_model()
            load_disruption_model()
        except Exception as e:
            print(f"Disruption model training skipped: {e}")
    if not load_delay_model():
        try:
            train_delay_model()
            load_delay_model()
        except Exception as e:
            print(f"Delay model training skipped: {e}")

    try:
        recalculate_all_roads_risk()
        print("Initial database recalculation completed successfully.")

        from app.services.gps_simulator import run_gps_simulation
        import asyncio
        asyncio.create_task(run_gps_simulation())
    except Exception as e:
        print(f"Error during startup recalculation: {e}")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "NER-Sentinel AI Backend API",
        "corridors": "Guwahati-Shillong-Silchar & Nagaon-Haflong-Silchar"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
