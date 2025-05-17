# src/validate_existence.py

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

# Ajusta estas rutas si tu estructura es diferente
# Definimos internamente los valores de lado y las flags legales
SIDE_LEFT = 'L'
SIDE_RIGHT = 'R'
LEGAL_FLAGS = [
    'AR_PEDEST',   # acceso peatonal
    'AR_TRUCKS',   # acceso camiones
    'AR_BUS',      # acceso autobuses
]

def _merge_with_naming(pois: gpd.GeoDataFrame, naming: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Une POIs con la tabla de naming por LINK_ID y nombre de calle.
    Devuelve pois con columnas de naming (rangos).
    """
    # Emparejamos POI.ST_NAME con naming.ST_NAME
    merged = pois.merge(
        naming[['LINK_ID', 'ST_NAME', 'L_REFADDR', 'L_NREFADDR', 'R_REFADDR', 'R_NREFADDR']],
        left_on=['LINK_ID', 'ST_NAME'],
        right_on=['LINK_ID', 'ST_NAME'],
        how='left',
        validate='many_to_one'
    )
    return merged

def _check_address_in_range(row: pd.Series) -> bool:
    """
    Dado un registro, determina si ACT_ST_NUM está dentro del rango
    correspondiente al lado (L/R).  
    """
    num = row['ACT_ST_NUM']
    if row['POI_ST_SD'] == SIDE_LEFT:
        low, high = row['L_REFADDR'], row['L_NREFADDR']
    else:
        low, high = row['R_REFADDR'], row['R_NREFADDR']

    # rangos pueden invertirse en geojson; normalizamos:
    lo, hi = min(low, high), max(low, high)
    return lo <= num <= hi

def _detect_legal_exception(row: pd.Series, street_attrs: pd.Series) -> bool:
    """
    Si alguna de las flags legales está activa en street_attrs,
    marcamos excepción legal.
    """
    for flag in LEGAL_FLAGS:
        if street_attrs.get(flag, False):
            return True
    return False

def validate_existence(loader_data: dict) -> gpd.GeoDataFrame:
    """
    Módulo 4: para cada POI determina:
     - 'OK' si la dirección y el nombre coinciden y no aplica excepción.
     - 'NOT_EXISTS' si está fuera de rango o faltó naming.
     - 'LEGAL_EXCEPTION' si está fuera de rango pero hay bandera legal.
    
    Agrega columnas:
     - error_type: str
     - suggestion: str
    """
    pois = loader_data['pois'].copy()
    naming = loader_data['naming']
    streets_nav = loader_data['streets_nav']

    # 1) Une con naming
    df = _merge_with_naming(pois, naming)

    # 2) Para cada POI, comprobamos existencia
    results = []
    for _, row in df.iterrows():
        if pd.isna(row['ST_NAME']):
            # No hubo match de calle
            etype = 'NOT_EXISTS'
            suggestion = f"No matching street name for '{row['ACT_ST_NAM']}' on LINK {row['LINK_ID']}"
        else:
            in_range = _check_address_in_range(row)
            if in_range:
                etype = 'OK'
                suggestion = ''
            else:
                # fuera de rango → ¿excepción legal?
                # buscamos atributos de street_nav:
                street = streets_nav[streets_nav['LINK_ID'] == row['LINK_ID']]
                if not street.empty and _detect_legal_exception(row, street.iloc[0]):
                    etype = 'LEGAL_EXCEPTION'
                    suggestion = "Access exception applies (check legal flags on segment)"
                else:
                    etype = 'NOT_EXISTS'
                    suggestion = (
                        f"Address {row['ACT_ST_NUM']} outside range "
                        f"{row['L_REFADDR']}-{row['L_NREFADDR'] if row['POI_ST_SD']=='L' else row['R_REFADDR']}-{row['R_NREFADDR']}"
                    )
        results.append({
            **row.drop(labels=['geometry']).to_dict(),
            'geometry': row.geometry,
            'error_type': etype,
            'suggestion': suggestion
        })

    # 3) Construimos GeoDataFrame de salida
    out = gpd.GeoDataFrame(results, crs=pois.crs)
    return out

if __name__ == "__main__":
    # Ejemplo de uso (requiere que loader.py esté listo):
    from src.loader import load_tile_data
    data = load_tile_data(tile_id=4815075)
    report = validate_existence(data)
    report.to_file("outputs/poi_existence_4815075.geojson", driver="GeoJSON")
    print("Existence validation complete.")
