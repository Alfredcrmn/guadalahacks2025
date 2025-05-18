# src/validate_existence.py

import geopandas as gpd
import pandas as pd

# Constantes de lado y flags legales
SIDE_LEFT = 'L'
SIDE_RIGHT = 'R'
LEGAL_FLAGS = ['AR_PEDEST', 'AR_TRUCKS', 'AR_BUS']

def validate_existence(loader_data: dict) -> gpd.GeoDataFrame:
    pois    = loader_data['pois'].copy()
    naming  = loader_data['naming']
    streets = loader_data['streets_nav']

    # 1) Detectar nombre de columna para LINK_ID ↔ link_id
    poi_link_col  = 'LINK_ID'  if 'LINK_ID'  in pois.columns   else None
    name_link_col = 'link_id'  if 'link_id'  in naming.columns else None
    if not poi_link_col or not name_link_col:
        raise KeyError("Expected LINK_ID in POIs and link_id in naming")

    # 2) Merge POIs ↔ Naming, trayendo rangos y esquemas
    df = pois.merge(
        naming[[name_link_col, 'ST_NAME',
                'L_REFADDR','L_NREFADDR','L_ADDRFORM','L_ADDRSCH',
                'R_REFADDR','R_NREFADDR','R_ADDRFORM','R_ADDRSCH']],
        left_on=[poi_link_col, 'ST_NAME'],
        right_on=[name_link_col, 'ST_NAME'],
        how='left', validate='many_to_one'
    )

    records = []
    for _, row in df.iterrows():
        geom = row.geometry

        # A) Si no tiene geometría válida → NOT_EXISTS
        if geom is None or (hasattr(geom, 'is_empty') and geom.is_empty):
            etype = 'NOT_EXISTS'
            suggestion = 'No coordinates'
        else:
            act_num = row.get('ACT_ST_NUM')
            poi_name = row.get('ST_NAME')

            # B) Si no tiene dirección (sin número o sin calle) → OK
            if pd.isna(act_num) or pd.isna(poi_name):
                etype = 'OK'
                suggestion = ''
            else:
                # C) Determinar rangos y esquema según lado
                side = row.get('POI_ST_SD')
                if side == SIDE_LEFT:
                    low_raw   = row.get('L_REFADDR')
                    high_raw  = row.get('L_NREFADDR')
                    scheme    = row.get('L_ADDRSCH')
                else:
                    low_raw   = row.get('R_REFADDR')
                    high_raw  = row.get('R_NREFADDR')
                    scheme    = row.get('R_ADDRSCH')

                # D) Validar rango numérico + esquema par/impar
                valid = False
                try:
                    low   = float(low_raw)
                    high  = float(high_raw)
                    num   = float(act_num)
                    lo, hi = min(low, high), max(low, high)
                    # rango básico
                    if lo <= num <= hi:
                        # si hay esquema, verificar par/impar
                        if scheme == 'E' and (num % 2 != 0):
                            valid = False
                        elif scheme == 'O' and (num % 2 != 1):
                            valid = False
                        else:
                            valid = True
                except Exception:
                    valid = False

                if valid:
                    etype = 'OK'
                    suggestion = ''
                else:
                    # E) Fuera de rango → ¿excepción legal?
                    seg = streets[streets[name_link_col] == row[poi_link_col]]
                    if not seg.empty and any(seg.iloc[0].get(flag, False) for flag in LEGAL_FLAGS):
                        etype = 'LEGAL_EXCEPTION'
                        suggestion = 'Legal access flag present'
                    else:
                        etype = 'OUT_OF_RANGE'
                        # muestra los límites originales en la sugerencia
                        suggestion = f"{act_num} outside {low_raw}–{high_raw}"

        # Construir registro de salida
        rec = row.drop(labels=['geometry']).to_dict()
        rec.update({
            'geometry': geom,
            'error_type': etype,
            'suggestion': suggestion
        })
        records.append(rec)

    return gpd.GeoDataFrame(records, crs=pois.crs)
