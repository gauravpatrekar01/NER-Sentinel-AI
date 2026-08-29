# NER-Sentinel AI

AI-Powered Logistics, Accessibility & Emergency Response Intelligence Platform for Northeast India.

## Overview

NER-Sentinel AI is a real-time monitoring and optimization system for logistics and emergency response across critical corridors in Northeast India, specifically focusing on:
- **Guwahati-Shillong-Silchar Corridor** (NH-6)
- **Nagaon-Haflong-Silchar Corridor**

The platform uses machine learning to predict road risks, optimize routes during incidents, and ensure timely delivery of essential supplies during monsoon emergencies.

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
