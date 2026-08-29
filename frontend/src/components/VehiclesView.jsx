import React, { useState } from "react";
import { Truck, MapPin, Compass, ShieldAlert, Award } from "lucide-react";

export default function VehiclesView({ vehicles, onSelectVehicle }) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredVehicles = vehicles.filter(v => 
    v.vehicle_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.cargo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.destination.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ padding: 24, overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: "bold", color: "#00f2fe" }}>VEHICLE FLEET INTELLIGENCE</h2>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Real-time GPS tracking and dynamic routing compliance tracking.
        </p>
      </div>

      <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <input 
            type="text" 
            placeholder="Search vehicle ID, cargo, or destination..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-control"
            style={{ width: "350px" }}
          />
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Showing <b>{filteredVehicles.length}</b> of <b>{vehicles.length}</b> vehicles
          </div>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(0, 242, 254, 0.2)", color: "#00f2fe", height: "40px" }}>
              <th style={{ padding: 8 }}>Vehicle ID</th>
              <th style={{ padding: 8 }}>Cargo</th>
              <th style={{ padding: 8 }}>Origin → Destination</th>
              <th style={{ padding: 8 }}>Telemetry Speed</th>
              <th style={{ padding: 8 }}>ETA</th>
              <th style={{ padding: 8 }}>Delivery Risk</th>
              <th style={{ padding: 8 }}>Status</th>
              <th style={{ padding: 8, textAlign: "center" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredVehicles.map(veh => {
              const isCritical = veh.cargo.toLowerCase().includes("medicine") || veh.cargo.toLowerCase().includes("oxygen");
              
              return (
                <tr 
                  key={veh.vehicle_id} 
                  style={{ 
                    borderBottom: "1px solid rgba(255, 255, 255, 0.05)", 
                    height: "50px",
                    background: isCritical ? "rgba(0, 242, 254, 0.02)" : "transparent"
                  }}
                >
                  <td style={{ padding: 8, fontWeight: "bold", fontFamily: "Orbitron" }}>
                    {veh.vehicle_id}
                  </td>
                  <td style={{ padding: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {isCritical ? <Award size={14} color="#00f2fe" /> : <Truck size={14} />}
                      {veh.cargo}
                    </div>
                  </td>
                  <td style={{ padding: 8 }}>
                    {veh.origin} → <span style={{ color: "#38bdf8" }}>{veh.destination}</span>
                  </td>
                  <td style={{ padding: 8, fontFamily: "Orbitron" }}>
                    {veh.speed_kmh} km/h
                  </td>
                  <td style={{ padding: 8, fontFamily: "Orbitron" }}>
                    {veh.eta_str} {veh.status === "BLOCKED" && <span style={{ color: "var(--color-blocked)" }}>(Stuck)</span>}
                  </td>
                  <td style={{ padding: 8, fontWeight: "bold", color: veh.delivery_risk_pct > 60 ? "var(--color-blocked)" : "var(--color-open)" }}>
                    {veh.delivery_risk_pct}%
                  </td>
                  <td style={{ padding: 8 }}>
                    <span className={`badge badge-${veh.status.toLowerCase()}`}>
                      {veh.status}
                    </span>
                  </td>
                  <td style={{ padding: 8, textAlign: "center" }}>
                    <button 
                      onClick={() => onSelectVehicle(veh)}
                      className="btn btn-primary"
                      style={{ padding: "4px 10px", fontSize: 11 }}
                    >
                      <MapPin size={12} />
                      LOCATE
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
