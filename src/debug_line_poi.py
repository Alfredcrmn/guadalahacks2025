import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import folium

def debug_line_poi(tile_id, poi_id, base_path="../data"):
    poi_path = f"{base_path}/POIs/POI_{tile_id}.csv"
    nav_path = f"{base_path}/STREETS_NAV/SREETS_NAV_{tile_id}.geojson"

    # 1. Cargar datos
    pois_df = pd.read_csv(poi_path)
    streets_gdf = gpd.read_file(nav_path)

    # 2. Buscar el POI
    try:
        poi = pois_df.loc[pois_df["POI_ID"] == poi_id].iloc[0]
    except IndexError:
        print(f"[ERROR] POI_ID {poi_id} no encontrado en tile {tile_id}")
        return

    # 3. Interpretar PERCFRREF
    link_id = poi["LINK_ID"]
    perc_raw = poi.get("PERCFRREF", 50)
    perc = pd.to_numeric(perc_raw, errors="coerce")
    if pd.isna(perc):
        perc = 50
    perc = max(0, min(100, perc)) / 100.0

    # 4. Encontrar la calle asociada
    street_row_df = streets_gdf[streets_gdf["link_id"] == link_id]
    if street_row_df.empty:
        print(f"[ERROR] LINK_ID {link_id} no encontrado")
        return
    street = street_row_df.iloc[0]
    line = street.geometry

    # 5. Normalizar DIR_TRAVEL
    raw_dir = street.get("DIR_TRAVEL", 1)
    dir_travel = 1  # por defecto bidireccional

    if isinstance(raw_dir, str):
        token = raw_dir.strip().upper()
        dir_travel = {"B": 1, "F": 2, "T": 3}.get(token, 1)
    else:
        # si no es string, puede ser número u otro
        try:
            dir_travel = int(raw_dir)
        except Exception:
            dir_travel = 1

    # 6. Aplicar inversión si es necesario
    if dir_travel == 3:
        line = LineString(list(line.coords)[::-1])

    # 7. Interpolar y calcular nodos
    poi_point    = line.interpolate(perc, normalized=True)
    ref_node     = Point(line.coords[0])
    non_ref_node = Point(line.coords[-1])

    # 8. Producto cruzado para determinar lado
    ax, ay = non_ref_node.x - ref_node.x, non_ref_node.y - ref_node.y
    bx, by = poi_point.x - ref_node.x,    poi_point.y - ref_node.y
    cross = ax * by - ay * bx
    actual_side   = "L" if cross > 0 else "R"
    expected_side = str(poi.get("POI_ST_SD", "")).strip().upper()

    # 9. Debug por consola
    print(f"[INFO] Tile {tile_id} – POI_ID {poi_id}")
    print(f"       LINK_ID: {link_id}")
    print(f"       DIR_TRAVEL raw='{raw_dir}' → {dir_travel}")
    print(f"       Expected: {expected_side} | Actual: {actual_side}")
    print(f"       Cross product: {cross:.6f}")

    # 10. Crear mapa con folium
    m = folium.Map(location=[poi_point.y, poi_point.x], zoom_start=18)
    folium.PolyLine(
        [(y, x) for x, y in line.coords],
        color="blue",
        weight=5,
        tooltip=f"LINK_ID {link_id}"
    ).add_to(m)
    folium.Marker([ref_node.y, ref_node.x],
                  tooltip="Reference Node",
                  icon=folium.Icon(color="green")
    ).add_to(m)
    folium.Marker([non_ref_node.y, non_ref_node.x],
                  tooltip="Non-Reference Node",
                  icon=folium.Icon(color="orange")
    ).add_to(m)
    folium.Marker([poi_point.y, poi_point.x],
                  popup=f"POI_ID {poi_id}<br>Expected: {expected_side}<br>Actual: {actual_side}",
                  icon=folium.Icon(color="red")
    ).add_to(m)

    # 11. Guardar HTML
    output_dir = "../outputs/debug_maps"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/debug_poi_{poi_id}.html"
    m.save(output_file)
    print(f"[INFO] Mapa generado: {output_file}")
    return output_file
