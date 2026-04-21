import json
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "geojson")


def rect(lon, lat, w, h):
    hw, hh = w / 2, h / 2
    return {"type": "Polygon", "coordinates": [[
        [lon - hw, lat - hh], [lon + hw, lat - hh],
        [lon + hw, lat + hh], [lon - hw, lat + hh],
        [lon - hw, lat - hh],
    ]]}


def feat(geom, props):
    return {"type": "Feature", "geometry": geom, "properties": props}


def fc(features):
    return {"type": "FeatureCollection", "features": features}


def save(data, filename):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    n = len(data["features"])
    print(f"  Saved {n} features -> {filename}")


def city_boundaries():
    return fc([
        feat({"type": "Polygon", "coordinates": [[[72.4700, 22.9200], [72.6900, 22.9200], [72.6900, 23.1200], [72.4700, 23.1200], [72.4700, 22.9200]]]}, {"name": "Ahmedabad"}),
        feat({"type": "Polygon", "coordinates": [[[72.5800, 23.1200], [72.7200, 23.1200], [72.7200, 23.3000], [72.5800, 23.3000], [72.5800, 23.1200]]]}, {"name": "Gandhinagar"}),
    ])


def ev_adoption_zones():
    wards = [
        (72.5050, 23.0300, 0.040, 0.030, "SG Highway Corridor", 52.0),
        (72.5100, 23.0150, 0.035, 0.025, "Prahlad Nagar", 48.0),
        (72.5000, 23.0450, 0.035, 0.025, "Bodakdev", 45.0),
        (72.4900, 23.0000, 0.035, 0.025, "Bopal-Ghuma", 42.0),
        (72.5400, 23.0600, 0.035, 0.025, "Thaltej", 40.0),
        (72.5150, 23.0400, 0.035, 0.025, "Vastrapur", 38.0),
        (72.5600, 23.0350, 0.030, 0.022, "Navrangpura", 32.0),
        (72.5250, 23.0200, 0.030, 0.022, "Satellite", 30.0),
        (72.5800, 23.0100, 0.030, 0.022, "Paldi", 25.0),
        (72.6000, 23.0300, 0.030, 0.022, "Naranpura", 24.0),
        (72.6100, 23.0500, 0.030, 0.022, "Ghatlodia", 22.0),
        (72.6300, 23.0700, 0.030, 0.022, "Chandkheda", 20.0),
        (72.5700, 23.0700, 0.030, 0.022, "Motera", 18.0),
        (72.5900, 22.9900, 0.030, 0.022, "Maninagar", 16.0),
        (72.6200, 23.0200, 0.030, 0.022, "Vastral", 12.0),
        (72.5500, 22.9800, 0.030, 0.022, "Isanpur", 10.0),
        (72.5300, 22.9700, 0.030, 0.022, "Nikol", 9.0),
        (72.6500, 22.9800, 0.030, 0.022, "Odhav Industrial", 7.0),
        (72.6700, 23.0800, 0.030, 0.022, "Naroda Industrial", 6.0),
        (72.6600, 22.9700, 0.030, 0.022, "Vatva Industrial", 5.0),
        (72.6500, 23.2200, 0.040, 0.030, "Gandhinagar Sector 1-10", 35.0),
        (72.6700, 23.2000, 0.035, 0.025, "Gandhinagar Sector 11-20", 30.0),
        (72.6300, 23.2400, 0.035, 0.025, "Gandhinagar Sector 21-30", 28.0),
    ]
    return fc([feat(rect(lon, lat, w, h), {"zone_name": name, "ev_density": d})
               for lon, lat, w, h, name, d in wards])


