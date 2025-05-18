import os
import json
import geopandas as gpd

# Rutas base
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_PATH = os.path.join(ROOT_DIR, "dashboard", "tiles.json")

# Leer geojson de tiles
tiles_path = os.path.join(DATA_DIR, "HERE_L11_Tiles.geojson")
tiles_gdf = gpd.read_file(tiles_path)
tile_ids = sorted(tiles_gdf["L11_Tile_ID"].unique())

# Filtrar solo los que tienen archivo de POIs
tile_ids_with_data = [
    tid for tid in tile_ids if os.path.exists(os.path.join(DATA_DIR, "POIs", f"POI_{tid}.csv"))
]

# Convertir a int nativo (evita error al hacer dump)
tile_ids_clean = [int(tid) for tid in tile_ids_with_data]

# Exportar como JSON
with open(OUTPUT_PATH, "w") as f:
    json.dump(tile_ids_clean, f, indent=2)

print(f"✅ Exported {len(tile_ids_clean)} tile IDs to {OUTPUT_PATH}")
