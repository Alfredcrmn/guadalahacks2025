import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

def validate_pois_within_tile(pois_df, tile_geom, streets_nav_gdf):
    """
    Calcula la geometría de cada POI interpolando su posición sobre el LINK_ID usando PERCFRREF.
    Luego verifica si cae dentro del tile.
    """
    # Asegura que el índice de calles esté por LINK_ID para acceso rápido
    streets_nav_gdf = streets_nav_gdf.set_index("link_id")

    geometries = []
    for _, row in pois_df.iterrows():
        link_id = row["LINK_ID"]
        perc = row.get("PERCFRREF", 50) / 100.0  # default: centro

        try:
            link_geom = streets_nav_gdf.loc[link_id].geometry
            poi_geom = link_geom.interpolate(perc, normalized=True)
        except KeyError:
            poi_geom = None  # El LINK_ID no existe
        geometries.append(poi_geom)

    # Asignar geometrías
    pois_df["geometry"] = geometries
    pois_gdf = gpd.GeoDataFrame(pois_df, geometry="geometry", crs="EPSG:4326")

    # Validar si están dentro del tile
    pois_gdf["inside_tile"] = pois_gdf["geometry"].apply(lambda geom: geom.within(tile_geom) if geom else False)

    return pois_gdf

def load_tile(tile_id: int, base_path: str = "data", export_errors: bool = True) -> dict:
    """
    Carga y valida los datos de un tile. Exporta errores si se encuentran POIs fuera del tile.
    """
    poi_path = os.path.join(base_path, "POIs", f"POI_{tile_id}.csv")
    nav_path = os.path.join(base_path, "STREETS_NAV", f"SREETS_NAV_{tile_id}.geojson")
    naming_path = os.path.join(base_path, "STREETS_NAMING_ADDRESSING", f"SREETS_NAMING_ADDRESSING_{tile_id}.geojson")
    tiles_path = os.path.join(base_path, "HERE_L11_Tiles.geojson")

    for path in [poi_path, nav_path, naming_path, tiles_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

    pois = pd.read_csv(poi_path)
    streets_nav = gpd.read_file(nav_path)
    naming = gpd.read_file(naming_path)
    tiles = gpd.read_file(tiles_path)

    tile_geom_row = tiles[tiles["L11_Tile_ID"] == tile_id]
    if tile_geom_row.empty:
        raise ValueError(f"No se encontró el tile_id {tile_id} en HERE_L11_Tiles.geojson")
    
    tile_geom = tile_geom_row.iloc[0].geometry
    pois = validate_pois_within_tile(pois, tile_geom, streets_nav)


    if export_errors:
        outside_pois = pois[pois["inside_tile"] == False]
        if not outside_pois.empty:
            os.makedirs("outputs", exist_ok=True)
            output_path = f"outputs/invalid_pois_{tile_id}.json"
            outside_pois[["POI_ID", "LINK_ID", "geometry"]].to_file(output_path, driver="GeoJSON")
            print(f"[INFO] {len(outside_pois)} POIs fuera del tile exportados a {output_path}")

    return {
        "tile_id": tile_id,
        "pois": pois,
        "streets_nav": streets_nav,
        "naming": naming,
        "tile_geom": tile_geom
    }
