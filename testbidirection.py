import geopandas as gpd

# Cargar el archivo GeoJSON
gdf = gpd.read_file("data/STREETS_NAV/SREETS_NAV_4815084.geojson")

# Filtrar donde DIR_TRAVEL es "B"
df_b = gdf[gdf["DIR_TRAVEL"] == "B"]

# Verificar que todos tengan MULTIDIGIT = "N"
violations = df_b[df_b["MULTIDIGIT"] != "N"]

# Mostrar resultados
if violations.empty:
    print("✅ Todos los segmentos con DIR_TRAVEL = 'B' tienen MULTIDIGIT = 'N'")
else:
    print(f"❌ {len(violations)} segmentos con DIR_TRAVEL = 'B' NO tienen MULTIDIGIT = 'N'")
    print(violations[["link_id", "MULTIDIGIT"]])
