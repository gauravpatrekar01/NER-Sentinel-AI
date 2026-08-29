import React, { useState, useEffect } from "react";
import ControlTower from "./components/ControlTower";
import VehiclesView from "./components/VehiclesView";
import DeliveriesView from "./components/DeliveriesView";
import IncidentsView from "./components/IncidentsView";
import SimulationView from "./components/SimulationView";
import { AlertCircle, RotateCcw, AlertTriangle, ShieldCheck } from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState("control-tower");
  const [roads, setRoads] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [weather, setWeather] = useState({
    rainfall_mm: 142.0,
    forecast: "Heavy Rain",
    visibility_km: 3.0,
    weather_risk_level: "HIGH"
  });
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [resetMessage, setResetMessage] = useState("");

  // Fetch all database states from FastAPI backend
  const refreshAllData = () => {
    fetch("http://127.0.0.1:8000/api/roads")
      .then(res => res.json())
      .then(setRoads)
      .catch(err => console.error("Error loading roads:", err));

    fetch("http://127.0.0.1:8000/api/vehicles")
      .then(res => res.json())
      .then(setVehicles)
      .catch(err => console.error("Error loading vehicles:", err));

    fetch("http://127.0.0.1:8000/api/deliveries")
      .then(res => res.json())
      .then(setDeliveries)
      .catch(err => console.error("Error loading deliveries:", err));

    fetch("http://127.0.0.1:8000/api/incidents")
      .then(res => res.json())
      .then(setIncidents)
      .catch(err => console.error("Error loading incidents:", err));

    fetch("http://127.0.0.1:8000/api/alerts")
      .then(res => res.json())
      .then(setAlerts)
      .catch(err => console.error("Error loading alerts:", err));

    fetch("http://127.0.0.1:8000/api/weather")
      .then(res => res.json())
      .then(setWeather)
      .catch(err => console.error("Error loading weather:", err));
  };

  // Poll database updates every 1500ms
  useEffect(() => {
    refreshAllData();
    const interval = setInterval(refreshAllData, 1500);
    return () => clearInterval(interval);
  }, []);

  // Action: Reset Demo State
  const handleResetDemo = () => {
    setResetMessage("Resetting network state...");
    setEmergencyMode(false);
    
    fetch("http://127.0.0.1:8000/api/reset", { method: "POST" })
      .then(res => res.json())
      .then(data => {
        refreshAllData();
        setResetMessage("✓ Seed data restored.");
        setTimeout(() => setResetMessage(""), 3000);
      })
      .catch(err => {
        console.error(err);
        setResetMessage("Reset failed. Verify backend.");
      });
  };

  // Action: Trigger Simulated Landslide (demo sequence trigger)
  const handleSimulateLandslide = () => {
    const payload = {
      road_id: "R-204",
      lat: 25.9015,
      lon: 91.8800,
      type: "Landslide",
      severity: "CRITICAL",
      description: "Monsoon triggered rockfall block at NH-6 Guwahati-Shillong corridor segment R-204.",
      photo_url: "https://images.unsplash.com/photo-1594897030264-ab7d87efc473?auto=format&fit=crop&w=400&q=80",
      optimize_immediately: true
    };

    fetch("http://127.0.0.1:8000/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(() => {
        refreshAllData();
      })
      .catch(err => console.error("Error simulating landslide:", err));
  };

  // Action: Toggle Emergency Mode
  const handleToggleEmergency = () => {
    setEmergencyMode(prev => !prev);
    // Refresh to trigger optimized calculations
    setTimeout(refreshAllData, 200);
  };

  // Callback to locate vehicle on GIS map
  const handleLocateVehicle = (veh) => {
    setSelectedVehicle(veh);
    setActiveTab("control-tower");
  };

  // Render navigation tab views
  const renderActiveContent = () => {
    switch (activeTab) {
      case "vehicles":
        return <VehiclesView vehicles={vehicles} onSelectVehicle={handleLocateVehicle} />;
      case "deliveries":
        return <DeliveriesView deliveries={deliveries} />;
      case "incidents":
        return <IncidentsView roads={roads} onSubmitIncidentSuccess={refreshAllData} />;
      case "simulation":
        return <SimulationView />;
      case "control-tower":
      default:
        return (
          <ControlTower
            roads={roads}
            vehicles={vehicles}
            deliveries={deliveries}
            incidents={incidents}
            alerts={alerts}
            weather={weather}
            emergencyMode={emergencyMode}
            onSimulateLandslide={handleSimulateLandslide}
            onToggleEmergency={handleToggleEmergency}
            onSelectVehicle={handleLocateVehicle}
          />
        );
    }
  };

  // Block count
  const isBlocked = roads.some(r => r.status === "BLOCKED");

  return (
    <div className="app-container">
      
      {/* Header bar */}
      <header className="header-bar">
        <div className="logo-section">
          <div className="logo-dot"></div>
          <div>
            <h1 className="header-title">NER-SENTINEL AI</h1>
            <div className="header-subtitle">Accessibility & Logistics Control Tower</div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-links">
          <button 
            className={`nav-item ${activeTab === 'control-tower' ? 'active' : ''}`}
            onClick={() => setActiveTab("control-tower")}
          >
            Control Tower
          </button>
          <button 
            className={`nav-item ${activeTab === 'vehicles' ? 'active' : ''}`}
            onClick={() => setActiveTab("vehicles")}
          >
            Vehicles
          </button>
          <button 
            className={`nav-item ${activeTab === 'deliveries' ? 'active' : ''}`}
            onClick={() => setActiveTab("deliveries")}
          >
            Deliveries
          </button>
          <button 
            className={`nav-item ${activeTab === 'incidents' ? 'active' : ''}`}
            onClick={() => setActiveTab("incidents")}
          >
            Field Officers
          </button>
          <button 
            className={`nav-item ${activeTab === 'simulation' ? 'active' : ''}`}
            onClick={() => setActiveTab("simulation")}
          >
            Simulator
          </button>
        </nav>

        {/* Control and Reset status */}
        <div className="system-status">
          {resetMessage && (
            <span style={{ color: "#00f2fe", fontSize: 12, fontWeight: "bold" }}>
              {resetMessage}
            </span>
          )}
          
          <button 
            onClick={handleResetDemo} 
            className="btn btn-outline" 
            style={{ padding: "6px 12px", fontSize: 12, display: "flex", gap: 6, alignItems: "center" }}
            title="Reset Database Seed"
          >
            <RotateCcw size={14} />
            RESET DEMO
          </button>

          <div className="live-indicator">
            <div className="pulse-dot"></div>
            <span>LIVE telemetry</span>
          </div>
        </div>
      </header>

      {/* Emergency Mode Notification Banner */}
      {emergencyMode && (
        <div style={{ 
          backgroundColor: "#d97706", 
          color: "#04060f", 
          padding: "6px 24px", 
          textAlign: "center", 
          fontWeight: "bold", 
          fontSize: 12,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          boxShadow: "0 4px 10px rgba(0,0,0,0.3)",
          zIndex: 90
        }}>
          <AlertTriangle size={16} />
          <span>EMERGENCY MONSOON LOGISTICS ACTIVATED — Prioritizing Medicine (1), Food (2) and Water (3) across East Khasi Hills, Cachar & West Jaintia Districts.</span>
        </div>
      )}

      {/* Main View Area */}
      {renderActiveContent()}
    </div>
  );
}
