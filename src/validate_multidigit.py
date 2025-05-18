import os
import json
import math
from shapely.geometry import LineString, MultiLineString
from shapely.strtree import STRtree

def normalize_line_geometry(geom):
    if isinstance(geom, LineString):
        return geom
    if isinstance(geom, MultiLineString):
        coords = []
        for part in geom.geoms:
            coords.extend(part.coords)
        return LineString(coords) if coords else None
    return None

def angle_from_linestring(line):
    coords = list(line.coords)
    if len(coords) < 2:
        return None
    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    return math.atan2(y2 - y1, x2 - x1)

def is_parallel_and_within_distance(line1, line2,
                                   angle_tol_deg=45,
                                   min_dist=0,
                                   max_dist=200):
    a1 = angle_from_linestring(line1)
    a2 = angle_from_linestring(line2)
    if a1 is None or a2 is None:
        return False
    diff = abs(math.degrees(a1 - a2)) % 180
    diff = min(diff, 180 - diff)
    if diff > angle_tol_deg:
        return False
    dist = line1.distance(line2) * 111_320
    return 0 <= dist <= max_dist


def score_link(row, min_length=20):
    s = 0
    if row.get("DIVIDER") == "Y":
        s += 2
    if str(row.get("FUNC_CLASS", "5")).strip() not in ("5", ""):
        s += 1
    if str(row.get("LANE_CAT", "1")).strip() != "1":
        s += 1
    if row.geometry.length * 111_320 > min_length:
        s += 1
    if str(row.get("SPEED_CAT", "0")).isdigit() and int(row["SPEED_CAT"]) >= 5:
        s += 1
    if row.get("TOLLWAY") == "Y":
        s += 1
    if row.get("URBAN") == "N":
        s += 0.5
    return s

def validate_multidigit(tile_data):
    tile_id = tile_data["tile_id"]
    nav     = tile_data["streets_nav"]
    naming  = tile_data["naming"]

    nav["MULTIDIGIT"] = nav["MULTIDIGIT"].astype(str).str.strip().str.upper()
    naming["ST_NAME"] = naming["ST_NAME"].astype(str).str.strip().str.upper()

    naming = naming[["link_id", "ST_NAME"]].copy()
    nav = nav.copy()

    merged = nav.merge(naming, on="link_id", how="left").dropna(subset=["ST_NAME"])
    merged["geometry"] = merged["geometry"].apply(normalize_line_geometry)
    merged = merged.dropna(subset=["geometry"])

    output = []
    st_groups = merged.groupby("ST_NAME")

    total_groups = 0
    groups_with_both = 0
    total_evals = 0

    SCORE_THRESHOLD = 4.0

    for st_name, grp in st_groups:
        total_groups += 1
        grp_n = grp[grp["MULTIDIGIT"] == "N"]
        grp_y = grp[grp["MULTIDIGIT"] == "Y"]
        if grp_n.empty or grp_y.empty:
            continue
        groups_with_both += 1

        geoms_with_data = []
        for _, row in grp_y.iterrows():
            geom = row.geometry
            if geom is not None:
                geoms_with_data.append((geom, row))

        if not geoms_with_data:
            continue

        geoms_only = [g for g, _ in geoms_with_data]
        idx_y = STRtree(geoms_only)
        geom_to_row = dict(geoms_with_data)

        for _, row_n in grp_n.iterrows():
            line_n = row_n.geometry
            cands = [g for g in geoms_only if line_n.distance(g) * 111_320 <= 200]




            for gY in cands:
                row_y = geom_to_row.get(gY)
                if row_y is None:
                    continue
                if is_parallel_and_within_distance(line_n, gY):
                    total_evals += 1
                    score = (score_link(row_n) + score_link(row_y)) / 2
                    if score >= SCORE_THRESHOLD:
                        output.append({
                            "tile_id": int(tile_id),
                            "poi_id": None,
                            "link_id": int(row_n.link_id),
                            "error_type": "potential_multidigit_false_negative",
                            "description": (
                                f"Parallel segment {int(row_y.link_id)} "
                                f"seems to need MULTIDIGIT=Y (score={score:.1f})"
                            ),
                            "suggestion": "Consider setting MULTIDIGIT to 'Y'",
                            "geometry": list(line_n.centroid.coords)[0]
                        })
                        break

    out_dir = os.path.join("../outputs", "validation_multidigit")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"errors_{tile_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"[DEBUG] total ST_NAME groups: {total_groups}")
    print(f"[DEBUG] groups with both N & Y: {groups_with_both}")
    print(f"[DEBUG] total N–Y pairs evaluated: {total_evals}")
    if output:
        print(f"[INFO] Exported {len(output)} MULTIDIGIT candidates to {out_path}")
    else:
        print(f"[INFO] No MULTIDIGIT issues found for tile {tile_id}")

    return output
