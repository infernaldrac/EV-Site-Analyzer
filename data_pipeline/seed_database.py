import json
import os
import sys

from sqlalchemy import create_engine, text

GEOJSON_DIR = os.path.join(os.path.dirname(__file__), "geojson")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/geo_analyzer",
)

TABLE_FILE_MAP = {
    "city_boundaries":   ["city_boundaries.geojson"],
    "highway_corridors": ["highway_corridors.geojson", "highway_corridors_sample.geojson"],
    "ev_stations":       ["ev_stations.geojson", "ev_stations_sample.geojson"],
    "fuel_stations":     ["fuel_stations.geojson", "fuel_stations_sample.geojson"],
    "rest_stops":        ["rest_stops.geojson", "rest_stops_sample.geojson"],
    "city_roads":        ["city_roads.geojson"],
    "ev_adoption_zones": ["ev_adoption_zones.geojson"],
    "income_zones":      ["income_zones.geojson"],
    "risk_zones":        ["risk_zones.geojson"],
    "population_zones":  ["population_zones.geojson"],
}

MERGE_TABLES = {"fuel_stations", "rest_stops", "ev_stations"}


def find_file(filenames):
    for fn in filenames:
        path = os.path.join(GEOJSON_DIR, fn)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    fc = json.load(f)
                if fc.get("features"):
                    return path
            except Exception:
                pass
    return None


def get_prop(props, *keys, default=""):
    for k in keys:
        if k in props and props[k] is not None:
            return props[k]
    return default


def map_highway_class(v):
    v = str(v).lower()
    if v in ("motorway", "trunk"):
        return "NH"
    if v == "primary":
        return "SH"
    return "MDR"


def map_road_class(v):
    v = str(v).lower()
    if v in ("primary", "trunk", "secondary", "residential", "tertiary", "unclassified"):
        return v
    return "residential"


def map_stop_type(props):
    amenity = str(props.get("amenity", "")).lower()
    if amenity == "restaurant":
        return "dhaba"
    return "rest_area"