def income_zones():
    wards = [
        (72.5100, 23.0150, 0.035, 0.025, "Prahlad Nagar", "very_high", 95.0),
        (72.5000, 23.0450, 0.035, 0.025, "Bodakdev", "very_high", 92.0),
        (72.5400, 23.0600, 0.035, 0.025, "Thaltej", "very_high", 90.0),
        (72.4900, 23.0000, 0.035, 0.025, "Bopal", "very_high", 88.0),
        (72.5050, 23.0300, 0.040, 0.030, "SG Highway", "very_high", 85.0),
        (72.5150, 23.0400, 0.035, 0.025, "Vastrapur", "high", 78.0),
        (72.5250, 23.0200, 0.030, 0.022, "Satellite", "high", 75.0),
        (72.5600, 23.0350, 0.030, 0.022, "Navrangpura", "high", 72.0),
        (72.6100, 23.0500, 0.030, 0.022, "Ghatlodia", "high", 68.0),
        (72.6500, 23.2200, 0.040, 0.030, "Gandhinagar Sectors", "high", 70.0),
        (72.5800, 23.0100, 0.030, 0.022, "Paldi", "medium", 58.0),
        (72.6000, 23.0300, 0.030, 0.022, "Naranpura", "medium", 55.0),
        (72.5900, 22.9900, 0.030, 0.022, "Maninagar", "medium", 52.0),
        (72.6300, 23.0700, 0.030, 0.022, "Chandkheda", "medium", 48.0),
        (72.5700, 23.0700, 0.030, 0.022, "Motera", "medium", 45.0),
        (72.6200, 23.0200, 0.030, 0.022, "Vastral", "medium", 42.0),
        (72.6500, 22.9800, 0.030, 0.022, "Odhav", "low", 28.0),
        (72.6700, 23.0800, 0.030, 0.022, "Naroda", "low", 25.0),
        (72.6600, 22.9700, 0.030, 0.022, "Vatva", "low", 22.0),
        (72.5500, 22.9800, 0.030, 0.022, "Isanpur", "low", 30.0),
        (72.5300, 22.9700, 0.030, 0.022, "Nikol", "low", 32.0),
        (72.6400, 22.9900, 0.030, 0.022, "Gomtipur", "low", 26.0),
    ]
    return fc([feat(rect(lon, lat, w, h), {"zone_name": name, "income_level": level, "income_score": score})
               for lon, lat, w, h, name, level, score in wards])


def population_zones():
    wards = [
        (72.5900, 22.9900, 0.030, 0.022, "Maninagar", 28500.0),
        (72.6400, 22.9900, 0.030, 0.022, "Gomtipur", 26000.0),
        (72.5800, 23.0100, 0.030, 0.022, "Paldi", 24000.0),
        (72.6700, 23.0800, 0.030, 0.022, "Naroda", 22000.0),
        (72.5500, 22.9800, 0.030, 0.022, "Isanpur", 20000.0),
        (72.5300, 22.9700, 0.030, 0.022, "Nikol", 19000.0),
        (72.6200, 23.0200, 0.030, 0.022, "Vastral", 18000.0),
        (72.5600, 23.0350, 0.030, 0.022, "Navrangpura", 14000.0),
        (72.5250, 23.0200, 0.030, 0.022, "Satellite", 12000.0),
        (72.6000, 23.0300, 0.030, 0.022, "Naranpura", 11500.0),
        (72.6100, 23.0500, 0.030, 0.022, "Ghatlodia", 10000.0),
        (72.6300, 23.0700, 0.030, 0.022, "Chandkheda", 9500.0),
        (72.5700, 23.0700, 0.030, 0.022, "Motera", 9000.0),
        (72.5150, 23.0400, 0.035, 0.025, "Vastrapur", 7500.0),
        (72.5400, 23.0600, 0.035, 0.025, "Thaltej", 5500.0),
        (72.4900, 23.0000, 0.035, 0.025, "Bopal", 5000.0),
        (72.5100, 23.0150, 0.035, 0.025, "Prahlad Nagar", 4500.0),
        (72.5000, 23.0450, 0.035, 0.025, "Bodakdev", 4200.0),
        (72.5050, 23.0300, 0.040, 0.030, "SG Highway", 3800.0),
        (72.6500, 22.9800, 0.030, 0.022, "Odhav", 8500.0),
        (72.6600, 22.9700, 0.030, 0.022, "Vatva", 7000.0),
        (72.6500, 23.2200, 0.040, 0.030, "Gandhinagar", 4500.0),
    ]
    return fc([feat(rect(lon, lat, w, h), {"zone_name": name, "pop_density": d})
               for lon, lat, w, h, name, d in wards])


