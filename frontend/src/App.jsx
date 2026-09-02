import React, { lazy, Suspense, useState, useEffect } from "react";
const ControlTower = lazy(() => import("./components/ControlTower"));
const VehiclesView = lazy(() => import("./components/VehiclesView"));
const DeliveriesView = lazy(() => import("./components/DeliveriesView"));
const IncidentsView = lazy(() => import("./components/IncidentsView"));
const SimulationView = lazy(() => import("./components/SimulationView"));
import { AlertCircle, RotateCcw, AlertTriangle, ShieldCheck } from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

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
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [isLoadingData, setIsLoadingData] = useState(true);

  // Fetch all database states from FastAPI backend
  const refreshAllData = async () => {
    try {
      const endpoints = ["roads", "vehicles", "deliveries", "incidents", "alerts", "weather"];
      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(`${API_BASE_URL}/api/${endpoint}`))
      );

      if (responses.some(response => !response.ok)) {
        throw new Error("One or more API requests failed");
      }

      const [roadsData, vehiclesData, deliveriesData, incidentsData, alertsData, weatherData] =
        await Promise.all(responses.map(response => response.json()));

      setRoads(roadsData);
      setVehicles(vehiclesData);
      setDeliveries(deliveriesData);
      setIncidents(incidentsData);
      setAlerts(alertsData);
      setWeather(weatherData);
      setConnectionStatus("connected");
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      setConnectionStatus("offline");
    } finally {
      setIsLoadingData(false);
    }
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
    
    fetch(`${API_BASE_URL}/api/reset`, { method: "POST" })
      .then(res => res.json())
      .then(data => {
        refreshAllData();
        setResetMessage("✓ Seed data restored.");
        setTimeout(() => setResetMessage(""), 3000);
      })
      .catch(err => {
        console.error(err);
        setConnectionStatus("offline");
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

    fetch(`${API_BASE_URL}/api/incidents`, {
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

          <div className={`live-indicator status-${connectionStatus}`} aria-live="polite">
            <div className="pulse-dot"></div>
            <span>{connectionStatus === "connected" ? "BACKEND CONNECTED" : connectionStatus === "offline" ? "BACKEND OFFLINE" : "CONNECTING..."}</span>
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
      {connectionStatus === "offline" && (
        <div className="connection-banner" role="alert">
          <AlertCircle size={16} />
          <span>Dashboard data is unavailable. Start the FastAPI backend, then retry.</span>
          <button className="btn btn-outline" onClick={refreshAllData} disabled={isLoadingData}>
            RETRY CONNECTION
          </button>
        </div>
      )}
      <Suspense fallback={<div style={{ padding: 24, color: "var(--text-secondary)" }}>Loading view...</div>}>
        {renderActiveContent()}
      </Suspense>
    </div>
  );
}