def insert_city_boundaries(conn, features):
    count = 0
    for f in features:
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        name = get_prop(props, "name", default="Unknown")
        conn.execute(text(
            "INSERT INTO city_boundaries (name, geom) VALUES (:name, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"name": name, "geom": geom})
        count += 1
    return count


def insert_highway_corridors(conn, features):
    count = 0
    for f in features:
        if f["geometry"]["type"] not in ("LineString", "MultiLineString"):
            continue
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        name = get_prop(props, "name", "ref", default="")
        hc = get_prop(props, "highway_class", default="")
        if not hc:
            hc = map_highway_class(get_prop(props, "highway", default="primary"))
        try:
            conn.execute(text(
                "INSERT INTO highway_corridors (name, highway_class, geom) "
                "VALUES (:name, :hc, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
            ), {"name": name, "hc": hc, "geom": geom})
            count += 1
        except Exception:
            pass
    return count


def insert_ev_stations(conn, features):
    count = 0
    for f in features:
        if f["geometry"]["type"] != "Point":
            continue
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        name = get_prop(props, "name", default="")
        operator = get_prop(props, "operator", default="")
        conn.execute(text(
            "INSERT INTO ev_stations (name, operator, source, geom) "
            "VALUES (:name, :operator, 'osm', ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"name": name, "operator": operator, "geom": geom})
        count += 1
    return count


def insert_fuel_stations(conn, features):
    count = 0
    for f in features:
        if f["geometry"]["type"] != "Point":
            continue
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        name = get_prop(props, "name", default="")
        brand = get_prop(props, "brand", "name", default="")
        conn.execute(text(
            "INSERT INTO fuel_stations (name, brand, geom) "
            "VALUES (:name, :brand, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"name": name, "brand": brand, "geom": geom})
        count += 1
    return count


def insert_rest_stops(conn, features):
    count = 0
    for f in features:
        if f["geometry"]["type"] != "Point":
            continue
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        name = get_prop(props, "name", default="")
        stop_type = get_prop(props, "stop_type", default="") or map_stop_type(props)
        conn.execute(text(
            "INSERT INTO rest_stops (name, stop_type, geom) "
            "VALUES (:name, :stop_type, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"name": name, "stop_type": stop_type, "geom": geom})
        count += 1
    return count


def insert_city_roads(conn, features):
    count = 0
    for f in features:
        if f["geometry"]["type"] not in ("LineString", "MultiLineString"):
            continue
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        name = get_prop(props, "name", default="")
        rc = get_prop(props, "road_class", default="") or map_road_class(get_prop(props, "highway", default="residential"))
        try:
            conn.execute(text(
                "INSERT INTO city_roads (name, road_class, geom) "
                "VALUES (:name, :rc, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
            ), {"name": name, "rc": rc, "geom": geom})
            count += 1
        except Exception:
            pass
    return count


def insert_ev_adoption_zones(conn, features):
    count = 0
    for f in features:
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        zone_name = get_prop(props, "zone_name", default="")
        ev_density = float(get_prop(props, "ev_density", default=10.0))
        conn.execute(text(
            "INSERT INTO ev_adoption_zones (zone_name, ev_density, geom) "
            "VALUES (:zone_name, :ev_density, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"zone_name": zone_name, "ev_density": ev_density, "geom": geom})
        count += 1
    return count


def insert_income_zones(conn, features):
    count = 0
    for f in features:
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        zone_name = get_prop(props, "zone_name", default="")
        income_level = get_prop(props, "income_level", default="medium")
        income_score = float(get_prop(props, "income_score", default=50.0))
        conn.execute(text(
            "INSERT INTO income_zones (zone_name, income_level, income_score, geom) "
            "VALUES (:zone_name, :income_level, :income_score, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"zone_name": zone_name, "income_level": income_level, "income_score": income_score, "geom": geom})
        count += 1
    return count


def insert_risk_zones(conn, features):
    count = 0
    for f in features:
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        zone_name = get_prop(props, "zone_name", default="")
        flood_risk = get_prop(props, "flood_risk", default="low")
        terrain_risk = get_prop(props, "terrain_risk", default="low")
        conn.execute(text(
            "INSERT INTO risk_zones (zone_name, flood_risk, terrain_risk, geom) "
            "VALUES (:zone_name, :flood_risk, :terrain_risk, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"zone_name": zone_name, "flood_risk": flood_risk, "terrain_risk": terrain_risk, "geom": geom})
        count += 1
    return count


def insert_population_zones(conn, features):
    count = 0
    for f in features:
        geom = json.dumps(f["geometry"])
        props = f.get("properties") or {}
        zone_name = get_prop(props, "zone_name", default="")
        pop_density = float(get_prop(props, "pop_density", default=5000.0))
        conn.execute(text(
            "INSERT INTO population_zones (zone_name, pop_density, geom) "
            "VALUES (:zone_name, :pop_density, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        ), {"zone_name": zone_name, "pop_density": pop_density, "geom": geom})
        count += 1
    return count


INSERT_FN = {
    "city_boundaries":   insert_city_boundaries,
    "highway_corridors": insert_highway_corridors,
    "ev_stations":       insert_ev_stations,
    "fuel_stations":     insert_fuel_stations,
    "rest_stops":        insert_rest_stops,
    "city_roads":        insert_city_roads,
    "ev_adoption_zones": insert_ev_adoption_zones,
    "income_zones":      insert_income_zones,
    "risk_zones":        insert_risk_zones,
    "population_zones":  insert_population_zones,
}


def seed_table(engine, table: str, filenames: list) -> bool:
    insert_fn = INSERT_FN[table]

    if table in MERGE_TABLES:
        all_features = []
        used_files = []
        for fn in filenames:
            path = os.path.join(GEOJSON_DIR, fn)
            if not os.path.exists(path):
                continue
            try:
                with open(path) as f:
                    fc = json.load(f)
                features = fc.get("features", [])
                if features:
                    all_features.extend(features)
                    used_files.append(f"{os.path.basename(path)}({len(features)})")
            except Exception as exc:
                print(f"  WARN {fn}: {exc}")

        if not all_features:
            print(f"  SKIP {table}: no features found in any file")
            return False

        try:
            with engine.begin() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                count = insert_fn(conn, all_features)
            print(f"  OK {table}: loaded {count} rows from {', '.join(used_files)}")
            return True
        except Exception as exc:
            print(f"  FAIL {table}: {exc}")
            return False

    filepath = find_file(filenames)
    if filepath is None:
        print(f"  SKIP {table}: no file found (tried {filenames})")
        return False

    try:
        with open(filepath) as f:
            fc = json.load(f)
        features = fc.get("features", [])
        if not features:
            print(f"  SKIP {table}: GeoJSON has no features at {os.path.basename(filepath)}")
            return False

        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            count = insert_fn(conn, features)

        print(f"  OK {table}: loaded {count} rows from {os.path.basename(filepath)}")
        return True

    except Exception as exc:
        print(f"  FAIL {table}: {exc}")
        import traceback
        traceback.print_exc()
        return False


def main():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    results = {}

    for table, filenames in TABLE_FILE_MAP.items():
        print(f"Loading {table}...")
        results[table] = seed_table(engine, table, filenames)

    print("\n=== Seed Summary ===")
    ok = [t for t, v in results.items() if v]
    fail = [t for t, v in results.items() if not v]
    print(f"Loaded:  {', '.join(ok) if ok else 'none'}")
    print(f"Skipped/Failed: {', '.join(fail) if fail else 'none'}")


if __name__ == "__main__":
    main()
