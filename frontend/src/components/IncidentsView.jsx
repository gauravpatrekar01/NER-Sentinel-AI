import React, { useState } from "react";
import { AlertOctagon, Upload, CheckCircle2, ShieldAlert } from "lucide-react";

const ROAD_COORDS = {
  "R-204": { lat: 25.9015, lon: 91.8800, name: "Guwahati-Shillong Highway (NH-6) - Landslide Zone" },
  "R-207": { lat: 25.5700, lon: 92.0500, name: "Shillong-Jowai Bypass (NH-6)" },
  "R-211": { lat: 25.3700, lon: 92.3100, name: "Jowai-Khliehriat Road (NH-6)" },
  "R-218": { lat: 25.1050, lon: 92.4200, name: "Khliehriat-Silchar Ridge (NH-6) - Sonapur Cave" },
  "R-301": { lat: 26.1100, lon: 92.1700, name: "Guwahati-Nagaon Expressway (NH-27)" },
  "R-302": { lat: 25.7500, lon: 92.9500, name: "Nagaon-Haflong Mountain Cut (NH-54)" },
  "R-303": { lat: 25.1100, lon: 92.8700, name: "Haflong-Silchar Link (NH-270)" }
};

export default function IncidentsView({ roads, onSubmitIncidentSuccess }) {
  const [roadId, setRoadId] = useState("R-204");
  const [lat, setLat] = useState(ROAD_COORDS["R-204"].lat);
  const [lon, setLon] = useState(ROAD_COORDS["R-204"].lon);
  const [type, setType] = useState("Landslide");
  const [severity, setSeverity] = useState("CRITICAL");
  const [description, setDescription] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [photoUrl, setPhotoUrl] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleRoadChange = (e) => {
    const selectedId = e.target.value;
    setRoadId(selectedId);
    if (ROAD_COORDS[selectedId]) {
      setLat(ROAD_COORDS[selectedId].lat);
      setLon(ROAD_COORDS[selectedId].lon);
    }
  };

  const handleSimulatedUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsUploading(true);
    setUploadProgress(10);
    
    // Simulate upload progress
    const timer = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(timer);
          setIsUploading(false);
          setPhotoUrl("https://images.unsplash.com/photo-1594897030264-ab7d87efc473?auto=format&fit=crop&w=400&q=80"); // Landslide image
          return 100;
        }
        return prev + 30;
      });
    }, 300);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSuccessMessage("");
    setErrorMsg("");

    const payload = {
      road_id: roadId,
      lat: parseFloat(lat),
      lon: parseFloat(lon),
      type,
      severity,
      description,
      photo_url: photoUrl || null,
      optimize_immediately: true
    };

    fetch("http://127.0.0.1:8000/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(res => {
        if (!res.ok) throw new Error("Server error during registration");
        return res.json();
      })
      .then(data => {
        setSuccessMessage(`Incident reported successfully. Affected vehicles: ${data.affected_vehicles_count || 0}. Alternate routes activated!`);
        setDescription("");
        setPhotoUrl("");
        setUploadProgress(0);
        if (onSubmitIncidentSuccess) onSubmitIncidentSuccess();
      })
      .catch(err => {
        console.error(err);
        setErrorMsg("Failed to report incident. Please verify server status.");
      });
  };

  return (
    <div style={{ padding: 24, overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: "bold", color: "#00f2fe" }}>FIELD INCIDENT REPORTING</h2>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Direct terminal interface for local officers to report blockages, floods, or structural failures.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 24 }}>
        
        {/* Reporting Form */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 className="card-title">
            <span>Report Road Incident</span>
            <AlertOctagon size={16} />
          </h3>

          {successMessage && (
            <div style={{ padding: 12, backgroundColor: "rgba(16,185,129,0.1)", border: "1px solid var(--color-open)", borderRadius: 6, color: "var(--color-open)", display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
              <CheckCircle2 size={16} />
              <span>{successMessage}</span>
            </div>
          )}

          {errorMsg && (
            <div style={{ padding: 12, backgroundColor: "rgba(244,63,94,0.1)", border: "1px solid var(--color-blocked)", borderRadius: 6, color: "var(--color-blocked)", display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
              <AlertOctagon size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            
            <div className="form-group">
              <label>Select Affected Road Segment</label>
              <select value={roadId} onChange={handleRoadChange} className="form-control">
                {roads.map(r => (
                  <option key={r.road_id} value={r.road_id}>
                    {r.name} ({r.road_id})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div className="form-group">
                <label>Latitude Coordinates (simulated GPS)</label>
                <input 
                  type="number" 
                  step="0.00001" 
                  value={lat} 
                  onChange={(e) => setLat(e.target.value)} 
                  className="form-control"
                  required
                />
              </div>
              <div className="form-group">
                <label>Longitude Coordinates (simulated GPS)</label>
                <input 
                  type="number" 
                  step="0.00001" 
                  value={lon} 
                  onChange={(e) => setLon(e.target.value)} 
                  className="form-control"
                  required
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div className="form-group">
                <label>Incident Type</label>
                <select value={type} onChange={(e) => setType(e.target.value)} className="form-control">
                  <option value="Landslide">Landslide</option>
                  <option value="Flood">Flood / Water Logging</option>
                  <option value="Road Damage">Severe Road Damage</option>
                  <option value="Bridge Issue">Bridge Damage / Collapse</option>
                  <option value="Traffic Blockage">Accident / Heavy Congestion</option>
                  <option value="Other">Other Obstruction</option>
                </select>
              </div>
              <div className="form-group">
                <label>Impact Severity</label>
                <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="form-control">
                  <option value="LOW">LOW (Slight speed reduction)</option>
                  <option value="MEDIUM">MEDIUM (Caution / minor delay)</option>
                  <option value="HIGH">HIGH (Single lane / major delay)</option>
                  <option value="CRITICAL">CRITICAL (COMPLETE BLOCKAGE)</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Detailed Incident Description</label>
              <textarea 
                value={description} 
                onChange={(e) => setDescription(e.target.value)} 
                className="form-control"
                rows="3"
                placeholder="Describe current road conditions, width of blockage, or river overflow depth..."
                required
              />
            </div>

            <div className="form-group">
              <label>Field Photo Upload (simulated)</label>
              <div style={{ border: "1px dashed rgba(0, 242, 254, 0.3)", borderRadius: 6, padding: "16px 12px", textAlign: "center", cursor: "pointer", background: "rgba(13, 19, 44, 0.4)", position: "relative" }}>
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={handleSimulatedUpload}
                  style={{ opacity: 0, position: "absolute", top: 0, left: 0, width: "100%", height: "100%", cursor: "pointer" }}
                />
                <Upload size={20} style={{ color: "#00f2fe", marginBottom: 6 }} />
                <div style={{ fontSize: 12 }}>
                  {isUploading ? `Uploading: ${uploadProgress}%` : (photoUrl ? "✓ Photo uploaded successfully" : "Click to select or drop a file")}
                </div>
              </div>
              {isUploading && (
                <div style={{ width: "100%", height: "4px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: 2, marginTop: 4, overflow: "hidden" }}>
                  <div style={{ width: `${uploadProgress}%`, height: "100%", backgroundColor: "#00f2fe" }}></div>
                </div>
              )}
            </div>

            <button type="submit" className="btn btn-primary" style={{ marginTop: 6 }}>
              SUBMIT INCIDENT & RECALCULATE
            </button>
          </form>
        </div>

        {/* Map Guidelines Card */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          
          <div className="glass-card">
            <h3 className="card-title">
              <span>Simulation Information</span>
              <ShieldAlert size={16} />
            </h3>
            <div style={{ fontSize: 12, lineHeight: "1.6", color: "var(--text-secondary)" }}>
              <p style={{ marginBottom: 10 }}>
                NER-Sentinel AI links field reports directly to our active routing engine:
              </p>
              <ul style={{ paddingLeft: 16, marginBottom: 10 }}>
                <li><b>Landslide or CRITICAL</b> reports will mark the road segment status as <b>BLOCKED</b>.</li>
                <li>Affected transit vehicles on that route will automatically trigger the optimizer.</li>
                <li>ETAs and delays will propagate dynamically across all dependent cargo orders.</li>
              </ul>
              <p>
                To reset changes and restore initial data for testing, click the <b>RESET DEMO</b> button in the main header.
              </p>
            </div>
          </div>

          {photoUrl && (
            <div className="glass-card">
              <h3 className="card-title">Uploaded Incident Photo Preview</h3>
              <img 
                src={photoUrl} 
                alt="Uploaded Incident" 
                style={{ width: "100%", borderRadius: 6, maxHeight: "200px", objectFit: "cover" }} 
              />
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
