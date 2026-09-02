# NER-Sentinel AI

AI-Powered Logistics, Accessibility & Emergency Response Intelligence Platform for Northeast India.

## Overview

NER-Sentinel AI is a real-time monitoring and optimization system for logistics and emergency response across critical corridors in Northeast India, specifically focusing on:

- **Guwahati-Shillong-Silchar Corridor** (NH-6)
- **Nagaon-Haflong-Silchar Corridor**

The platform uses machine learning to predict road risks, optimize routes during incidents, and ensure timely delivery of essential supplies during monsoon emergencies.

## What This Project Does

NER-Sentinel AI is a local demonstration of an emergency logistics control tower. It models a transport network containing road segments, vehicles, deliveries, weather observations, and field incidents. The application helps an operator answer three questions:

1. Which roads and deliveries are currently at risk?
2. What happens when a road is blocked by a landslide, flood, or another incident?
3. Which vehicles, deliveries, and routes should be prioritized during an emergency?

The system is designed around a repeatable demo workflow rather than a live production deployment. The included data is seeded locally, the ML training data is synthetic, route choices are deterministic, and vehicle telemetry changes only when an API request updates it.

## How the System Works

The application has four cooperating layers:

### 1. React control tower

The frontend in `frontend/src` is a Vite-powered React application with five views:

- **Control Tower** shows KPI cards, the Leaflet map, road risk colors, vehicle and facility markers, critical shipments, and alerts.
- **Vehicles** lists fleet vehicles and lets the operator locate a vehicle on the map.
- **Deliveries** filters shipments by priority and shows status, ETA, and delivery risk.
- **Field Officers** submits a road incident, including incident type, severity, location, description, and an optional photo URL.
- **Simulator** compares a baseline network with an AI-optimized network under scenarios such as heavy rain, flood, landslide, or storm.

The frontend polls the API every 1.5 seconds. It does not contain the main business rules; buttons send requests to FastAPI and then refresh the displayed state. The map uses OpenStreetMap tiles and does not require an API key for local development.

### 2. FastAPI service

The backend exposes REST endpoints under `/api`. Routers separate the public API by domain: roads, vehicles, deliveries, incidents, weather, alerts, routes, simulation, and reset. Services contain the calculations and state changes behind those endpoints.

For the working demo shown by the frontend, start `backend/app/main.py`. It uses the CSV-backed implementation in `database.py` and the original service modules. The application enables CORS so the Vite frontend at `http://localhost:5173` can call the API at `http://127.0.0.1:8000`.

### 3. Local data and ML risk engine

The demo data is stored in CSV files under `backend/data`. Roads include geometry and terrain-related attributes; vehicles include positions and routes; deliveries include cargo, priority, and ETA information; weather and incidents influence risk calculations.

The ML pipeline in `backend/app/ml` trains a Random Forest classifier on generated examples. The predictor converts road and weather inputs into a disruption probability, accessibility score, risk level, and contributing factor explanations. If trained model files are unavailable, the predictor has a deterministic fallback calculation, so the demo can still run.

### 4. Operational cascade

When an operator reports or simulates an incident, the backend performs a cascade:

1. Save the incident.
2. Block or downgrade the affected road based on incident type and severity.
3. Recalculate road risk and accessibility.
4. Find vehicles and deliveries affected by the road condition.
5. Select alternate routes where available.
6. Recalculate ETA and delivery risk.
7. Generate alerts for blocked roads, rerouting, delays, and critical shipments.

The **Simulate Landslide** button demonstrates this flow for road `R-204`. **Emergency Mode** changes prioritization so critical medicine, food, and water deliveries receive preference. **Reset Demo** restores the baseline seed data.

## Backend Implementations

This repository contains two backend generations. They are separate implementations and should not be mixed when running the application:

| Entry point               | Storage                | Status                                | Command                  |
| ------------------------- | ---------------------- | ------------------------------------- | ------------------------ |
| `backend/app/main.py`     | CSV files              | Current frontend-compatible demo path | `python app/main.py`     |
| `backend/app/main_new.py` | SQLAlchemy with SQLite | Newer service/API implementation      | `python app/main_new.py` |

The `*_new.py` routers and services add database models, emergency endpoints, richer risk and impact services, and additional demo routes. However, the existing React screens still expect several field names and response shapes from the CSV-backed API. Use `main.py` for the complete workflow shown in the screenshots unless the frontend contracts are updated for `main_new.py`.

The newer implementation requires an explicit seed step on a fresh database:

```bash
cd backend
python -m app.seed
python app/main_new.py
```

It creates a local SQLite database named `ner_sentinel.db`; no external database or secret key is required.

## Risk, Routing, and Simulation Details

- Road risk combines weather, terrain, road condition, traffic, flood risk, landslide history, and active incident severity.
- A blocked road has zero accessibility and maximum risk in the service layer.
- Delivery risk considers route condition, road risk, priority, and ETA impact.
- Route optimization currently uses predefined corridor alternatives and local scoring. It does not call Google Maps, Mapbox, OpenRouteService, or another external routing API.
- Simulation runs simplified baseline and optimized comparisons using deterministic delay and route assumptions. It is intended for decision-support demonstration, not validated forecasting.
- Telemetry is represented by stored coordinates and API updates; there is no GPS device stream or background vehicle movement process.

