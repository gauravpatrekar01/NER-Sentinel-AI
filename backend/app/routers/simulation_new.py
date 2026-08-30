from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db
from app.services.simulation_service_new import SimulationService
from pydantic import BaseModel

router = APIRouter(prefix="/simulation", tags=["simulation"])

class SimulationRequestSchema(BaseModel):
    scenario: str
    rainfall_mm: float = None

@router.post("/run")
def run_simulation(schema: SimulationRequestSchema, db: Session = Depends(get_db)):
    simulation_service = SimulationService(db)
    result = simulation_service.run_scenario(schema.scenario, schema.rainfall_mm)
    return result

@router.post("/landslide-demo")
def run_landslide_demo(db: Session = Depends(get_db)):
    simulation_service = SimulationService(db)
    result = simulation_service.run_landslide_demo()
    return result
