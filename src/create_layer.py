from qgis.core import QgsVectorLayer, QgsProject, QgsFields, QgsField
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsFeature, QgsGeometry, QgsCoordinateReferenceSystem
import pandas as pd
import numpy as np
from qgis.core import Qgis, QgsMessageLog

FIELD_TYPE_MAP = {
    "eventDate": QVariant.Date,
    "coordinateAccuracy": QVariant.Int,
    "individualCount": QVariant.Int,
    "isSensitiveTaxon": QVariant.Bool,
    "availableDate": QVariant.Bool,
    "redListStatusFinlandYear": QVariant.Int,
    "isBreedingSite": QVariant.Bool,
    "isMigrating": QVariant.Bool,
    "isStateLand": QVariant.Bool,
    "maleIndividualCount": QVariant.Int,
    "femaleIndividualCount": QVariant.Int,
}

def create_layer(gdf, layer_name, qgis_crs):
    """Create QGIS layer directly from GeoDataFrame"""
    if gdf.empty:
        return 0
    
    # Determine geometry type from the GeoDataFrame
    geom_types = gdf.geometry.geom_type.unique()
    if len(geom_types) > 1:
        # Handle mixed geometries by creating separate layers
        for geom_type in geom_types:
            subset_gdf = gdf[gdf.geometry.geom_type == geom_type]
            create_layer(subset_gdf, f"{layer_name}_{geom_type}", qgis_crs)
        return
    
    geom_type = geom_types[0]
    type_string = f"{geom_type}?crs={qgis_crs.authid()}"
    
    # Create memory layer
    layer = QgsVectorLayer(type_string.lower(), layer_name, "memory")
    if not layer.isValid():
        QMessageBox.warning(None, 'FinBIF_Plugin', f'Failed to create {layer_name} layer')
        return
    
    # Get column names excluding geometry
    column_names = [col for col in gdf.columns if col != 'geometry']

    # Add fields based on GeoDataFrame columns
    data_provider = layer.dataProvider()
    fields = QgsFields()

    for col_name in column_names:
        dtype = gdf.dtypes[col_name]
        # Map pandas dtypes to QGIS QVariant types
        qvariant_type = FIELD_TYPE_MAP.get(col_name, QVariant.String)
        if qvariant_type == QVariant.String:  # Use dtype mapping as fallback
            if 'int' in str(dtype).lower():
                qvariant_type = QVariant.Int
            elif 'float' in str(dtype).lower():
                qvariant_type = QVariant.Double
            elif 'datetime' in str(dtype).lower():
                qvariant_type = QVariant.DateTime
            elif 'bool' in str(dtype).lower():
                qvariant_type = QVariant.Bool
        
        fields.append(QgsField(col_name, qvariant_type))
    
    data_provider.addAttributes(fields)
    layer.updateFields()
    
    # Add features from GeoDataFrame
    features = []
    for idx, row in gdf.iterrows():
        feature = QgsFeature()
        
        # Convert Shapely geometry to QGIS geometry using WKT
        try:
            feature.setGeometry(QgsGeometry.fromWkt(row.geometry.wkt))
        except:
            # Skip invalid geometries
            QgsMessageLog.logMessage(f"Found invalid geometry {row.geometry.wkt} that prevented layer creation -> skipping.", level=Qgis.MessageLevel.Warning)
            continue
        
        # Set attributes in the correct order matching field order
        attributes = []
        for col in column_names:
            value = row[col]

            # Convert to appropriate Python type for QGIS
            if pd.isna(value):
                attributes.append(None)
            elif isinstance(value, pd.Timestamp):
                attributes.append(value.to_pydatetime())
            elif isinstance(value, pd.Period):
                attributes.append(str(value))
            elif isinstance(value, (pd.Series, list)):
                # Handle cases where the value is unexpectedly a Series or list
                attributes.append(str(value))
            else:
                attributes.append(value)
        
        feature.setAttributes(attributes)
        features.append(feature)
    
    if features:
        data_provider.addFeatures(features)
        layer.setCrs(qgis_crs)
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)
    else:
        QMessageBox.warning(None, 'FinBIF_Plugin', f'No valid features to add to {layer_name} layer')