def city_roads_sample():
    roads = [
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.4900, 23.0000], [72.5050, 23.0300], [72.5200, 23.0600], [72.5400, 23.0800],
        ]}, "properties": {"name": "SG Highway", "highway": "primary", "road_class": "primary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5600, 23.0350], [72.5700, 23.0300], [72.5800, 23.0250], [72.5900, 23.0200],
        ]}, "properties": {"name": "CG Road", "highway": "primary", "road_class": "primary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5800, 22.9900], [72.5800, 23.0100], [72.5800, 23.0300], [72.5800, 23.0500],
        ]}, "properties": {"name": "Ashram Road", "highway": "primary", "road_class": "primary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5100, 23.0150], [72.5300, 23.0200], [72.5500, 23.0250], [72.5700, 23.0300],
        ]}, "properties": {"name": "Satellite Road", "highway": "secondary", "road_class": "secondary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.6000, 23.0300], [72.6100, 23.0400], [72.6200, 23.0500], [72.6300, 23.0600],
        ]}, "properties": {"name": "Naranpura Road", "highway": "secondary", "road_class": "secondary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5900, 22.9900], [72.6000, 22.9950], [72.6100, 23.0000], [72.6200, 23.0050],
        ]}, "properties": {"name": "Maninagar Road", "highway": "secondary", "road_class": "secondary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.6300, 23.0700], [72.6400, 23.0800], [72.6500, 23.0900],
        ]}, "properties": {"name": "Chandkheda Road", "highway": "secondary", "road_class": "secondary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.4900, 23.0000], [72.5000, 22.9900], [72.5100, 22.9800],
        ]}, "properties": {"name": "Bopal Road", "highway": "secondary", "road_class": "secondary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.6500, 23.2200], [72.6600, 23.2100], [72.6700, 23.2000],
        ]}, "properties": {"name": "Gandhinagar Sector Road", "highway": "primary", "road_class": "primary"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.6500, 22.9800], [72.6600, 22.9750], [72.6700, 22.9700],
        ]}, "properties": {"name": "Odhav Road", "highway": "secondary", "road_class": "secondary"}},
    ]
    return {"type": "FeatureCollection", "features": roads}



def highway_corridors_sample():
    features = [
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.3200, 22.8200], [72.3600, 22.8600], [72.4000, 22.9000],
            [72.4300, 22.9300], [72.4600, 22.9600], [72.4900, 22.9900],
            [72.5100, 23.0100], [72.5300, 23.0400], [72.5600, 23.0700],
            [72.5900, 23.1000], [72.6200, 23.1400], [72.6600, 23.1800],
            [72.7000, 23.2200], [72.7400, 23.2600], [72.7800, 23.3000],
        ]}, "properties": {"name": "NH-48 Delhi-Mumbai", "highway_class": "NH"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5700, 23.0200], [72.5800, 23.0500], [72.5900, 23.0800],
            [72.6000, 23.1100], [72.6100, 23.1400], [72.6200, 23.1700],
            [72.6300, 23.2000], [72.6400, 23.2300], [72.6500, 23.2600],
        ]}, "properties": {"name": "NH-147 Ahmedabad-Gandhinagar", "highway_class": "NH"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5800, 23.0300], [72.5400, 23.0200], [72.5000, 23.0100],
            [72.4600, 23.0000], [72.4200, 22.9900], [72.3800, 22.9800],
            [72.3400, 22.9700], [72.3000, 22.9600], [72.2600, 22.9500],
        ]}, "properties": {"name": "NH-947 Ahmedabad-Rajkot", "highway_class": "NH"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.4600, 22.9700], [72.4800, 22.9800], [72.5000, 22.9900],
            [72.5200, 23.0000], [72.5400, 23.0100], [72.5600, 23.0200],
            [72.5800, 23.0300], [72.6000, 23.0500], [72.6200, 23.0700],
            [72.6400, 23.0900], [72.6600, 23.1100], [72.6800, 23.1300],
            [72.7000, 23.1500],
        ]}, "properties": {"name": "SH-17 SGRD Highway", "highway_class": "SH"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5800, 22.8800], [72.5800, 22.9200], [72.5800, 22.9600],
            [72.5800, 23.0000], [72.5800, 23.0400], [72.5800, 23.0800],
            [72.5800, 23.1200], [72.5800, 23.1600], [72.5800, 23.2000],
            [72.5800, 23.2400], [72.5800, 23.2800],
        ]}, "properties": {"name": "SH-41 Ahmedabad-Mehsana", "highway_class": "SH"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5800, 23.0300], [72.6000, 23.0100], [72.6200, 22.9900],
            [72.6400, 22.9700], [72.6600, 22.9500], [72.6800, 22.9300],
            [72.7000, 22.9100], [72.7200, 22.8900],
        ]}, "properties": {"name": "SH-68 Ahmedabad-Vadodara", "highway_class": "SH"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [
            [72.5000, 23.0000], [72.4600, 22.9900], [72.4200, 22.9800],
            [72.3800, 22.9700], [72.3400, 22.9600], [72.3000, 22.9500],
        ]}, "properties": {"name": "SH-135 Sanand-Viramgam", "highway_class": "SH"}},
    ]
    return {"type": "FeatureCollection", "features": features}


