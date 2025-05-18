import os
import geopandas as gpd
from loader import load_tile
from validate_slide import validate_poi_side, export_validation_results
from validate_multidigit import validate_multidigit
from validate_existence import validate_existence
import traceback


# Ruta absoluta al proyecto
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Cargar lista de tiles desde geojson
tiles_path = os.path.join(DATA_DIR, "HERE_L11_Tiles.geojson")
tiles_gdf = gpd.read_file(tiles_path)
tile_ids = sorted(tiles_gdf["L11_Tile_ID"].unique())

EXIST_OUT = os.path.join(DATA_DIR, "outputs", "existence")
os.makedirs(EXIST_OUT, exist_ok=True)

# Filtrar los tiles que tienen POI disponible
tile_ids_with_data = [
    tid for tid in tile_ids if os.path.exists(os.path.join(DATA_DIR, "POIs", f"POI_{tid}.csv"))
]

print(f"Tiles únicos en el geojson: {len(tile_ids)}")
print(f"Tiles con archivo POI disponible: {len(tile_ids_with_data)}\n")

for tile_id in tile_ids_with_data:
    print("\n-------------------------------------------------------------")
    print(f"Tile {tile_id}")
    try:
        tile_data = load_tile(tile_id, base_path=DATA_DIR)
        total = len(tile_data["pois"])
        inside = tile_data["pois"]["inside_tile"].sum()
        outside = total - inside
        print(f"POIs totales: {total}")
        print(f"Dentro del tile: {inside}")
        print(f"Fuera del tile: {outside}\n")
        # Ejecutar Módulo 2: Validación de lado de calle
        results = validate_poi_side(tile_data)
        export_validation_results(results, tile_id)
        
        # Módulo 3 (MULTIDIGIT)
        validate_multidigit(tile_data)
        
        # Módulo 4 (EXISTENCE)
        exist_gdf = validate_existence(tile_data)
        out_path = os.path.join(EXIST_OUT, f"existence_{tile_id}.geojson")
        exist_gdf.to_file(out_path, driver="GeoJSON")
        print(f"  • Existence report written to: {out_path}")

        # Optional quick counts
        counts = exist_gdf["error_type"].value_counts()
        for etype, cnt in counts.items():
            print(f"    {etype:16s}: {cnt}")
        
    except Exception as e:
        print(f"[ERROR] Tile {tile_id} failed:\n{traceback.format_exc()}")