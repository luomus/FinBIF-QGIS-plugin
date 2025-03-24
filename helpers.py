import json
from shapely.geometry import shape, mapping, MultiPolygon, MultiLineString, MultiPoint, Polygon, LineString, Point
from pyproj import Transformer
from qgis.core import QgsJsonUtils, QgsVectorLayer, QgsProject
from PyQt5.QtWidgets import QMessageBox

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

def create_layer(features, geometry_type, qgis_crs):
    """Create a QGIS memory layer from GeoJSON-like features."""
    if features:
        # Determine the field definitions from the first feature
        fields = QgsJsonUtils.stringToFields(json.dumps(features[0]))

        # Create a temporary layer
        type_string = f"{geometry_type}?crs={qgis_crs.authid()}"
        layer_name = f"FinBIF_{geometry_type}_Occurrences"
        layer = QgsVectorLayer(type_string.lower(), layer_name, "memory")

        if layer.isValid():
            # Add fields to the layer
            data_provider = layer.dataProvider()
            data_provider.addAttributes(fields)
            layer.updateFields()

            # Convert GeoJSON features to QgsFeature objects
            geojson_features = {
                "type": "FeatureCollection",
                "features": features
            }
            qgis_features = QgsJsonUtils.stringToFeatureList(json.dumps(geojson_features), fields)

            # Add features to the layer
            data_provider.addFeatures(qgis_features)
            layer.setCrs(qgis_crs)
            layer.updateExtents()

            QgsProject.instance().addMapLayer(layer)
        else:
            QMessageBox.warning(None, 'FinBIF_Plugin', f'Failed to create {geometry_type.lower()} layer from fetched data.')