import os
import requests
import uuid
import time
from typing import List, Dict, Any
from app.database import load_incidents, save_incidents
from app.models.models import Incident
from app.services.risk_service import recalculate_all_roads_risk

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")

# Mapping keywords to specific NER routes for simulation context
LOCATION_KEYWORDS = {
    "guwahati": ["R-204", "R-301"],
    "shillong": ["R-204", "R-207"],
    "jowai": ["R-207", "R-211"],
    "khliehriat": ["R-211", "R-218"],
    "silchar": ["R-218", "R-303"],
    "nagaon": ["R-301", "R-302"],
    "haflong": ["R-302", "R-303"]
}

EVENT_TYPES = {
    "landslide": ("Landslide", "CRITICAL"),
    "flood": ("Flood", "HIGH"),
    "block": ("Traffic Blockage", "HIGH"),
    "accident": ("Road Damage", "MEDIUM"),
    "bridge": ("Bridge Issue", "CRITICAL")
}

def parse_news_for_incidents(news_items: List[Dict[str, Any]]) -> List[Incident]:
    new_incidents = []
    
    for item in news_items:
        title = item.get("title", "").lower()
        desc = item.get("description", "").lower()
        content = title + " " + desc
        
        # Check event type
        matched_event = None
        for keyword, event_info in EVENT_TYPES.items():
            if keyword in content:
                matched_event = event_info
                break
                
        if not matched_event:
            continue
            
        # Check location
        matched_road = None
        for loc, roads in LOCATION_KEYWORDS.items():
            if loc in content:
                matched_road = roads[0] # Just take the primary road for simplicity
                break
                
        if matched_event and matched_road:
            # We have a valid incident!
            inc = Incident(
                incident_id=f"INC-NEWS-{str(uuid.uuid4())[:8]}",
                road_id=matched_road,
                lat=0.0, # Will be set by a routing engine if needed, or 0.0 for general road issue
                lon=0.0,
                type=matched_event[0],
                severity=matched_event[1],
                description=f"Auto-generated from News: {item.get('title')}",
                photo_url=item.get("image_url"),
                timestamp=time.time(),
                active=True
            )
            new_incidents.append(inc)
            
    return new_incidents

def fetch_real_news() -> List[Incident]:
    if not NEWSDATA_API_KEY:
        return []
        
    try:
        url = f"https://newsdata.io/api/1/news?apikey={NEWSDATA_API_KEY}&q=meghalaya OR assam OR landslide OR flood&country=in&language=en"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        return parse_news_for_incidents(results)
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def update_incidents_from_news():
    """
    Fetches news, parses for incidents, updates state, and recalculates risk.
    """
    new_incidents = fetch_real_news()
    if new_incidents:
        current_incidents = load_incidents()
        
        # Avoid duplicates based on description or recent time
        existing_descs = [inc.description for inc in current_incidents if inc.active]
        
        added = False
        for inc in new_incidents:
            if inc.description not in existing_descs:
                current_incidents.append(inc)
                added = True
                
        if added:
            save_incidents(current_incidents)
            recalculate_all_roads_risk()
            return True
            
    return False
