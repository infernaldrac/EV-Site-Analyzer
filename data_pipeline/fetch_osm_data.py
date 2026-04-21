import json
import os
import time

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = "22.85,72.35,23.30,72.85"
OUT_DIR = os.path.join(os.path.dirname(__file__), "geojson")

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def overpass_query(query: str, timeout_sec: int = 90) -> dict:
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(2):
            try:
                resp = requests.post(mirror, data={"data": query}, timeout=timeout_sec)
                if resp.status_code == 429:
                    print(f"  Rate limited on {mirror}, waiting 10s...")
                    time.sleep(10)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("elements"):
                    return data
                return data
            except Exception as exc:
                print(f"  {mirror} attempt {attempt+1} failed: {exc}")
                time.sleep(5)
    return {"elements": []}


def elements_to_geojson_points(elements: list, extra_props: dict = None) -> dict:
    features = []
    for el in elements:
        if el.get("type") == "node":
            props = dict(el.get("tags", {}))
            if extra_props:
                props.update(extra_props)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [el["lon"], el["lat"]]},
                "properties": props,
            })
    return {"type": "FeatureCollection", "features": features}


def elements_to_geojson_lines(elements: list) -> dict:
    nodes = {el["id"]: el for el in elements if el.get("type") == "node"}
    features = []
    for el in elements:
        if el.get("type") == "way":
            coords = []
            for nid in el.get("nodes", []):
                n = nodes.get(nid)
                if n:
                    coords.append([n["lon"], n["lat"]])
            if len(coords) >= 2:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": el.get("tags", {}),
                })
    return {"type": "FeatureCollection", "features": features}


def elements_to_geojson_polygons(elements: list) -> dict:
    nodes = {el["id"]: el for el in elements if el.get("type") == "node"}
    features = []
    for el in elements:
        if el.get("type") == "way":
            coords = []
            for nid in el.get("nodes", []):
                n = nodes.get(nid)
                if n:
                    coords.append([n["lon"], n["lat"]])
            if len(coords) >= 4 and coords[0] == coords[-1]:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [coords]},
                    "properties": el.get("tags", {}),
                })
    return {"type": "FeatureCollection", "features": features}


def fetch_city_roads() -> dict:
    q = f"""
    [out:json][timeout:90];
    (
      way["highway"~"^(primary|secondary|residential|trunk|tertiary|unclassified)$"]({BBOX});
    );
    out body;
    >;
    out skel qt;
    """
    data = overpass_query(q, 90)
    return elements_to_geojson_lines(data.get("elements", []))


def fetch_highways() -> dict:
    q = f"""
    [out:json][timeout:90];
    (
      way["highway"~"^(motorway|trunk|primary)$"]({BBOX});
    );
    out body;
    >;
    out skel qt;
    """
    data = overpass_query(q, 90)
    return elements_to_geojson_lines(data.get("elements", []))


def fetch_fuel_stations() -> dict:
    q = f"""
    [out:json][timeout:60];
    (
      node["amenity"="fuel"]({BBOX});
      node["amenity"="petrol_station"]({BBOX});
    );
    out body;
    """
    data = overpass_query(q, 60)
    return elements_to_geojson_points(data.get("elements", []))


def fetch_rest_stops() -> dict:
    q = f"""
    [out:json][timeout:60];
    (
      node["amenity"="restaurant"]({BBOX});
      node["amenity"="fast_food"]({BBOX});
      node["amenity"="cafe"]({BBOX});
      node["highway"="rest_area"]({BBOX});
      node["amenity"="truckers_stop"]({BBOX});
    );
    out body;
    """
    data = overpass_query(q, 60)
    return elements_to_geojson_points(data.get("elements", []))


def fetch_ev_stations() -> dict:
    q = f"""
    [out:json][timeout:60];
    (
      node["amenity"="charging_station"]({BBOX});
      node["amenity"="ev_charging"]({BBOX});
    );
    out body;
    """
    data = overpass_query(q, 60)
    return elements_to_geojson_points(data.get("elements", []))


def fetch_city_admin_boundary() -> dict:
    q = """
    [out:json][timeout:60];
    (
      relation["name"="Ahmedabad"]["admin_level"="6"];
      relation["name"="Gandhinagar"]["admin_level"="6"];
      relation["name"="Ahmedabad Municipal Corporation"]["boundary"="administrative"];
    );
    out body;
    >;
    out skel qt;
    """
    data = overpass_query(q, 60)
    return elements_to_geojson_polygons(data.get("elements", []))


def fetch_parking() -> dict:
    q = f"""
    [out:json][timeout:60];
    (
      node["amenity"="parking"]({BBOX});
      way["amenity"="parking"]({BBOX});
    );
    out body;
    >;
    out skel qt;
    """
    data = overpass_query(q, 60)
    points = elements_to_geojson_points(data.get("elements", []))
    return points


def save_geojson(data: dict, filename: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"  Saved {len(data['features'])} features -> {filename}")


if __name__ == "__main__":
    print("Fetching city roads...")
    save_geojson(fetch_city_roads(), "city_roads.geojson")

    print("Fetching highway corridors...")
    save_geojson(fetch_highways(), "highway_corridors.geojson")

    print("Fetching fuel stations...")
    save_geojson(fetch_fuel_stations(), "fuel_stations.geojson")

    print("Fetching rest stops / restaurants...")
    save_geojson(fetch_rest_stops(), "rest_stops.geojson")

    print("Fetching EV charging stations...")
    save_geojson(fetch_ev_stations(), "ev_stations.geojson")

    print("Fetching parking areas...")
    save_geojson(fetch_parking(), "parking.geojson")

    print("OSM fetch complete.")
