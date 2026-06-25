# GPX to GeoJSON API with Feature Layer Integration

A FastAPI-based service that converts GPX files to GeoJSON format and automatically appends them to your hosted ArcGIS feature layers.

## Features

- ✅ Convert GPX files to standard GeoJSON format
- ✅ Extract tracks, routes, and waypoints separately
- ✅ Automatically append features to ArcGIS feature layers via REST API
- ✅ Support for ArcGIS authentication tokens
- ✅ Filter features by type before appending
- ✅ Runs in Docker for easy deployment
- ✅ Interactive API documentation at `/docs`

## Project Structure

```
gpx-geojson-api/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose configuration
├── USAGE_EXAMPLES.py     # Code examples
└── README.md            # This file
```

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- (Optional) ArcGIS feature layer URL for integration

### Installation & Running

```bash
# 1. Clone or create the project directory
mkdir gpx-geojson-api
cd gpx-geojson-api

# 2. Copy all files (app.py, requirements.txt, Dockerfile, docker-compose.yml)

# 3. Build and start the container
docker-compose up --build

# 4. API is now available at http://localhost:8000
```

Access the interactive API documentation:
```
http://localhost:8000/docs
```

## API Endpoints

**Jump to Section:**
1. [Convert GPX to GeoJSON Only](#1-convert-gpx-to-geojson-only)
2. [Convert and Append to Feature Layer](#2-convert-and-append-to-feature-layer)
3. [Health Check](#3-health-check)
4. [Conversion History](#4-conversion-history)

---

### 1. Convert GPX to GeoJSON Only

**Endpoint:** `POST /convert`

Convert a GPX file and get the GeoJSON result without appending to a feature layer.

**Request:**
```bash
curl -X POST -F "file=@myroute.gpx" http://localhost:8000/convert
```

**Response:**
```json
{
  "status": "success",
  "conversion_id": "myroute.gpx_1234567890",
  "feature_count": 3,
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  }
}
```

### 2. Convert and Append to Feature Layer

**Endpoint:** `POST /convert-and-append`

Convert a GPX file and immediately append to your feature layer.

Convert GPX to GeoJSON and immediately append to your feature layer.

**Request Parameters:**
- `file` (required): The GPX file to upload
- `feature_layer_url` (required): Full REST endpoint of your feature layer
  - Example: `https://services.arcgis.com/.../FeatureServer/0/addFeatures`
- `feature_layer_token` (optional): ArcGIS authentication token if required
- `layer_filter` (optional): Filter features by type
  - Options: `type=track`, `type=waypoint`, `type=route`

**Example:**
```bash
curl -X POST \
  -F "file=@myroute.gpx" \
  -F "feature_layer_url=https://services.arcgis.com/YOUR_SERVICE/FeatureServer/0/addFeatures" \
  -F "feature_layer_token=YOUR_TOKEN" \
  http://localhost:8000/convert-and-append
```

**Python Example:**
```python
import requests

with open("myroute.gpx", "rb") as f:
    files = {"file": f}
    data = {
        "feature_layer_url": "https://services.arcgis.com/.../addFeatures",
        "feature_layer_token": "your_token"
    }
    
    response = requests.post(
        "http://localhost:8000/convert-and-append",
        files=files,
        data=data
    )
    print(response.json())
```

### 3. Health Check

**Endpoint:** `GET /health`

Check if the API is running.

Check if the API is running.

```bash
curl http://localhost:8000/health
```

### 4. Conversion History

**Endpoint:** `GET /conversion-history`

View previously converted files (useful for debugging).

View previously converted files (useful for debugging).

```bash
curl http://localhost:8000/conversion-history
```

## How It Works

### Step-by-Step Flow

```
GPX File Upload
       ↓
Parse GPX File
       ↓
Extract Tracks, Routes, Waypoints
       ↓
Convert to GeoJSON Format
       ↓
(Optional) Apply Filters
       ↓
Convert to ArcGIS Feature Format
       ↓
POST to Feature Layer REST API
       ↓
Success Response
```

### Data Conversion Details

**Track/Route Conversion:**
- GPX tracks and routes become GeoJSON `LineString` geometries
- Properties include: name, feature_type, timestamp

**Waypoint Conversion:**
- GPX waypoints become GeoJSON `Point` geometries
- Properties include: name, feature_type, timestamp

**Format Transformation:**
- GeoJSON → ArcGIS Feature Format
  - Points: `{x, y}`
  - LineStrings: `{paths: [[coordinates]]}`
  - Attributes: Feature properties

## Integration with ArcGIS Feature Layers

### Finding Your Feature Layer URL

1. **ArcGIS Online:**
   - Go to your item in ArcGIS Online
   - Click "Share" → "Share the item"
   - Copy the REST endpoint URL

2. **ArcGIS Server:**
   - Navigate to your feature service
   - Look for `/FeatureServer/0/addFeatures` endpoint

### Example URLs

```
# ArcGIS Online hosted feature layer
https://services.arcgis.com/sharing/rest/content/items/YOUR_ITEM_ID/data

# ArcGIS Server
https://your-server.arcgis.com/arcgis/rest/services/YourService/FeatureServer/0/addFeatures
```

### Authentication

If your feature layer requires authentication:

1. Generate a token in ArcGIS
2. Pass it via the `feature_layer_token` parameter
3. API will include it in the REST request

## Docker Management

### Start the API
```bash
docker-compose up --build
```

### Run in background
```bash
docker-compose up -d --build
```

### Stop the API
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f gpx-api
```

### Rebuild after code changes
```bash
docker-compose up --build
```

## Common Use Cases

### Use Case 1: Batch Upload GPX Files
```python
from pathlib import Path
import requests

API_URL = "http://localhost:8000"
FEATURE_LAYER_URL = "https://services.arcgis.com/.../addFeatures"
TOKEN = "your_token"

for gpx_file in Path("./gpx_files").glob("*.gpx"):
    with open(gpx_file, "rb") as f:
        response = requests.post(
            f"{API_URL}/convert-and-append",
            files={"file": f},
            data={
                "feature_layer_url": FEATURE_LAYER_URL,
                "feature_layer_token": TOKEN
            }
        )
        print(f"{gpx_file.name}: {response.json()['status']}")
```

### Use Case 2: Extract Specific Route Data
```python
import requests

response = requests.post(
    "http://localhost:8000/convert",
    files={"file": open("route.gpx", "rb")}
)

geojson = response.json()["geojson"]

# Extract only tracks
tracks = [f for f in geojson["features"] 
          if f["properties"]["feature_type"] == "track"]

# Extract only waypoints
waypoints = [f for f in geojson["features"] 
             if f["properties"]["feature_type"] == "waypoint"]
```

### Use Case 3: Append Only Specific Feature Types
```python
requests.post(
    "http://localhost:8000/convert-and-append",
    files={"file": open("route.gpx", "rb")},
    data={
        "feature_layer_url": "https://...",
        "layer_filter": "type=track"  # Only append tracks
    }
)
```

## Troubleshooting

### API not responding
```bash
# Check if container is running
docker-compose ps

# View logs
docker-compose logs gpx-api

# Restart
docker-compose restart
```

### Feature layer append fails
- Verify the `feature_layer_url` is correct and ends in `/addFeatures`
- Check if authentication token is required and valid
- Ensure feature layer accepts the geometry types being sent

### GPX parsing errors
- Verify GPX file is valid XML
- Check that the GPX file contains tracks, routes, or waypoints
- View error details in API response

## Next Steps

1. **Test locally:** Use curl or the `/docs` interface to test endpoints
2. **Integrate with your workflow:** Adapt usage examples to your needs
3. **Deploy:** Move to production server and update configuration
4. **Scale:** Use async workers (Gunicorn) for handling multiple simultaneous uploads

## Advanced Configuration

### Production Deployment
Replace the default Uvicorn with Gunicorn for better concurrency:

```dockerfile
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "app:app"]
```

### Environment Variables
Add to `docker-compose.yml`:
```yaml
environment:
  - FEATURE_LAYER_URL=https://your-url
  - FEATURE_LAYER_TOKEN=your_token
  - LOG_LEVEL=info
```

## License

Open source - Use and modify as needed.
