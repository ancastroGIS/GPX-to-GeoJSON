from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import gpxpy
import json
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

app = FastAPI(title="GPX to GeoJSON API with Feature Layer Integration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store conversion results for reference
conversion_history = {}


def _to_arcgis_ms(dt) -> Optional[int]:
    """Convert a GPX datetime to ArcGIS epoch-milliseconds (esriFieldTypeDate)."""
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

@app.post("/convert")
async def convert_gpx_to_geojson(file: UploadFile = File(...)):
    """
    Upload a GPX file and get GeoJSON output
    Returns the GeoJSON in standard format
    """
    try:
        if not file.filename.lower().endswith('.gpx'):
            raise HTTPException(status_code=400, detail="File must be a .gpx file")
        
        contents = await file.read()
        gpx = gpxpy.parse(contents.decode('utf-8'))
        
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Convert tracks
        for track in gpx.tracks:
            for segment in track.segments:
                coordinates = [[point.longitude, point.latitude] for point in segment.points]
                
                if len(coordinates) < 2:
                    continue
                
                feature = {
                    "type": "Feature",
                    "properties": {
                        "name": track.name or "Track",
                        "type": "track",
                        "timestamp": datetime.now().isoformat()
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates
                    }
                }
                geojson["features"].append(feature)
        
        # Convert waypoints
        for waypoint in gpx.waypoints:
            feature = {
                "type": "Feature",
                "properties": {
                    "name": waypoint.name or "Waypoint",
                    "type": "waypoint",
                    "timestamp": datetime.now().isoformat()
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [waypoint.longitude, waypoint.latitude]
                }
            }
            geojson["features"].append(feature)
        
        # Convert routes
        for route in gpx.routes:
            coordinates = [[point.longitude, point.latitude] for point in route.points]
            
            if len(coordinates) < 2:
                continue
            
            feature = {
                "type": "Feature",
                "properties": {
                    "name": route.name or "Route",
                    "type": "route",
                    "timestamp": datetime.now().isoformat()
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                }
            }
            geojson["features"].append(feature)
        
        # Store for reference
        conversion_id = f"{file.filename}_{datetime.now().timestamp()}"
        conversion_history[conversion_id] = geojson
        
        return JSONResponse(content={
            "status": "success",
            "conversion_id": conversion_id,
            "feature_count": len(geojson["features"]),
            "geojson": geojson
        })
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing GPX: {str(e)}")


@app.post("/convert-and-append")
async def convert_and_append_to_feature_layer(
    file: UploadFile = File(...),
    feature_layer_url: Optional[str] = None,
    feature_layer_token: Optional[str] = None,
    layer_filter: Optional[str] = None,
):
    """
    Convert GPX to GeoJSON and immediately append to a feature layer via REST API

    Args:
        file: GPX file to upload
        feature_layer_url: REST endpoint (e.g., 'https://services.arcgis.com/.../addFeatures')
        feature_layer_token: Optional authentication token
        layer_filter: Optional filter like "type=track" to only append specific features

    Returns:
        Conversion and append results
    """
    if not feature_layer_url:
        raise HTTPException(status_code=400, detail="feature_layer_url is required")
    try:
        # Step 1: Convert GPX to GeoJSON
        contents = await file.read()
        gpx = gpxpy.parse(contents.decode('utf-8'))
        
        features = []
        
        # Parse tracks — each GPS point becomes a Point feature (layer is esriGeometryPoint)
        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    coords = [pt.longitude, pt.latitude]
                    if pt.elevation is not None:
                        coords.append(float(pt.elevation))
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "name": track.name or "Track",
                            "descript": "",
                            "type": "track",
                            "comment": "",
                            "symbol": "",
                            "datetimes": pt.time.isoformat() if pt.time else None,
                            "elevation": float(pt.elevation) if pt.elevation is not None else None,
                            "datetime": _to_arcgis_ms(pt.time),
                            "feature_type": "track",
                        },
                        "geometry": {"type": "Point", "coordinates": coords},
                    })

        # Parse routes — same point-per-vertex approach
        for route in gpx.routes:
            for pt in route.points:
                coords = [pt.longitude, pt.latitude]
                if pt.elevation is not None:
                    coords.append(float(pt.elevation))
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": route.name or "Route",
                        "descript": "",
                        "type": "route",
                        "comment": "",
                        "symbol": "",
                        "datetimes": pt.time.isoformat() if pt.time else None,
                        "elevation": float(pt.elevation) if pt.elevation is not None else None,
                        "datetime": _to_arcgis_ms(pt.time),
                        "feature_type": "route",
                    },
                    "geometry": {"type": "Point", "coordinates": coords},
                })

        # Parse waypoints
        for waypoint in gpx.waypoints:
            features.append({
                "type": "Feature",
                "properties": {
                    "name": waypoint.name or "Waypoint",
                    "descript": waypoint.description or "",
                    "type": "waypoint",
                    "comment": "",
                    "symbol": waypoint.symbol or "",
                    "datetimes": waypoint.time.isoformat() if waypoint.time else None,
                    "elevation": float(waypoint.elevation) if waypoint.elevation is not None else None,
                    "datetime": _to_arcgis_ms(waypoint.time),
                    "feature_type": "waypoint",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [waypoint.longitude, waypoint.latitude],
                },
            })
        
        # Apply filter if specified
        if layer_filter:
            filter_type = layer_filter.split("=")[1] if "=" in layer_filter else None
            if filter_type:
                features = [f for f in features if f["properties"].get("feature_type") == filter_type]
        
        if not features:
            return JSONResponse(
                status_code=400,
                content={"error": "No features matched the filter criteria"}
            )
        
        # Step 2: Append to feature layer
        append_result = await append_to_feature_layer(
            features=features,
            feature_layer_url=feature_layer_url,
            token=feature_layer_token
        )
        
        return JSONResponse(content={
            "status": "success",
            "gpx_file": file.filename,
            "features_converted": len(features),
            "append_result": append_result
        })
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


