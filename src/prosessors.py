from shapely.geometry import shape, mapping, MultiPolygon, MultiLineString, MultiPoint, Polygon, LineString, Point
import re


def process_geometry_collection(geometry, crs):
    """Convert GeometryCollection to MultiX if only one type exists, or MultiPolygon otherwise (buffering lines/points)."""
    
    if crs == 'WGS84':
        buffer_distance=4.49e-6 # 0.5 meters in WGS84
    else:
        buffer_distance=0.5

    geometries = [shape(g) for g in geometry['geometries']]  # Convert GeoJSON to Shapely geometries

    if len(geometries) == 1:
        return mapping(geometries[0])  # Return as-is if only one geometry

    # Check if all geometries are of the same type and return MultiX if so
    if all(isinstance(g, LineString) for g in geometries):
        return mapping(MultiLineString(geometries))
    if all(isinstance(g, Point) for g in geometries):
        return mapping(MultiPoint(geometries))
    if all(isinstance(g, Polygon) for g in geometries):
        return mapping(MultiPolygon(geometries))
    if all(isinstance(g, MultiLineString) for g in geometries):
        return mapping(MultiLineString([geom for g in geometries for geom in g.geoms]))
    if all(isinstance(g, MultiPoint) for g in geometries):  
        return mapping(MultiPoint([geom for g in geometries for geom in g.geoms]))
    if all(isinstance(g, MultiPolygon) for g in geometries):
        return mapping(MultiPolygon([geom for g in geometries for geom in g.geoms]))

    # Mixed types → Convert to MultiPolygon (buffer points & lines)
    buffered_geoms = [
        g.buffer(buffer_distance) if isinstance(g, (Point, LineString, MultiPoint, MultiLineString))
        else g
        for g in geometries if isinstance(g, (Polygon, MultiPolygon, Point, LineString, MultiPoint, MultiLineString))
    ]

    # Dissolve buffered geometries and return as MultiPolygon
    dissolved = buffered_geoms[0]
    for geom in buffered_geoms[1:]:
        dissolved = dissolved.union(geom)   
    return mapping(dissolved)

def map_values(combo_box, mapping_dict):
    """This function maps values if they are not the same in QGIS dialog window and in api.laji.fi"""
    selected_values = combo_box.currentData()
    return ','.join(filter(None, [mapping_dict.get(value, '') for value in selected_values]))

def collect_all_field_names(features):
    keys = set()
    for f in features:
        keys.update(f.get("properties", {}).keys())
    return keys  # consistent order

def combine_similar_columns(features):
    """
    Finds similar columns (e.g. keyword[0], keyword[1], keyword[2]) and combines them
    """
    pattern = re.compile(r'^(.*)\[(\d+)\]$')
    for feature in features:
        props = feature.get("properties", {})
        # Find all base names with [n] pattern
        columns_dict = {}
        for key in list(props.keys()):
            match = pattern.match(key)
            if match:
                base_name = match.group(1)
                columns_dict.setdefault(base_name, []).append(key)
        # Combine values for each base name
        for base_name, keys in columns_dict.items():
            combined = ', '.join(str(props[k]) for k in keys if props[k] not in [None, '', 'nan'])
            props[base_name] = combined
            for k in keys:
                props.pop(k, None)
        feature["properties"] = props
    return features