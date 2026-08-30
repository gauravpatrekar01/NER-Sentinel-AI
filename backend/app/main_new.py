import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database_sqlalchemy import init_db
from app.routers import (
    roads_new as roads, 
    vehicles_new as vehicles, 
    deliveries_new as deliveries, 
    incidents_new as incidents, 
    weather_new as weather, 
    simulation_new as simulation, 
    alerts_new as alerts, 
    reset_new as reset, 
    routes_new as routes,
    emergency_new as emergency,
    demo
)
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from app.ml.predictor import load_model
from app.database_sqlalchemy import SessionLocal

app = FastAPI(
    title="NER-Sentinel AI API",
    description="AI-Powered Logistics, Accessibility & Emergency Response Intelligence Platform Backend",
    version="2.0.0"
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
app.include_router(emergency.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    # Initialize database
    init_db()
    
    # Load ML Model
    load_model()
    
    # Trigger initial risk and status calculations to populate database fields
    try:
        db = SessionLocal()
        road_risk_service = RoadRiskService(db)
        delivery_risk_service = DeliveryRiskService(db)
        
        road_risk_service.recalculate_all_roads_risk()
        delivery_risk_service.recalculate_all_deliveries_risk()
        
        db.close()
        print("Initial database recalculation completed successfully.")
    except Exception as e:
        print(f"Error during startup recalculation: {e}")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "NER-Sentinel AI Backend API v2.0",
        "corridors": "Guwahati-Shillong-Silchar & Nagaon-Haflong-Silchar",
        "database": "SQLAlchemy",
        "features": [
            "Road risk assessment with ML",
            "Delivery risk calculation",
            "Incident management and cascading",
            "Impact analysis",
            "Route optimization",
            "ETA calculation",
            "Alert generation",
            "Emergency mode",
            "Simulation and what-if analysis",
            "Demo scenarios"
        ]
    }

if __name__ == "__main__":
    uvicorn.run("app.main_new:app", host="0.0.0.0", port=8000, reload=True)