## Secrets and External Services

No API keys, cloud credentials, weather service keys, map keys, or LLM keys are required by the current codebase. The frontend map uses OpenStreetMap tiles. All backend data, route logic, and risk calculations run locally.

If a commercial map or live weather provider is added later, its key should be supplied through environment configuration and never committed to Git. A Vite browser variable such as `VITE_MAP_API_KEY` is visible to users, so it must be restricted and treated as a public client credential.

## Features

- **Real-time Road Monitoring**: Track road status, accessibility scores, and risk levels across multiple corridors
- **AI-Powered Risk Prediction**: ML models predict landslide and flood risks based on weather and terrain data
- **Dynamic Route Optimization**: Automatic rerouting of vehicles during incidents (landslides, floods, etc.)
- **Emergency Response Mode**: Prioritizes medicine, food, and water deliveries during crises
- **Live Telemetry**: Real-time vehicle tracking with GPS positions and ETA calculations
- **Incident Management**: Field officers can report incidents that trigger cascading network optimizations
- **Simulation Engine**: Test scenarios and compare baseline vs optimized logistics outcomes
- **Interactive GIS Map**: Visualize roads, vehicles, incidents, and delivery routes on an interactive map

## Tech Stack

### Backend

- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation
- **scikit-learn**: Machine learning for risk prediction
- **pandas/numpy**: Data processing

### Frontend

- **React 19**: UI framework
- **Vite**: Build tool and dev server
- **Leaflet**: Interactive maps
- **React Leaflet**: React integration for Leaflet
- **Lucide React**: Icon library
- **Recharts**: Data visualization

## Project Structure

```
NER-Sentinel-AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # CSV-based data storage
│   │   ├── models/              # Pydantic models
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Business logic
│   │   └── ml/                  # Machine learning models
│   ├── data/                    # CSV seed data
│   └── test_api.py              # End-to-end API tests
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main React component
│   │   ├── components/          # React components
│   │   └── main.jsx             # React entry point
│   └── package.json
└── requirements.txt
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory**

   ```bash
   cd backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**

   ```bash
   pip install -r ../requirements.txt
   ```

5. **Train ML models** (first time only)

   ```bash
   python app/ml/train_models.py
   ```

6. **Start the backend server**
   ```bash
   python app/main.py
   ```
   The API will be available at `http://127.0.0.1:8000`

### Frontend Setup

1. **Navigate to frontend directory**

   ```bash
   cd frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:5173`

## Running the Application

1. Start the backend server (from backend directory):

   ```bash
   python app/main.py
   ```

2. Start the frontend server (from frontend directory):

   ```bash
   npm run dev
   ```

3. Open your browser to `http://localhost:5173`

## API Endpoints

### Core Endpoints

- `GET /` - Health check
- `GET /api/roads` - Get all roads with status and risk scores
- `GET /api/vehicles` - Get all vehicles with positions and routes
- `GET /api/deliveries` - Get all deliveries with risk percentages
- `GET /api/incidents` - Get all reported incidents
- `GET /api/alerts` - Get system alerts
- `GET /api/weather` - Get current weather conditions

### Action Endpoints

- `POST /api/incidents` - Report a new incident (triggers cascade optimization)
- `POST /api/simulation/run` - Run simulation scenarios
- `POST /api/reset` - Reset database to initial seed state
- `GET /api/routes` - Get optimized route alternatives

## Testing

### Backend API Tests

Run the end-to-end API test suite:

```bash
cd backend
python test_api.py
```

This will test:

- Health check endpoint
- Roads and vehicles data loading
- Incident registration and cascade effects
- Automatic rerouting verification
- Simulation scenarios
- Database reset functionality

## Demo Features

### Simulate Landslide

Click the "Simulate Landslide" button in the Control Tower to:

- Trigger a landslide incident on R-204 (Guwahati-Shillong Highway)
- Watch automatic road blockage and vehicle rerouting
- Observe real-time risk score updates
- See delivery risk adjustments as vehicles take alternate routes

### Emergency Mode

Toggle emergency mode to prioritize essential supplies (medicine, food, water) during monsoon crises across East Khasi Hills, Cachar & West Jaintia Districts.

### Reset Demo

Use the "RESET DEMO" button to restore the database to its initial seed state for repeated testing.

## Development

### Adding New Roads

Edit `backend/app/database.py` and add road definitions to `SEED_ROADS` list.

### Modifying ML Models

Update training data and model parameters in `backend/app/ml/train_models.py`.

### Adding New UI Components

Create new components in `frontend/src/components/` and import them in `App.jsx`.

## License

This project is developed for logistics and emergency response optimization in Northeast India.

## Contact

For questions or contributions, please refer to the project repository.
