# src/validate_existence.py

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

SIDE_LEFT = "L"
SIDE_RIGHT = "R"

def validate_existence(loader_data: dict) -> gpd.GeoDataFrame:
    pois = loader_data["pois"].copy()
    streets = loader_data["streets_nav"]
    tile_geom = loader_data["tile_geom"]

    # Filtrar solo calles marcadas como MULTIDIGIT
    if "MULTIDIGIT" not in streets.columns:
        raise KeyError("MULTIDIGIT column missing in streets_nav")

    multig_links = streets[streets["MULTIDIGIT"] == "Y"]
    multig_links = multig_links.set_index("link_id")

    results = []

    for _, row in pois.iterrows():
        link_id = row.get("LINK_ID")
        poi_geom = row.geometry
        perc = row.get("PERCFRREF", 50) / 100.0  # default center
        side = row.get("POI_ST_SD")

        if pd.isna(link_id) or poi_geom is None or poi_geom.is_empty:
            error_type = "INVALID_GEOMETRY"
            suggestion = "Missing geometry or link_id"
        elif link_id not in multig_links.index:
            error_type = "NOT_MULTIDIGIT"
            suggestion = "Associated link is not MULTIDIGIT"
        else:
            link_geom = multig_links.loc[link_id].geometry
            # Interpolar posición teórica a lo largo del link
            try:
                projected_point = link_geom.interpolate(perc, normalized=True)
                # Si está dentro del tile, y cae sobre MULTIDIGIT válido
                if tile_geom.contains(poi_geom):
                    error_type = "LEGITIMATE_EXCEPTION"
                    suggestion = "POI correctly placed within MULTIDIGIT link"
                else:
                    error_type = "OUTSIDE_TILE"
                    suggestion = "POI outside tile bounds"
            except Exception as e:
                error_type = "ERROR"
                suggestion = f"Interpolation failed: {str(e)}"

        results.append({
            **row.to_dict(),
            "error_type": error_type,
            "suggestion": suggestion
        })

    return gpd.GeoDataFrame(results, geometry="geometry", crs=pois.crs)
