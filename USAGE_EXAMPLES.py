"""
USAGE EXAMPLES FOR GPX-TO-GEOJSON API
=====================================

This file shows how to call your API from different contexts
"""

# ============================================================================
# EXAMPLE 1: Simple GPX to GeoJSON Conversion
# ============================================================================

import requests

# Endpoint running on Docker
API_URL = "http://localhost:8000"

# Convert GPX file to GeoJSON
with open("myroute.gpx", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{API_URL}/convert", files=files)
    result = response.json()

print(f"Converted {result['feature_count']} features")
geojson = result["geojson"]


# ============================================================================
# EXAMPLE 2: Convert and Append to ArcGIS Feature Layer (Complete Workflow)
# ============================================================================

import requests

API_URL = "http://localhost:8000"

# Your ArcGIS feature layer details
FEATURE_LAYER_URL = "https://services.arcgis.com/sharing/rest/content/items/YOUR_ITEM_ID/data"
# OR for a service endpoint:
# FEATURE_LAYER_URL = "https://your-server.arcgis.com/arcgis/rest/services/YourService/FeatureServer/0/addFeatures"

# ArcGIS authentication token (if required)
TOKEN = "your_token_here"  # Optional

with open("myroute.gpx", "rb") as f:
    files = {"file": f}
    data = {
        "feature_layer_url": FEATURE_LAYER_URL,
        "feature_layer_token": TOKEN,
        # Optional: only append tracks, not waypoints
        "layer_filter": "type=track"
    }
    
    response = requests.post(
        f"{API_URL}/convert-and-append",
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Features appended: {result['append_result']}")


# ============================================================================
# EXAMPLE 3: Python script for batch processing
# ============================================================================

import requests
import os
from pathlib import Path

API_URL = "http://localhost:8000"
FEATURE_LAYER_URL = "https://services.arcgis.com/..." 
TOKEN = "your_token"
GPX_FOLDER = "./gpx_files"

for gpx_file in Path(GPX_FOLDER).glob("*.gpx"):
    print(f"Processing {gpx_file.name}...")
    
    with open(gpx_file, "rb") as f:
        files = {"file": f}
        data = {
            "feature_layer_url": FEATURE_LAYER_URL,
            "feature_layer_token": TOKEN
        }
        
        response = requests.post(
            f"{API_URL}/convert-and-append",
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            print(f"✓ {gpx_file.name} appended successfully")
        else:
            print(f"✗ {gpx_file.name} failed: {response.text}")


# ============================================================================
# EXAMPLE 4: cURL commands
# ============================================================================

# Just convert to GeoJSON
# curl -X POST -F "file=@myroute.gpx" http://localhost:8000/convert

# Convert and append to feature layer
# curl -X POST \
#   -F "file=@myroute.gpx" \
#   -F "feature_layer_url=https://services.arcgis.com/.../addFeatures" \
#   -F "feature_layer_token=your_token" \
#   http://localhost:8000/convert-and-append

# Health check
# curl http://localhost:8000/health


# ============================================================================
# EXAMPLE 5: JavaScript/Node.js (if running in browser or Node)
# ============================================================================

/*
async function uploadGPX(gpxFile, featureLayerUrl, token) {
  const formData = new FormData();
  formData.append("file", gpxFile);
  formData.append("feature_layer_url", featureLayerUrl);
  formData.append("feature_layer_token", token);
  
  const response = await fetch("http://localhost:8000/convert-and-append", {
    method: "POST",
    body: formData
  });
  
  const result = await response.json();
  console.log(`Appended ${result.features_converted} features`);
  return result;
}
*/


# ============================================================================
# EXAMPLE 6: Extracting specific route data before appending
# ============================================================================

import requests
import json

API_URL = "http://localhost:8000"

# Convert to GeoJSON first
with open("myroute.gpx", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{API_URL}/convert", files=files)
    geojson = response.json()["geojson"]

# Extract only routes (LineStrings)
routes = [f for f in geojson["features"] 
          if f["geometry"]["type"] == "LineString"]

# Extract only waypoints (Points)
waypoints = [f for f in geojson["features"] 
             if f["geometry"]["type"] == "Point"]

print(f"Found {len(routes)} routes and {len(waypoints)} waypoints")

# Now append just the routes to your feature layer
# (Requires manual REST call or your feature layer to accept the GeoJSON)


# ============================================================================
# EXAMPLE 7: ArcGIS-specific example with proper authentication
# ============================================================================

import requests
from arcgis.gis import GIS

# Login to ArcGIS Online
gis = GIS("https://www.arcgisonline.com/sharing/rest", "username", "password")

# Get your token
token = gis._token

# Call your API with the token
API_URL = "http://localhost:8000"
FEATURE_LAYER_ID = "YOUR_ITEM_ID"

with open("myroute.gpx", "rb") as f:
    files = {"file": f}
    data = {
        "feature_layer_url": f"https://services.arcgis.com/sharing/rest/content/items/{FEATURE_LAYER_ID}/data",
        "feature_layer_token": token
    }
    
    response = requests.post(
        f"{API_URL}/convert-and-append",
        files=files,
        data=data
    )
    
    print(response.json())


# ============================================================================
# STARTUP COMMANDS
# ============================================================================

"""
1. Build and start the container:
   docker-compose up --build

2. The API will be available at:
   http://localhost:8000

3. View interactive docs:
   http://localhost:8000/docs

4. Test the health endpoint:
   curl http://localhost:8000/health

5. Stop the container:
   docker-compose down
"""
