import React, { useState } from "react";
import { AlertCircle, CheckCircle, Clock, ShieldAlert } from "lucide-react";

export default function DeliveriesView({ deliveries }) {
  const [priorityFilter, setPriorityFilter] = useState("ALL");

  const filteredDeliveries = priorityFilter === "ALL" 
    ? deliveries 
    : deliveries.filter(d => d.priority === priorityFilter);

  const getPriorityBadgeStyle = (priority) => {
    switch (priority) {
      case "CRITICAL":
        return { backgroundColor: "rgba(244,63,94,0.2)", color: "var(--color-blocked)", borderColor: "rgba(244,63,94,0.4)" };
      case "HIGH":
        return { backgroundColor: "rgba(249,115,22,0.2)", color: "var(--color-high-risk)", borderColor: "rgba(249,115,22,0.4)" };
      case "MEDIUM":
        return { backgroundColor: "rgba(245,158,11,0.2)", color: "var(--color-moderate)", borderColor: "rgba(245,158,11,0.4)" };
      default:
        return { backgroundColor: "rgba(16,185,129,0.2)", color: "var(--color-open)", borderColor: "rgba(16,185,129,0.4)" };
    }
  };

  return (
    <div style={{ padding: 24, overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: "bold", color: "#00f2fe" }}>CARGO DELIVERY ORDERS</h2>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          AI-driven delivery failure risk and ETA predictions based on dynamic weather and landslides.
        </p>
      </div>

      <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 8 }}>
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "NORMAL"].map(p => (
              <button 
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`btn ${priorityFilter === p ? 'btn-primary' : 'btn-outline'}`}
                style={{ padding: "6px 12px", fontSize: 12 }}
              >
                {p}
              </button>
            ))}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Showing <b>{filteredDeliveries.length}</b> of <b>{deliveries.length}</b> orders
          </div>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(0, 242, 254, 0.2)", color: "#00f2fe", height: "40px" }}>
              <th style={{ padding: 8 }}>Order ID</th>
              <th style={{ padding: 8 }}>Cargo Description</th>
              <th style={{ padding: 8 }}>Priority</th>
              <th style={{ padding: 8 }}>Weight (kg)</th>
              <th style={{ padding: 8 }}>Assigned Vehicle</th>
              <th style={{ padding: 8 }}>ETA (Original)</th>
              <th style={{ padding: 8 }}>On-Time Probability</th>
              <th style={{ padding: 8 }}>Risk Level</th>
              <th style={{ padding: 8 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredDeliveries.map(d => {
              const pStyle = getPriorityBadgeStyle(d.priority);
              
              return (
                <tr 
                  key={d.delivery_id} 
                  style={{ 
                    borderBottom: "1px solid rgba(255, 255, 255, 0.05)", 
                    height: "50px"
                  }}
                >
                  <td style={{ padding: 8, fontWeight: "bold", fontFamily: "Orbitron" }}>
                    {d.delivery_id}
                  </td>
                  <td style={{ padding: 8 }}>
                    <div>
                      <div>{d.cargo}</div>
                      {d.delay_reason && (
                        <div style={{ fontSize: 10, color: "var(--color-blocked)", fontStyle: "italic" }}>
                          Reason: {d.delay_reason}
                        </div>
                      )}
                    </div>
                  </td>
                  <td style={{ padding: 8 }}>
                    <span 
                      className="badge" 
                      style={{ 
                        ...pStyle, 
                        border: "1px solid"
                      }}
                    >
                      {d.priority}
                    </span>
                  </td>
                  <td style={{ padding: 8, fontFamily: "Orbitron" }}>
                    {d.weight_kg.toLocaleString()} kg
                  </td>
                  <td style={{ padding: 8, fontWeight: "bold", fontFamily: "Orbitron", color: "#38bdf8" }}>
                    {d.vehicle_id}
                  </td>
                  <td style={{ padding: 8 }}>
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <span style={{ fontFamily: "Orbitron", fontWeight: "bold" }}>
                        {d.eta_str}
                      </span>
                      <span style={{ fontSize: 10, color: "var(--text-muted)", textDecoration: d.eta_str !== d.original_eta_str ? "line-through" : "none" }}>
                        ({d.original_eta_str})
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: 8, fontWeight: "bold", fontFamily: "Orbitron", color: d.on_time_probability > 60 ? "var(--color-open)" : "var(--color-critical)" }}>
                    {d.on_time_probability}%
                  </td>
                  <td style={{ padding: 8, fontWeight: "bold", color: d.delivery_risk_pct > 60 ? "var(--color-blocked)" : "var(--color-open)" }}>
                    {d.delivery_risk_pct}%
                  </td>
                  <td style={{ padding: 8 }}>
                    <span className={`badge badge-${d.status.toLowerCase()}`}>
                      {d.status}
                    </span>
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
