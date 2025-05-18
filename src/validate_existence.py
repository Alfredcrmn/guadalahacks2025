# src/validate_existence.py

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString

SIDE_LEFT = "L"
SIDE_RIGHT = "R"

# Maximum allowed distance in meters from the POI to a MULTIDIGIT link
MAX_DIST_METERS = 5

# Valid FAC_TYPEs that qualify as legitimate exceptions when very close to MULTIDIGIT links
VALID_FAC_TYPES = {4013, 4100, 4170}

def validate_existence(loader_data: dict) -> gpd.GeoDataFrame:
    """
    Validates the existence and legitimacy of POIs located inside Multiply Digitised (MULTIDIGIT) links.

    Implements the logic for Case 4/4 from the Guadalajara Hackathon 2025 challenge:
    "Legitimate Exception: correct location and confirmed existence". It detects POIs
    that are valid despite triggering the POI295 validation rule.

    Validation steps:
    - Check POI geometry and link_id.
    - Verify if the associated link is marked MULTIDIGIT.
    - Measure real distance between POI and the MULTIDIGIT link geometry.
    - If distance ≤ MAX_DIST_METERS AND POI.FAC_TYPE is in VALID_FAC_TYPES → LEGITIMATE_EXCEPTION.

    Returns a GeoDataFrame with added columns: error_type, suggestion, distance_meters, fac_type.
    """

    pois = loader_data["pois"].copy()
    streets = loader_data["streets_nav"]

    if "MULTIDIGIT" not in streets.columns:
        raise KeyError("MULTIDIGIT column missing in streets_nav")

    multig_links = streets[streets["MULTIDIGIT"] == "Y"]
    multig_links = multig_links.set_index("link_id")

    results = []

    for _, row in pois.iterrows():
        link_id = row.get("LINK_ID")
        poi_geom = row.geometry
        perc = row.get("PERCFRREF", 50) / 100.0
        side = row.get("POI_ST_SD")
        fac_type = int(row.get("FAC_TYPE", -1)) if not pd.isna(row.get("FAC_TYPE")) else -1

        # Default values
        distance = None
        error_type = "UNDEFINED"
        suggestion = ""

        if pd.isna(link_id) or poi_geom is None or poi_geom.is_empty:
            error_type = "INVALID_GEOMETRY"
            suggestion = "Missing geometry or LINK_ID"
        elif link_id not in multig_links.index:
            error_type = "NOT_MULTIDIGIT"
            suggestion = "Associated link is not MULTIDIGIT"
        else:
            link_geom = multig_links.loc[link_id].geometry
            try:
                # Measure distance from POI to line
                distance = poi_geom.distance(link_geom)

                if distance <= MAX_DIST_METERS:
                    if fac_type in VALID_FAC_TYPES:
                        error_type = "LEGITIMATE_EXCEPTION"
                        suggestion = f"Valid FAC_TYPE {fac_type} near MULTIDIGIT (dist {distance:.2f}m)"
                    else:
                        error_type = "TOO_CLOSE_INVALID_TYPE"
                        suggestion = f"FAC_TYPE {fac_type} is not valid for legit exception (dist {distance:.2f}m)"
                else:
                    error_type = "TOO_FAR_FROM_LINK"
                    suggestion = f"POI is {distance:.2f}m from MULTIDIGIT link"
            except Exception as e:
                error_type = "DISTANCE_ERROR"
                suggestion = f"Distance calc failed: {str(e)}"

        # Output full row + analysis
        results.append({
            **row.to_dict(),
            "fac_type": fac_type,
            "distance_meters": distance,
            "error_type": error_type,
            "suggestion": suggestion
        })

    return gpd.GeoDataFrame(results, geometry="geometry", crs=pois.crs)
