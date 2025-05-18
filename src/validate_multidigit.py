import os
import json
import geopandas as gpd
import pandas as pd

def find_closest_parallel_segment(link_row, nav_gdf, naming_with_nav_df, min_dist=0.1, max_dist=200):
    link_id = link_row["link_id"]
    this_geom = link_row["geometry"]
    if "DIR_TRAVEL" not in link_row.index or pd.isna(link_row["DIR_TRAVEL"]):
        print(f"[DEBUG] Link {link_id} has no DIR_TRAVEL value")
        return None, None
    this_dir = link_row["DIR_TRAVEL"]

    if this_dir not in ("T", "F"):
        print(f"[DEBUG] Link {link_id} has DIR_TRAVEL={this_dir}, not 'T' or 'F'")
        return None, None

    # Get the street name directly from naming_with_nav_df
    row_name_match = naming_with_nav_df[naming_with_nav_df["link_id"] == link_id]
    if row_name_match.empty or "ST_NAME" not in row_name_match.columns:
        print(f"[DEBUG] Link {link_id} has no matching ST_NAME in naming_with_nav_df")
        return None, None

    st_name = row_name_match.iloc[0]["ST_NAME"]
    st_name = st_name.strip().upper() if isinstance(st_name, str) else ""
    
    if not st_name:
        print(f"[DEBUG] Link {link_id} has empty ST_NAME")
        return None, None

    # Ensure ST_NAME is normalized in the naming_with_nav_df
    naming_with_nav_copy = naming_with_nav_df.copy()
    naming_with_nav_copy["ST_NAME"] = naming_with_nav_copy["ST_NAME"].astype(str).str.strip().str.upper()

    opposite_dir = "F" if this_dir == "T" else "T" if this_dir == "F" else None
    if not opposite_dir:
        print(f"[DEBUG] Could not determine opposite direction for {this_dir}")
        return None, None

    # Verify DIR_TRAVEL exists in naming_with_nav_df
    if "DIR_TRAVEL" not in naming_with_nav_copy.columns:
        print(f"[ERROR] naming_with_nav no contiene DIR_TRAVEL — omitiendo link_id {link_id}")
        return None, None

    candidates = naming_with_nav_copy[
        (naming_with_nav_copy["ST_NAME"] == st_name) &
        (naming_with_nav_copy["DIR_TRAVEL"] == opposite_dir) &
        (naming_with_nav_copy["link_id"] != link_id)
    ]
    
    print(f"[DEBUG] For link {link_id} with dir {this_dir}, found {len(candidates)} candidates with opposite dir {opposite_dir} and same name '{st_name}'")

    if candidates.empty or "geometry" not in candidates.columns:
        return None, None

    # Transform to EPSG:3857 for accurate distance calculations
    seg_geom_3857 = gpd.GeoSeries([this_geom], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
    candidates_3857 = gpd.GeoDataFrame(candidates.copy(), geometry="geometry", crs="EPSG:4326").to_crs("EPSG:3857")

    # Add debug for the first few candidates:
    print(f"[DEBUG] Distance calculation for link {link_id}:")
    min_found_dist = float("inf")
    for i, (_, cand) in enumerate(candidates_3857.iterrows()):
        if i < 5:  # Only check first 5 candidates for debug
            dist = seg_geom_3857.distance(cand.geometry)
            print(f"[DEBUG]   Distance to candidate {cand['link_id']}: {dist:.2f}m")
            min_found_dist = min(min_found_dist, dist)
    print(f"[DEBUG]   Min distance found: {min_found_dist:.2f}m (threshold: {min_dist}-{max_dist}m)")

    # Count how many candidates are within distance thresholds
    candidates_in_range = 0
    candidates_parallel = 0
    candidates_both = 0

    for _, cand in candidates_3857.iterrows():
        dist = seg_geom_3857.distance(cand.geometry)
        is_in_range = min_dist <= dist <= max_dist
        is_parallel = is_roughly_parallel(this_geom, cand.geometry)
        
        if is_in_range:
            candidates_in_range += 1
        if is_parallel:
            candidates_parallel += 1
        if is_in_range and is_parallel:
            candidates_both += 1

    print(f"[DEBUG] Candidates: {len(candidates_3857)} total, {candidates_in_range} in range, {candidates_parallel} parallel, {candidates_both} both")
    
    # Add visualization here:
    static_counter = getattr(find_closest_parallel_segment, "counter", [0])
    if len(candidates_3857) > 10 and candidates_both == 0 and static_counter[0] < 3:
        visualize_example(link_id, this_geom, candidates, tile_id, output_dir="outputs/debug_maps")
        static_counter[0] += 1
    find_closest_parallel_segment.counter = static_counter

    closest = None
    closest_dist = float("inf")
    for _, cand in candidates_3857.iterrows():
        dist = seg_geom_3857.distance(cand.geometry)
        if min_dist <= dist <= max_dist and dist < closest_dist:
            # Check if segments are roughly parallel
            if is_roughly_parallel(this_geom, cand.geometry):
                closest = cand
                closest_dist = dist

    if closest is not None:
        print(f"[INFO] Found valid multidigit pair for link {link_id}! Distance: {closest_dist:.2f}m")
        return closest, closest_dist
    else:
        print(f"[ERROR] No valid multidigit pair found for link {link_id} with MULTIDIGIT=Y")
        return None, None

def get_multidigit_segments(streets_nav_gdf):
    """
    Retorna un GeoDataFrame con los segmentos donde MULTIDIGIT = Y
    """
    return streets_nav_gdf[streets_nav_gdf["MULTIDIGIT"] == "Y"].copy()


def validate_multidigit(tile_id, tile_data, export=True):
    """
    Valida si los segmentos con MULTIDIGIT=Y tienen pares válidos.
    """
    # Add debugging at beginning of function
    streets_nav = tile_data["streets_nav"]
    multidigit_segments = streets_nav[streets_nav["MULTIDIGIT"] == "Y"]
    print(f"\n[DEBUG] Found {len(multidigit_segments)} segments with MULTIDIGIT=Y in tile {tile_id}")

    # Check MULTIDIGIT column presence
    if "MULTIDIGIT" not in streets_nav.columns:
        possible_columns = [col for col in streets_nav.columns if col.upper() == "MULTIDIGIT"]
        if possible_columns:
            print(f"[DEBUG] Found MULTIDIGIT column as {possible_columns[0]}, not 'MULTIDIGIT'")
            streets_nav["MULTIDIGIT"] = streets_nav[possible_columns[0]]
        else:
            print(f"[WARNING] No MULTIDIGIT column found in streets_nav!")
            return []
            
    # Print sample data for first few segments
    for i, (_, row) in enumerate(multidigit_segments.iterrows()):
        if i < 5:  # Just print first 5 for debugging
            link_id = row["link_id"]
            print(f"[DEBUG] Sample MULTIDIGIT segment: link_id={link_id}, DIR_TRAVEL={row.get('DIR_TRAVEL', 'N/A')}")
            
            # Find street name
            name_match = tile_data["naming_with_nav"][tile_data["naming_with_nav"]["link_id"] == link_id]
            if not name_match.empty and "ST_NAME" in name_match.columns:
                print(f"[DEBUG]   Street name: {name_match.iloc[0]['ST_NAME']}")
                
    results = []
    for _, row in multidigit_segments.iterrows():
        if _ % 20 == 0:
            print(f"[DEBUG] Procesando segmento {_ + 1} de {len(multidigit_segments)} en tile {tile_id}")
        closest, dist = find_closest_parallel_segment(
            row, 
            streets_nav, 
            tile_data["naming_with_nav"],
            min_dist=0.1,   # Practically no minimum
            max_dist=200    # Very wide maximum
        )

        if closest is None:
            link_id = int(row["link_id"])
            coords = list(map(list, row["geometry"].coords)) if row["geometry"] else None

            results.append({
                "tile_id": int(tile_id),
                "poi_id": None,
                "link_id": link_id,
                "error_type": "incorrect_multidigit_attribution",
                "description": "Segment marked as MULTIDIGIT=Y but no valid parallel segment with opposite direction and same name found within 500m",
                "suggestion": "Update MULTIDIGIT to 'N'",
                "geometry": coords
            })

    print(f"[DEBUG] Tile {tile_id} - errores encontrados: {len(results)}")

    if export:
        output_dir = "outputs/validation_multidigit"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"errors_{tile_id}.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[MULTIDIGIT] Exported {len(results)} entries for tile {tile_id} → {output_path}")

    valid_pairs_found = len(multidigit_segments) - len(results)
    if valid_pairs_found > 0:
        print(f"[SUMMARY] Tile {tile_id} tuvo {valid_pairs_found} segmentos con pareja válida")
    else:
        print(f"[SUMMARY] Tile {tile_id} no tuvo ningún segmento con pareja válida")

    count_multidigit = len(multidigit_segments)
    count_valid = count_multidigit - len(results)
    count_errors = len(results)

    # At end of function, add stat summary
    print(f"\nResults for tile {tile_id}:")
    print(f"Total multidigit segments analyzed: {count_multidigit}")
    print(f"Valid multidigit pairs found: {count_valid}")
    print(f"Invalid multidigit segments (errors): {count_errors}")

    return results