def fuel_stations_sample():
    stations = [
        (72.3400, 22.8400, "HP - NH-48 Sanand South", "Hindustan Petroleum"),
        (72.3800, 22.8800, "Indian Oil - NH-48 Sanand", "Indian Oil"),
        (72.4200, 22.9200, "BPCL - NH-48 Sanand Junction", "Bharat Petroleum"),
        (72.4600, 22.9600, "HP - NH-48 Sarkhej", "Hindustan Petroleum"),
        (72.5000, 23.0000, "Indian Oil - NH-48 Makarba", "Indian Oil"),
        (72.5300, 23.0400, "BPCL - NH-48 Chandlodia", "Bharat Petroleum"),
        (72.5700, 23.0800, "HP - NH-48 Motera", "Hindustan Petroleum"),
        (72.6100, 23.1300, "Indian Oil - NH-48 Adalaj", "Indian Oil"),
        (72.6500, 23.1800, "BPCL - NH-48 Kalol South", "Bharat Petroleum"),
        (72.7000, 23.2300, "HP - NH-48 Kalol", "Hindustan Petroleum"),
        (72.7500, 23.2800, "Indian Oil - NH-48 Kalol North", "Indian Oil"),
        (72.5400, 23.0200, "BPCL - NH-947 Sarkhej", "Bharat Petroleum"),
        (72.5000, 23.0100, "HP - NH-947 Sanand Road", "Hindustan Petroleum"),
        (72.4600, 23.0000, "Indian Oil - NH-947 Sanand", "Indian Oil"),
        (72.4200, 22.9900, "BPCL - NH-947 Sanand West", "Bharat Petroleum"),
        (72.3800, 22.9800, "HP - NH-947 Viramgam Road", "Hindustan Petroleum"),
        (72.3400, 22.9700, "Indian Oil - NH-947 Viramgam", "Indian Oil"),
        (72.3000, 22.9600, "BPCL - NH-947 Viramgam West", "Bharat Petroleum"),
        (72.5800, 23.0500, "HP - NH-147 Chandkheda", "Hindustan Petroleum"),
        (72.6000, 23.0900, "Indian Oil - NH-147 Adalaj", "Indian Oil"),
        (72.6200, 23.1400, "BPCL - NH-147 Gandhinagar South", "Bharat Petroleum"),
        (72.6400, 23.1900, "HP - NH-147 Gandhinagar", "Hindustan Petroleum"),
        (72.6500, 23.2400, "Indian Oil - NH-147 Gandhinagar North", "Indian Oil"),
        (72.4700, 22.9750, "BPCL - SH-17 Sarkhej", "Bharat Petroleum"),
        (72.5100, 22.9950, "HP - SH-17 Makarba", "Hindustan Petroleum"),
        (72.5500, 23.0150, "Indian Oil - SH-17 Central", "Indian Oil"),
        (72.5900, 23.0400, "BPCL - SH-17 Chandlodia", "Bharat Petroleum"),
        (72.6300, 23.0800, "HP - SH-17 Chandkheda", "Hindustan Petroleum"),
        (72.6700, 23.1200, "Indian Oil - SH-17 Adalaj", "Indian Oil"),
        (72.7000, 23.1500, "BPCL - SH-17 East", "Bharat Petroleum"),
        (72.5800, 22.9200, "HP - SH-41 Vatva South", "Hindustan Petroleum"),
        (72.5800, 22.9600, "Indian Oil - SH-41 Vatva", "Indian Oil"),
        (72.5800, 23.0000, "BPCL - SH-41 Maninagar", "Bharat Petroleum"),
        (72.5800, 23.0400, "HP - SH-41 Paldi", "Hindustan Petroleum"),
        (72.5800, 23.0800, "Indian Oil - SH-41 Motera", "Indian Oil"),
        (72.5800, 23.1200, "BPCL - SH-41 Chandkheda", "Bharat Petroleum"),
        (72.5800, 23.1600, "HP - SH-41 Kadi Road", "Hindustan Petroleum"),
        (72.5800, 23.2000, "Indian Oil - SH-41 Gandhinagar", "Indian Oil"),
        (72.5800, 23.2400, "BPCL - SH-41 Mehsana Road", "Bharat Petroleum"),
        (72.6100, 23.0100, "HP - SH-68 Vatva", "Hindustan Petroleum"),
        (72.6400, 22.9700, "Indian Oil - SH-68 Narol", "Indian Oil"),
        (72.6700, 22.9400, "BPCL - SH-68 Bareja", "Bharat Petroleum"),
        (72.7000, 22.9100, "HP - SH-68 Kheda Road", "Hindustan Petroleum"),
        (72.5050, 23.0300, "HP - SG Highway", "Hindustan Petroleum"),
        (72.5100, 23.0150, "Indian Oil - Prahlad Nagar", "Indian Oil"),
        (72.5800, 23.0100, "BPCL - Paldi", "Bharat Petroleum"),
        (72.6100, 23.0500, "HP - Ghatlodia", "Hindustan Petroleum"),
        (72.5900, 22.9900, "BPCL - Maninagar", "Bharat Petroleum"),
        (72.6500, 22.9800, "HP - Odhav", "Hindustan Petroleum"),
        (72.4900, 23.0000, "Indian Oil - Bopal", "Indian Oil"),
        (72.5400, 23.0600, "BPCL - Thaltej", "Bharat Petroleum"),
        (72.6000, 23.0300, "Indian Oil - Naranpura", "Indian Oil"),
        (72.6700, 23.0800, "HP - Naroda", "Hindustan Petroleum"),
        (72.6600, 22.9700, "Indian Oil - Vatva", "Indian Oil"),
        (72.6500, 23.2200, "HP - Gandhinagar Sector 11", "Hindustan Petroleum"),
    ]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
         "properties": {"name": name, "brand": brand, "amenity": "fuel"}}
        for lon, lat, name, brand in stations
    ]}


