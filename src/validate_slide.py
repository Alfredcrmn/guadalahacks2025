import os
import json
import math
from shapely.geometry import Point
from collections import Counter

def get_reference_node(line):
    coords = list(line.coords)
    first, last = coords[0], coords[-1]
    if first[1] < last[1]:
        return first, last
    elif first[1] > last[1]:
        return last, first
    else:
        return (first, last) if first[0] < last[0] else (last, first)

def determine_side(ref_node, non_ref_node, poi_point):
    ax, ay = non_ref_node[0] - ref_node[0], non_ref_node[1] - ref_node[1]
    bx, by = poi_point.x - ref_node[0], poi_point.y - ref_node[1]
    cross = ax * by - ay * bx
    return "L" if cross > 0 else "R"

def displace_point(poi_point, ref_node, non_ref_node, side="R", distance=5):
    dx = non_ref_node[0] - ref_node[0]
    dy = non_ref_node[1] - ref_node[1]
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return poi_point
    ux = -dy / length
    uy = dx / length
    factor = 1 if side == "L" else -1
    new_x = poi_point.x + factor * ux * (distance / 111320)
    new_y = poi_point.y + factor * uy * (distance / 111320)
    return Point(new_x, new_y)
#Función de validate
def validate_poi_side(tile_data):
    pois = tile_data["pois"]
    streets_nav = tile_data["streets_nav"]
    tile_id = int(tile_data["tile_id"])

    results = []
    processed_ids = set()
    streets_nav = streets_nav.set_index("link_id")

    for _, poi in pois.iterrows():
        try:
            poi_id = int(poi["POI_ID"])
            link_id = int(poi["LINK_ID"])
            expected_side = str(poi["POI_ST_SD"]).strip().upper()
            geometry = poi.geometry
        except Exception:
            continue

        if poi_id in processed_ids or not poi["inside_tile"]:
            continue
        processed_ids.add(poi_id)

        if link_id not in streets_nav.index:
            results.append({
                "tile_id": tile_id,
                "poi_id": poi_id,
                "link_id": link_id,
                "error_type": "invalid_link_reference",
                "description": "LINK_ID not found in street geometry",
                "suggestion": "Check if link ID is missing from base NAV data",
                "geometry": None
            })
            continue

        try:
            line = streets_nav.loc[link_id].geometry
            ref_node, non_ref_node = get_reference_node(line)

            displaced = displace_point(geometry, ref_node, non_ref_node, expected_side)
            actual_side = determine_side(ref_node, non_ref_node, displaced)

            if actual_side != expected_side:
                results.append({
                    "tile_id": tile_id,
                    "poi_id": poi_id,
                    "link_id": link_id,
                    "error_type": "wrong_side_of_street",
                    "description": f"POI expected on {expected_side} side, but is located on {actual_side}",
                    "suggestion": f"Update POI_ST_SD to '{actual_side}'",
                    "expected_side": expected_side,
                    "actual_side": actual_side,
                    "geometry": [float(geometry.x), float(geometry.y)] if geometry else None
                })

        except Exception as e:
            results.append({
                "tile_id": tile_id,
                "poi_id": poi_id,
                "link_id": link_id,
                "error_type": "geometry_processing_error",
                "description": str(e),
                "suggestion": "Check geometry or input values",
                "geometry": None
            })

    side_errors = [
        (e["expected_side"], e["actual_side"])
        for e in results
        if e["error_type"] == "wrong_side_of_street"
    ]
    pattern_counts = Counter(side_errors)
    if pattern_counts:
        print(f"[INFO] Side error patterns in tile {tile_id}:")
        for pattern, count in pattern_counts.items():
            print(f"  - {pattern[0]} → {pattern[1]}: {count}")

    bad_assignments = {
        "R_expected_but_L_actual": 0,
        "L_expected_but_R_actual": 0,
        "total_R": 0,
        "total_L": 0,
    }

    for e in results:
        if e["error_type"] != "wrong_side_of_street":
            continue
        expected = e.get("expected_side")
        actual = e.get("actual_side")
        if expected == "R":
            bad_assignments["total_R"] += 1
            if actual == "L":
                bad_assignments["R_expected_but_L_actual"] += 1
        elif expected == "L":
            bad_assignments["total_L"] += 1
            if actual == "R":
                bad_assignments["L_expected_but_R_actual"] += 1

    print(f"[INFO] POI_ST_SD misassignments in tile {tile_id}:")
    print(f"  → R but actually L: {bad_assignments['R_expected_but_L_actual']} / {bad_assignments['total_R']}")
    print(f"  → L but actually R: {bad_assignments['L_expected_but_R_actual']} / {bad_assignments['total_L']}")

    return results

def export_validation_results(results, tile_id):
    if not results:
        print(f"[INFO] No side errors found in tile {tile_id}")
        return

    output_dir = os.path.join("../outputs", "validation_side")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"errors_{tile_id}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"[INFO] {len(results)} side errors exported to {output_path}")