# 1. Add is_roughly_parallel function
def is_roughly_parallel(line1, line2, max_angle_diff=60):  # Even more lenient - 60 degrees
    """Check if two lines are roughly parallel"""
    from shapely.geometry import LineString
    import numpy as np
    
    # Get direction vector for first line
    p1, p2 = line1.coords[0], line1.coords[-1]
    v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    # Normalize
    if np.linalg.norm(v1) != 0:
        v1 = v1 / np.linalg.norm(v1)
    else:
        return False
    
    # Get direction vector for second line
    p1, p2 = line2.coords[0], line2.coords[-1]
    v2 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    # Normalize
    if np.linalg.norm(v2) != 0:
        v2 = v2 / np.linalg.norm(v2)
    else:
        return False
    
    # Calculate angle between vectors
    dot_product = np.dot(v1, v2)
    # Clamp to handle floating point errors
    dot_product = np.clip(dot_product, -1.0, 1.0)
    angle_rad = np.arccos(np.abs(dot_product))
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg <= max_angle_diff

def visualize_example(link_id, segment_geom, candidates, tile_id, output_dir="outputs/debug_maps"):
    """Create a simple HTML map to visualize a segment and its candidates"""
    import folium
    import os
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get centroid for map center
    center = [segment_geom.centroid.y, segment_geom.centroid.x]
    
    # Create map
    m = folium.Map(location=center, zoom_start=15)
    
    # Add segment in red
    folium.GeoJson(
        segment_geom,
        style_function=lambda x: {'color': 'red', 'weight': 4}
    ).add_to(m)
    
    # Add all candidates in blue
    for _, cand in candidates.iterrows():
        folium.GeoJson(
            cand.geometry,
            style_function=lambda x: {'color': 'blue', 'weight': 2}
        ).add_to(m)
    
    # Save map
    m.save(f"{output_dir}/link_{link_id}_tile_{tile_id}.html")
    print(f"[DEBUG] Created debug map for link {link_id} at {output_dir}/link_{link_id}_tile_{tile_id}.html")

    # Create map for first 3 segments with candidates but no valid match
    static_counter = getattr(find_closest_parallel_segment, "counter", [0])
    if len(candidates) > 10 and min_found_dist > 0 and static_counter[0] < 3:
        visualize_example(link_id, this_geom, candidates, tile_id, output_dir="outputs/debug_maps")
        static_counter[0] += 1
    find_closest_parallel_segment.counter = static_counter