from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import gpxpy
import json

app = FastAPI(title="GPX to GeoJSON API")

@app.post("/convert")
async def convert_gpx_to_geojson(file: UploadFile = File(...)):
    """
    Upload a GPX file and get GeoJSON output
    """
    try:
        contents = await file.read()
        gpx = gpxpy.parse(contents.decode('utf-8'))
        
        # Initialize GeoJSON structure
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Convert tracks
        for track in gpx.tracks:
            for segment in track.segments:
                coordinates = [[point.longitude, point.latitude] for point in segment.points]
                feature = {
                    "type": "Feature",
                    "properties": {"name": track.name or "Track"},
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
                "properties": {"name": waypoint.name or "Waypoint"},
                "geometry": {
                    "type": "Point",
                    "coordinates": [waypoint.longitude, waypoint.latitude]
                }
            }
            geojson["features"].append(feature)
        
        return JSONResponse(content=geojson)
    
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
