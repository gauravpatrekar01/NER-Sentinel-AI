import React, { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Play, TrendingUp, Sliders, ShieldCheck, AlertTriangle } from "lucide-react";

export default function SimulationView() {
  const [scenario, setScenario] = useState("heavy_rain");
  const [rainfall, setRainfall] = useState(140);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleRunSimulation = () => {
    setLoading(true);
    
    fetch("http://127.0.0.1:8000/api/simulation/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario, rainfall_mm: parseFloat(rainfall) })
    })
      .then(res => res.json())
      .then(data => {
        setResults(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  const [eventLoading, setEventLoading] = useState(false);
  const handleTriggerEvent = (eventType) => {
    setEventLoading(true);
    fetch("http://127.0.0.1:8000/api/simulation/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType })
    })
      .then(res => res.json())
      .then(() => setEventLoading(false))
      .catch(err => {
        console.error(err);
        setEventLoading(false);
      });
  };

  // Format data for Recharts chart
  const getChartData = () => {
    if (!results) return [];
    return [
      {
        name: "Delayed Orders",
        "Without AI": results.baseline_delayed_count,
        "With NER-Sentinel": results.optimized_delayed_count
      },
      {
        name: "Avg Delay (hrs)",
        "Without AI": results.baseline_avg_delay_hours,
        "With NER-Sentinel": results.optimized_avg_delay_hours
      },
      {
        name: "Critical Affected",
        "Without AI": results.baseline_critical_affected,
        "With NER-Sentinel": results.optimized_critical_affected
      }
    ];
  };

  return (
    <div style={{ padding: 24, overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: "bold", color: "#00f2fe" }}>DECISION SCENARIO SIMULATOR</h2>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Run what-if scenario simulations to evaluate NER logistics network resilience under extreme climate conditions.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "350px 1fr", gap: 24 }}>
        
        {/* Input Parameters Controls */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 className="card-title">
            <span>Simulation Parameters</span>
            <Sliders size={16} />
          </h3>

          <div className="form-group">
            <label>Disaster Scenario</label>
            <select value={scenario} onChange={(e) => setScenario(e.target.value)} className="form-control">
              <option value="heavy_rain">Heavy Monsoon Rainfall</option>
              <option value="landslide">Landslide on NH-6 Corridor</option>
              <option value="flood">Flash Floods / Water logging</option>
              <option value="storm">Severe Cyclonic Storm</option>
            </select>
          </div>

          <div className="form-group">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <label>Rainfall Intensity</label>
              <span style={{ fontSize: 12, fontWeight: "bold", color: "#00f2fe" }}>{rainfall} mm</span>
            </div>
            <input 
              type="range" 
              min="0" 
              max="250" 
              value={rainfall} 
              onChange={(e) => setRainfall(e.target.value)}
              style={{ width: "100%", accentColor: "#00f2fe", cursor: "pointer", marginTop: 8 }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-muted)", marginTop: 4 }}>
              <span>0mm (Dry)</span>
              <span>120mm (Heavy)</span>
              <span>250mm (Severe)</span>
            </div>
          </div>

          <div className="form-group">
            <label>Active Fleet Vehicles (Simulated)</label>
            <input type="text" className="form-control" value="37 (Standard seed)" disabled />
          </div>

          <div className="form-group">
            <label>Total Scheduled Orders</label>
            <input type="text" className="form-control" value="124 (Standard seed)" disabled />
          </div>

          <button 
            onClick={handleRunSimulation} 
            className="btn btn-primary" 
            style={{ marginTop: 10 }}
            disabled={loading}
          >
            <Play size={16} fill="currentColor" />
            {loading ? "EXECUTING NETWORK RUNS..." : "RUN SIMULATION"}
          </button>
        </div>

        {/* Real-Time System Triggers */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 className="card-title">
            <span>Real-Time System Triggers</span>
            <AlertTriangle size={16} />
          </h3>
          <p style={{ fontSize: 11, color: "var(--text-secondary)" }}>
            Inject real-time events into the live network. Watch as the decision engine reroutes vehicles in the Control Tower.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <button className="btn btn-outline" onClick={() => handleTriggerEvent("NORMAL")} disabled={eventLoading} style={{ fontSize: 11 }}>Clear Weather</button>
            <button className="btn btn-outline" onClick={() => handleTriggerEvent("HEAVY_RAIN")} disabled={eventLoading} style={{ fontSize: 11 }}>Heavy Rain</button>
            <button className="btn btn-outline" onClick={() => handleTriggerEvent("EXTREME_RAIN")} disabled={eventLoading} style={{ fontSize: 11, color: "var(--color-warning)", borderColor: "var(--color-warning)" }}>Extreme Storm</button>
            <button className="btn btn-outline" onClick={() => handleTriggerEvent("FLOOD")} disabled={eventLoading} style={{ fontSize: 11, color: "var(--color-critical)", borderColor: "var(--color-critical)" }}>Flash Flood</button>
            <button className="btn btn-outline" onClick={() => handleTriggerEvent("LANDSLIDE")} disabled={eventLoading} style={{ fontSize: 11, color: "var(--color-critical)", borderColor: "var(--color-critical)" }}>Landslide Block</button>
            <button className="btn btn-outline" onClick={() => handleTriggerEvent("EMERGENCY_MODE")} disabled={eventLoading} style={{ fontSize: 11, color: "var(--color-critical)", borderColor: "var(--color-critical)" }}>Emergency Mode</button>
          </div>
          
          {eventLoading && <div style={{ fontSize: 11, color: "var(--color-warning)", textAlign: "center", marginTop: 8 }}>Injecting event...</div>}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Results Analysis Panel */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: 16, minHeight: "450px" }}>
          <h3 className="card-title">
            <span>Simulation Analysis Output</span>
            <TrendingUp size={16} />
          </h3>

          {!results ? (
            <div style={{ display: "flex", flex: 1, flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", gap: 12 }}>
              <ShieldCheck size={48} style={{ opacity: 0.3 }} />
              <div style={{ fontSize: 14 }}>Set parameters and trigger Run Simulation.</div>
              <div style={{ fontSize: 11 }}>Calculates logistics network runs both with and without AI routing optimizations.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20, flex: 1 }}>
              
              {/* Metric Comparison Cards */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                
                {/* Baseline Cards */}
                <div style={{ padding: 14, background: "rgba(244,63,94,0.03)", border: "1px solid rgba(244,63,94,0.15)", borderRadius: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: "bold", color: "var(--color-blocked)", marginBottom: 8, textTransform: "uppercase" }}>
                    Baseline Regime (Without AI)
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Delayed Deliveries</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron" }}>{results.baseline_delayed_count}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Avg Delay (hours)</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron" }}>{results.baseline_avg_delay_hours} hrs</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Critical Delayed</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron", color: "var(--color-critical)" }}>{results.baseline_critical_affected}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>On-Time Rate</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron" }}>{results.baseline_on_time_pct}%</div>
                    </div>
                  </div>
                </div>

                {/* AI Optimized Cards */}
                <div style={{ padding: 14, background: "rgba(16,185,129,0.03)", border: "1px solid rgba(16,185,129,0.15)", borderRadius: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: "bold", color: "var(--color-open)", marginBottom: 8, textTransform: "uppercase" }}>
                    NER-Sentinel Regime (With AI)
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Delayed Deliveries</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron" }}>{results.optimized_delayed_count}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Avg Delay (hours)</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron" }}>{results.optimized_avg_delay_hours} hrs</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Critical Delayed</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron", color: "var(--color-open)" }}>{results.optimized_critical_affected}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>On-Time Rate</div>
                      <div style={{ fontSize: 24, fontWeight: "bold", fontFamily: "Orbitron", color: "var(--color-open)" }}>{results.optimized_on_time_pct}%</div>
                    </div>
                  </div>
                </div>

              </div>

              {/* Chart */}
              <div style={{ flex: 1, height: "240px", minHeight: "240px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={getChartData()}
                    margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" stroke="var(--text-secondary)" fontSize={11} />
                    <YAxis stroke="var(--text-secondary)" fontSize={11} />
                    <Tooltip 
                      contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border-glow)", color: "var(--text-primary)" }} 
                      itemStyle={{ color: "var(--text-primary)" }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Without AI" fill="var(--color-blocked)" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="With NER-Sentinel" fill="var(--color-open)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Final Summary message */}
              <div style={{ padding: 10, background: "rgba(0, 242, 254, 0.05)", border: "1px solid rgba(0, 242, 254, 0.2)", borderRadius: 6, fontSize: 12, textAlign: "center" }}>
                <b>AI Performance Report:</b> Sentinel AI routing reduced average delay hours by <b>{Math.round(((results.baseline_avg_delay_hours - results.optimized_avg_delay_hours) / (results.baseline_avg_delay_hours || 1)) * 100)}%</b> and successfully salvaged <b>{results.baseline_critical_affected - results.optimized_critical_affected}</b> critical medical deliveries.
              </div>

            </div>
          )}
        </div>

      </div>
    </div>
  );
}
