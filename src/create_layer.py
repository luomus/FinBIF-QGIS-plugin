from qgis.core import QgsJsonUtils, QgsVectorLayer, QgsProject, QgsFields, QgsField
from PyQt5.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QVariant
import json
from .prosessors import collect_all_field_names


FIELD_TYPE_MAP = {
    "gathering.eventDate.end": QVariant.Date,
    "gathering.eventDate.begin": QVariant.Date,
    "unit.linkings.originalTaxon.taxonomicOrder": QVariant.Int,
    "unit.linkings.taxon.taxonomicOrder": QVariant.Int,
    "gathering.interpretations.coordinateAccuracy": QVariant.Int,
    "unit.linkings.originalTaxon.occurrenceCountFinland": QVariant.Int,
    "unit.linkings.originalTaxon.sensitive": QVariant.Bool,
    "document.loadDate": QVariant.Date,
    "unit.linkings.originalTaxon.finnish": QVariant.Bool,
    "unit.linkings.originalTaxon.latestRedListStatusFinland.year": QVariant.Int,
    "unit.linkings.originalTaxon.cursiveName": QVariant.Bool,
    "unit.interpretations.individualCount": QVariant.Int
}

def create_layer(features, geometry_type, qgis_crs):
    """Create a QGIS memory layer from GeoJSON-like features."""
    if features:
        # Determine the field definitions from the first feature
        field_names = collect_all_field_names(features)

        fields = QgsFields()
        for name in field_names:
            qvariant_type = FIELD_TYPE_MAP.get(name, QVariant.String)
            fields.append(QgsField(name, qvariant_type))

        # Create a temporary layer
        type_string = f"{geometry_type}?crs={qgis_crs.authid()}"
        layer_name = f"FinBIF_{geometry_type}_Occurrences"
        layer = QgsVectorLayer(type_string.lower(), layer_name, "memory")

        if layer.isValid():
            # Add fields to the layer
            data_provider = layer.dataProvider()
            data_provider.addAttributes(fields)
            layer.updateFields()

            ordered_features = []
            for f in features:
                ordered_props = {key: f["properties"].get(key, "") for key in field_names}
                ordered_feature = {
                    "type": "Feature",
                    "geometry": f["geometry"],
                    "properties": ordered_props
                }
                ordered_features.append(ordered_feature)

            # Convert GeoJSON features to QgsFeature objects
            geojson_features = {
                "type": "FeatureCollection",
                "features": ordered_features
            }
            qgis_features = QgsJsonUtils.stringToFeatureList(json.dumps(geojson_features), fields)

            # Add features to the layer
            data_provider.addFeatures(qgis_features)
            layer.setCrs(qgis_crs)
            layer.updateExtents()

            QgsProject.instance().addMapLayer(layer)
        else:
            QMessageBox.warning(None, 'FinBIF_Plugin', f'Failed to create {geometry_type.lower()} layer from fetched data.')