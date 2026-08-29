from fastapi import APIRouter
from pydantic import BaseModel
from app.services.simulation_service import run_network_simulation
from app.models.models import SimulationResult

router = APIRouter(prefix="/simulation", tags=["simulation"])

class SimulationRequestSchema(BaseModel):
    scenario: str
    rainfall_mm: float

@router.post("/run", response_model=SimulationResult)
def run_simulation(schema: SimulationRequestSchema):
    res_dict = run_network_simulation(schema.scenario, schema.rainfall_mm)
    return SimulationResult(**res_dict)