def rest_stops_sample():
    stops = [
        (72.3500, 22.8500, "Sanand Highway Dhaba", "dhaba"),
        (72.3900, 22.8900, "Rajwadu Resort - NH-48", "dhaba"),
        (72.4300, 22.9300, "Sanand Junction Dhaba", "dhaba"),
        (72.4700, 22.9700, "Sarkhej Dhaba - NH-48", "dhaba"),
        (72.5100, 23.0100, "Makarba Rest Stop", "rest_area"),
        (72.5400, 23.0500, "Chandlodia Dhaba", "dhaba"),
        (72.5800, 23.0900, "Motera Highway Restaurant", "dhaba"),
        (72.6200, 23.1400, "Adalaj Dhaba", "dhaba"),
        (72.6600, 23.1900, "Kalol South Dhaba", "dhaba"),
        (72.7100, 23.2400, "Kalol Rest Area", "rest_area"),
        (72.7600, 23.2900, "Kalol North Dhaba", "dhaba"),
        (72.5300, 23.0200, "Sarkhej Dhaba - NH-947", "dhaba"),
        (72.4900, 23.0100, "Sanand Road Dhaba", "dhaba"),
        (72.4500, 23.0000, "Sanand Dhaba", "dhaba"),
        (72.4100, 22.9900, "Sanand West Dhaba", "dhaba"),
        (72.3700, 22.9800, "Viramgam Road Dhaba", "dhaba"),
        (72.3300, 22.9700, "Viramgam Dhaba", "dhaba"),
        (72.2900, 22.9600, "Viramgam West Rest Stop", "rest_area"),
        (72.5900, 23.0600, "Chandkheda Dhaba", "dhaba"),
        (72.6100, 23.1000, "Adalaj Highway Restaurant", "dhaba"),
        (72.6300, 23.1500, "Gandhinagar South Dhaba", "dhaba"),
        (72.6500, 23.2000, "Gandhinagar Rest Area", "rest_area"),
        (72.6600, 23.2500, "Gandhinagar North Dhaba", "dhaba"),
        (72.4600, 22.9700, "Sarkhej Dhaba - SH-17", "dhaba"),
        (72.5000, 22.9900, "Makarba Dhaba", "dhaba"),
        (72.5400, 23.0100, "SH-17 Central Dhaba", "dhaba"),
        (72.5900, 23.0400, "Chandlodia SH-17 Dhaba", "dhaba"),
        (72.6400, 23.0900, "Chandkheda SH-17 Dhaba", "dhaba"),
        (72.6800, 23.1300, "Adalaj SH-17 Rest Stop", "rest_area"),
        (72.7100, 23.1600, "SH-17 East Dhaba", "dhaba"),
        (72.5800, 22.9300, "Vatva South Dhaba", "dhaba"),
        (72.5800, 22.9700, "Vatva Dhaba", "dhaba"),
        (72.5800, 23.0100, "Maninagar Dhaba", "dhaba"),
        (72.5800, 23.0500, "Paldi Dhaba", "dhaba"),
        (72.5800, 23.0900, "Motera Dhaba", "dhaba"),
        (72.5800, 23.1300, "Chandkheda Dhaba SH-41", "dhaba"),
        (72.5800, 23.1700, "Kadi Road Dhaba", "dhaba"),
        (72.5800, 23.2100, "Gandhinagar Dhaba", "dhaba"),
        (72.5800, 23.2500, "Mehsana Road Rest Stop", "rest_area"),
        (72.6200, 23.0000, "Vatva SH-68 Dhaba", "dhaba"),
        (72.6500, 22.9600, "Narol Dhaba", "dhaba"),
        (72.6800, 22.9300, "Bareja Dhaba", "dhaba"),
        (72.7100, 22.9000, "Kheda Road Dhaba", "dhaba"),
        (72.5050, 23.0300, "Honest Restaurant - SG Highway", "dhaba"),
        (72.5900, 22.9900, "Maninagar City Dhaba", "dhaba"),
        (72.6500, 23.2200, "Gandhinagar Sector 11 Canteen", "rest_area"),
    ]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
         "properties": {"name": name, "stop_type": stop_type, "amenity": "restaurant"}}
        for lon, lat, name, stop_type in stops
    ]}


