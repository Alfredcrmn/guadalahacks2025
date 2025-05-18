import os
import geopandas as gpd
from loader import load_tile
from validate_multidigit import validate_multidigit

# Ruta absoluta al proyecto
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Cargar lista de tiles desde geojson
tiles_path = os.path.join(DATA_DIR, "HERE_L11_Tiles.geojson")
tiles_gdf = gpd.read_file(tiles_path)
tile_ids = sorted(tiles_gdf["L11_Tile_ID"].unique())

# Filtrar los tiles que tienen POI disponible
tile_ids_with_data = [
    tid for tid in tile_ids if os.path.exists(os.path.join(DATA_DIR, "POIs", f"POI_{tid}.csv"))
]

print(f"Tiles únicos en el geojson: {len(tile_ids)}")
print(f"Tiles con archivo POI disponible: {len(tile_ids_with_data)}\n")

for tile_id in tile_ids_with_data:
    print(f"Tile {tile_id}")
    try:
        tile_data = load_tile(tile_id, base_path=DATA_DIR)

        validate_multidigit(tile_id, tile_data)


        total = len(tile_data["pois"])
        inside = tile_data["pois"]["inside_tile"].sum()
        outside = total - inside
        print(f"POIs totales: {total}")
        print(f"Dentro del tile: {inside}")
        print(f"Fuera del tile: {outside}\n")
    except Exception as e:
        print(f"Error con tile {tile_id}: {e}\n")
