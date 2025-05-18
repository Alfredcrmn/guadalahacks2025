import os
import json
import math
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString

def angle_from_linestring(line):
    coords = list(line.coords)
    if len(coords) < 2:
        return None
    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    return math.atan2(y2 - y1, x2 - x1)

def is_parallel_and_within_distance(line1, line2, angle_tol_deg=20, min_dist=3, max_dist=80):
    if line1.is_empty or line2.is_empty:
        return False
    angle1 = angle_from_linestring(line1)
    angle2 = angle_from_linestring(line2)
    if angle1 is None or angle2 is None:
        return False
    angle_diff = abs(math.degrees(angle1 - angle2)) % 180
    angle_diff = min(angle_diff, 180 - angle_diff)
    if angle_diff > angle_tol_deg:
        return False
    dist = line1.distance(line2) * 111320  # grados a metros
    return min_dist <= dist <= max_dist

def load_tile_nav_and_names(tile_id, base_path="data"):
    nav_path = os.path.join(base_path, "STREETS_NAV", f"SREETS_NAV_{tile_id}.geojson")
    naming_path = os.path.join(base_path, "STREETS_NAMING_ADDRESSING", f"SREETS_NAMING_ADDRESSING_{tile_id}.geojson")
    if not os.path.exists(nav_path) or not os.path.exists(naming_path):
        raise FileNotFoundError("Nav o Naming file no encontrado.")
    nav = gpd.read_file(nav_path)
    naming = gpd.read_file(naming_path)
    nav["MULTIDIGIT"] = nav["MULTIDIGIT"].astype(str).str.strip().str.upper()
    nav["FUNC_CLASS"] = nav["FUNC_CLASS"].astype(str).str.strip()
    nav["LANE_CAT"] = nav["LANE_CAT"].astype(str).str.strip()
    nav["DIVIDER"] = nav["DIVIDER"].astype(str).str.strip().str.upper()
    naming["ST_NAME"] = naming["ST_NAME"].astype(str).str.strip().str.upper()
    merged = nav.merge(naming[["link_id", "ST_NAME"]], on="link_id", how="left")
    return merged

def find_multidigit_errors(tile_id, base_path="data"):
    merged = load_tile_nav_and_names(tile_id, base_path)
    print(f"[DEBUG] Original links: {len(merged)}")

    # Solo descartar si ambos FUNC_CLASS=5 y LANE_CAT=1
    merged = merged[~((merged["FUNC_CLASS"] == "5") & (merged["LANE_CAT"] == "1"))]
    print(f"[DEBUG] After filtering FUNC_CLASS=5 & LANE_CAT=1: {len(merged)}")

    merged = merged[merged["ST_NAME"].notna()]
    street_groups = merged.groupby("ST_NAME")
    suspicious_pairs = []

    for st_name, group in street_groups:
        group = group.reset_index(drop=True)
        for i in range(len(group)):
            line1 = group.loc[i].geometry
            link1 = group.loc[i].link_id
            m1 = group.loc[i]["MULTIDIGIT"]
            d1 = group.loc[i]["DIVIDER"]
            len1 = line1.length * 111320

            for j in range(i + 1, len(group)):
                line2 = group.loc[j].geometry
                link2 = group.loc[j].link_id
                m2 = group.loc[j]["MULTIDIGIT"]
                d2 = group.loc[j]["DIVIDER"]
                len2 = line2.length * 111320

                # Tolerar tramos cortos si alguno tiene DIVIDER
                if (len1 < 40 or len2 < 40) and not ("Y" in (d1, d2)):
                    continue

                if is_parallel_and_within_distance(line1, line2):
                    if m1 == "N" or m2 == "N":
                        suspicious_pairs.append({
                            "tile_id": tile_id,
                            "link1": int(link1),
                            "link2": int(link2),
                            "st_name": st_name,
                            "MULTIDIGIT_link1": m1,
                            "MULTIDIGIT_link2": m2,
                            "DIVIDER_link1": d1,
                            "DIVIDER_link2": d2,
                            "note": "unverified_divider" if (d1 != "Y" and d2 != "Y") else "confirmed_divider"
                        })
    return suspicious_pairs

if __name__ == "__main__":
    TILE_ID = 4815075  # cámbialo según el tile a probar
    results = find_multidigit_errors(TILE_ID)

    print(f"[INFO] Found {len(results)} suspicious MULTIDIGIT pairs in tile {TILE_ID}")
    for r in results[:10]:
        print(f"  → {r['link1']} ⬌ {r['link2']} ({r['st_name']}) [{r['note']}]")

    # Exportar resultados
    os.makedirs("outputs", exist_ok=True)
    out_path = f"outputs/multidigit_candidates_{TILE_ID}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[INFO] Exported to {out_path}")