def ev_stations_sample():
    stations = [
        (72.5050, 23.0300, "Tata Power - Iscon Mega Mall SG Hwy", "Tata Power EZ Charge"),
        (72.5100, 23.0150, "Tata Power - Prahlad Nagar Garden", "Tata Power EZ Charge"),
        (72.5600, 23.0350, "Tata Power - Navrangpura", "Tata Power EZ Charge"),
        (72.6100, 23.0500, "Tata Power - Ghatlodia", "Tata Power EZ Charge"),
        (72.5000, 23.0450, "ChargeZone - Bodakdev", "ChargeZone"),
        (72.5400, 23.0600, "ChargeZone - Thaltej", "ChargeZone"),
        (72.6300, 23.0700, "ChargeZone - Chandkheda", "ChargeZone"),
        (72.4900, 23.0000, "ChargeZone - Bopal", "ChargeZone"),
        (72.5250, 23.0200, "Ather Grid - Satellite", "Ather Energy"),
        (72.5150, 23.0400, "Ather Grid - Vastrapur", "Ather Energy"),
        (72.5800, 23.0100, "Ather Grid - Paldi", "Ather Energy"),
        (72.6500, 23.2200, "GETCO EV Station - Gandhinagar Sec 11", "GETCO"),
        (72.6700, 23.2000, "GETCO EV Station - Gandhinagar Sec 21", "GETCO"),
        (72.6300, 23.2400, "ChargeZone - Gandhinagar Sec 28", "ChargeZone"),
        (72.4300, 22.9300, "Tata Power - NH-48 Sanand", "Tata Power EZ Charge"),
        (72.5100, 23.0100, "ChargeZone - NH-48 Makarba", "ChargeZone"),
        (72.6200, 23.1400, "Tata Power - NH-48 Adalaj", "Tata Power EZ Charge"),
        (72.7000, 23.2300, "ChargeZone - NH-48 Kalol", "ChargeZone"),
        (72.4600, 23.0000, "Tata Power - NH-947 Sanand", "Tata Power EZ Charge"),
        (72.3800, 22.9800, "ChargeZone - NH-947 Viramgam Road", "ChargeZone"),
        (72.5000, 22.9900, "Tata Power - SH-17 Makarba", "Tata Power EZ Charge"),
        (72.6400, 23.0900, "ChargeZone - SH-17 Chandkheda", "ChargeZone"),
        (72.5800, 23.1200, "Tata Power - SH-41 Chandkheda", "Tata Power EZ Charge"),
        (72.5800, 23.2000, "ChargeZone - SH-41 Gandhinagar", "ChargeZone"),
    ]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
         "properties": {"name": name, "operator": operator, "amenity": "charging_station"}}
        for lon, lat, name, operator in stations
    ]}


