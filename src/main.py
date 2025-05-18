# src/main.py

import os
import geopandas as gpd

from loader import load_tile
from validate_existence import validate_existence

# ── CONFIG ────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))    # src/
PROJECT_ROOT = os.path.dirname(ROOT_DIR)                 # project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
POI_SUBDIR = os.path.join(DATA_DIR, "POIs")
TILES_GEOJSON = os.path.join(DATA_DIR, "HERE_L11_Tiles.geojson")

# outputs for existence validator
EXIST_OUT = os.path.join(PROJECT_ROOT, "outputs", "existence")
# keep your old style summary (no files written)
# we'll still create OUTPUT_DIR if not exist
os.makedirs(EXIST_OUT, exist_ok=True)
# ──────────────────────────────────────────────────────────────────────────

def find_tile_ids_with_pois():
    """Return sorted list of tile IDs for which a POI CSV exists."""
    tiles_gdf = gpd.read_file(TILES_GEOJSON)
    all_tiles = sorted(tiles_gdf["L11_Tile_ID"].unique())
    has_poi = [
        tid for tid in all_tiles
        if os.path.exists(os.path.join(POI_SUBDIR, f"POI_{tid}.csv"))
    ]
    return has_poi

def run_tile_reports(tile_id: int):
    """1) Your original load & inside/outside summary
       2) Existence‐validation + GeoJSON dump."""
    print(f"\n▶ Tile {tile_id}")

    # ----- PART 1: load_tile summary -----
    try:
        tile_data = load_tile(tile_id, base_path=DATA_DIR)
        total = len(tile_data["pois"])
        inside = tile_data["pois"]["inside_tile"].sum()
        outside = total - inside

        print(f"  • POIs total : {total}")
        print(f"  • Inside tile: {inside}")
        print(f"  • Outside    : {outside}")
    except Exception as e:
        print(f"⚠️  load_tile error: {e}")

    # ----- PART 2: existence‐validation -----
    try:
        exist_gdf = validate_existence(tile_data)
        out_path = os.path.join(EXIST_OUT, f"existence_{tile_id}.geojson")
        exist_gdf.to_file(out_path, driver="GeoJSON")
        print(f"  • Existence report written to: {out_path}")

        # Optional quick counts
        counts = exist_gdf["error_type"].value_counts()
        for etype, cnt in counts.items():
            print(f"    {etype:16s}: {cnt}")
    except Exception as e:
        print(f"⚠️  validate_existence error: {e}")

def main():
    tile_ids = find_tile_ids_with_pois()
    print(f"Found {len(tile_ids)} tiles with POI files: {tile_ids}")

    for tid in tile_ids:
        run_tile_reports(tid)

if __name__ == "__main__":
    main()