async def append_to_feature_layer(
    features: list,
    feature_layer_url: str,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Append features to an ArcGIS feature layer via REST API
    
    Args:
        features: List of GeoJSON features
        feature_layer_url: Full REST endpoint (supports /addFeatures or /applyEdits)
        token: Optional authentication token
    
    Returns:
        Response from feature layer service
    """
    try:
        # Convert GeoJSON features to ArcGIS format
        arcgis_features = [convert_geojson_to_arcgis(f) for f in features]
        
        if not feature_layer_url:
            return {"status": "error", "message": "feature_layer_url is required"}

        # Prepare payload - different format for applyEdits vs addFeatures
        if "/applyEdits" in feature_layer_url:
            # applyEdits expects adds/updates/deletes structure
            payload = {
                "adds": json.dumps(arcgis_features),
                "f": "json"
            }
        else:
            # addFeatures expects features array
            payload = {
                "features": json.dumps(arcgis_features),
                "f": "json"
            }
        
        if token:
            payload["token"] = token
        
        # Make the request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                feature_layer_url,
                data=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def convert_geojson_to_arcgis(geojson_feature: Dict) -> Dict:
    """
    Convert GeoJSON feature to ArcGIS feature format
    Maps all GeoJSON properties directly to ArcGIS attributes
    """
    geometry = geojson_feature.get("geometry", {})
    properties = geojson_feature.get("properties", {})
    
    # Convert GeoJSON geometry to ArcGIS geometry
    arcgis_geometry = convert_geometry_to_arcgis(geometry)
    
    # Clean up properties - remove feature_type if present (internal use only)
    attributes = {k: v for k, v in properties.items() if k != "feature_type"}
    
    return {
        "geometry": arcgis_geometry,
        "attributes": attributes
    }


def convert_geometry_to_arcgis(geometry: Dict) -> Dict:
    """
    Convert GeoJSON geometry to ArcGIS geometry format
    Includes spatial reference for WGS84 (EPSG:4326)
    """
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    
    # Standard spatial reference for WGS84 (lat/lon)
    spatial_ref = {"wkid": 4326}
    
    if geom_type == "Point":
        result = {
            "x": coordinates[0],
            "y": coordinates[1],
            "spatialReference": spatial_ref,
        }
        if len(coordinates) >= 3:
            result["z"] = coordinates[2]
        return result
    
    elif geom_type == "LineString":
        return {
            "paths": [coordinates],
            "spatialReference": spatial_ref
        }
    
    elif geom_type == "Polygon":
        return {
            "rings": coordinates,
            "spatialReference": spatial_ref
        }
    
    elif geom_type == "MultiPoint":
        return {
            "points": coordinates,
            "spatialReference": spatial_ref
        }
    
    return geometry


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/conversion-history")
async def get_conversion_history():
    """
    Retrieve previously converted GPX files (useful for debugging)
    """
    return {
        "count": len(conversion_history),
        "conversions": list(conversion_history.keys())
    }


@app.get("/ui", response_class=HTMLResponse)
async def frontend():
    return Path("static/index.html").read_text(encoding="utf-8")


@app.get("/")
async def root():
    return {
        "service": "GPX to GeoJSON API",
        "endpoints": {
            "ui": "GET /ui - Web interface",
            "convert": "POST /convert - Convert GPX file to GeoJSON",
            "convert_and_append": "POST /convert-and-append - Convert and append to feature layer",
            "health": "GET /health - Health check",
            "docs": "GET /docs - Interactive API documentation"
        }
    }