def risk_zones():
    zones = [
        (72.5780, 23.0500, 0.018, 0.120, "Sabarmati Floodplain North", "high", "low"),
        (72.5760, 23.0000, 0.018, 0.080, "Sabarmati Floodplain Central", "high", "low"),
        (72.5750, 22.9600, 0.018, 0.060, "Sabarmati Floodplain South", "high", "low"),
        (72.6600, 22.9700, 0.035, 0.025, "Vatva Low-lying", "high", "medium"),
        (72.6400, 22.9800, 0.030, 0.022, "Gomtipur Low-lying", "high", "low"),
        (72.5900, 23.0050, 0.030, 0.020, "Kankaria Lake Zone", "medium", "low"),
        (72.6100, 22.9850, 0.030, 0.020, "Chandola Lake Zone", "medium", "low"),
        (72.6700, 23.0800, 0.030, 0.022, "Naroda Drainage", "medium", "low"),
        (72.5500, 22.9800, 0.030, 0.022, "Isanpur Drainage", "medium", "low"),
        (72.5100, 23.0150, 0.035, 0.025, "Prahlad Nagar Elevated", "low", "low"),
        (72.5000, 23.0450, 0.035, 0.025, "Bodakdev Elevated", "low", "low"),
        (72.5400, 23.0600, 0.035, 0.025, "Thaltej Elevated", "low", "low"),
        (72.4900, 23.0000, 0.035, 0.025, "Bopal Elevated", "low", "low"),
        (72.5050, 23.0300, 0.040, 0.030, "SG Highway Elevated", "low", "low"),
        (72.6500, 23.2200, 0.060, 0.080, "Gandhinagar Planned", "low", "low"),
        (72.3800, 22.8800, 0.060, 0.040, "NH-48 Sanand Section", "low", "low"),
        (72.4600, 22.9600, 0.060, 0.040, "NH-48 Sarkhej Section", "low", "low"),
        (72.5400, 23.0500, 0.060, 0.040, "NH-48 Chandlodia Section", "low", "low"),
        (72.6500, 23.1800, 0.060, 0.040, "NH-48 Kalol Section", "low", "low"),
        (72.4500, 23.0000, 0.060, 0.040, "NH-947 Sanand Section", "low", "low"),
        (72.3500, 22.9700, 0.060, 0.040, "NH-947 Viramgam Section", "medium", "low"),
        (72.5000, 22.9900, 0.060, 0.040, "SH-17 Makarba Section", "low", "low"),
        (72.6500, 23.1000, 0.060, 0.040, "SH-17 Adalaj Section", "low", "low"),
        (72.5800, 22.9400, 0.020, 0.080, "SH-41 South Section", "medium", "low"),
        (72.5800, 23.1500, 0.020, 0.080, "SH-41 North Section", "low", "low"),
        (72.6500, 22.9500, 0.060, 0.040, "SH-68 Narol Section", "medium", "low"),
        (72.7000, 22.9100, 0.060, 0.040, "SH-68 Kheda Section", "low", "low"),
    ]
    return fc([feat(rect(lon, lat, w, h), {"zone_name": name, "flood_risk": flood, "terrain_risk": terrain})
               for lon, lat, w, h, name, flood, terrain in zones])

if __name__ == "__main__":
    save(city_boundaries(), "city_boundaries.geojson")
    save(ev_adoption_zones(), "ev_adoption_zones.geojson")
    save(income_zones(), "income_zones.geojson")
    save(population_zones(), "population_zones.geojson")
    save(risk_zones(), "risk_zones.geojson")
    save(highway_corridors_sample(), "highway_corridors_sample.geojson")
    save(ev_stations_sample(), "ev_stations_sample.geojson")
    save(fuel_stations_sample(), "fuel_stations_sample.geojson")
    save(rest_stops_sample(), "rest_stops_sample.geojson")
    save(city_roads_sample(), "city_roads.geojson")
    print("Data generation complete.")
