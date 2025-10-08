from shapely.geometry import MultiPolygon, MultiLineString, MultiPoint, Polygon, LineString, Point, GeometryCollection
import re
from shapely.ops import unary_union
import pandas as pd
import geopandas as gpd

def map_collection_id(gdf, collection_names):
    """Map collection IDs to collection names
    """
    gdf['document.collectionName'] = gdf['document.collectionId'].str.split('/').str[-1].map(collection_names)
    return gdf

def merge_taxonomy_data(occurrence_gdf, taxonomy_df):
    """ Merge taxonomy information to the occurrence data."""

    if 'unit.linkings.taxon.informalTaxonGroups[0]' not in occurrence_gdf.columns:
        occurrence_gdf['unit.linkings.taxon.informalTaxonGroups[0]'] = None
        
    occurrence_gdf['unit.linkings.taxon.informalTaxonGroups[0]'] = occurrence_gdf['unit.linkings.taxon.informalTaxonGroups[0]'].str.extract(r'(MVL\.\d+)')
    merged_gdf = occurrence_gdf.merge(taxonomy_df, left_on='unit.linkings.taxon.informalTaxonGroups[0]', right_on='id', how='left')

    # Drop all unit.linkings.taxon.informalTaxonGroup[n] columns
    columns_to_drop = [col for col in merged_gdf.columns if col.startswith('unit.linkings.taxon.informalTaxonGroups[') and col.endswith(']')]
    columns_to_drop.append('id')
    if columns_to_drop:
        merged_gdf.drop(columns=columns_to_drop, inplace=True)

    return merged_gdf

def validate_geometry(gdf):
    """ Validate geometries in the GeoDataFrame."""

    # Use make_valid to ensure all geometries are valid
    invalid = ~gdf['geometry'].is_valid
    gdf.loc[invalid, 'geometry'] = gdf.loc[invalid, 'geometry'].make_valid()
    return gdf

def convert_geometry_collection_to_multipolygon(gdf, buffer_distance=0.5):
    """Convert GeometryCollection to MultiPolygon in the entire GeoDataFrame, buffering points and lines if necessary.
       The resulting MultiPolygon is dissolved into a single geometry."""

    def process_geometry(geometry):
        if isinstance(geometry, GeometryCollection):
            geom_types = {type(geom) for geom in geometry.geoms}
            geometries = list(geometry.geoms)

            # If the GeometryCollection has only one geometry, return it as-is
            if len(geometries) == 1:
                return geometries[0]

            # If all geometries are of the same type, convert to MultiX
            if geom_types == {LineString}:
                return MultiLineString(list(geometry.geoms))
            elif geom_types == {Point}:
                return MultiPoint(list(geometry.geoms))
            elif geom_types == {Polygon}:
                return MultiPolygon(list(geometry.geoms))
            elif geom_types == {MultiLineString}:
                return MultiLineString([g for geom in geometry.geoms for g in geom.geoms])
            elif geom_types == {MultiPoint}:
                return MultiPoint([g for geom in geometry.geoms for g in geom.geoms])
            elif geom_types == {MultiPolygon}:
                return MultiPolygon([g for geom in geometry.geoms for g in geom.geoms])

            # In other case, buffer points and lines and return the dissolved result as MultiPolygon
            polygons = [geom.buffer(buffer_distance) if isinstance(geom, (Point, LineString, MultiPoint, MultiLineString)) 
                        else geom 
                        for geom in geometry.geoms if isinstance(geom, (Polygon, MultiPolygon, Point, LineString, MultiPoint, MultiLineString))]

            if polygons:
                dissolved_geometry = unary_union(polygons)
                
                if isinstance(dissolved_geometry, Polygon):
                    return MultiPolygon([dissolved_geometry])

                return dissolved_geometry
            else:
                return None
        return geometry

    gdf['geometry'] = gdf['geometry'].apply(process_geometry)
    
    return gdf

def map_values(combo_box, mapping_dict):
    """This function maps values if they are not the same in QGIS dialog window and in api.laji.fi"""
    selected_values = combo_box.currentData()
    return ','.join(filter(None, [mapping_dict.get(value, '') for value in selected_values]))

def combine_similar_columns(gdf):
    """
    Finds similar columns (e.g. keyword[0], keyword[1], keyword[2]) and combines them
    """
    # Use regex to find columns with a pattern containing [n]
    pattern = re.compile(r'^(.+?)(\[\d+\])(.*)$')

    # Dictionary to store the groups of columns
    columns_dict = {}

    for col in gdf.columns:
        match = pattern.match(col)
        if match:
            base_name = match.group(1) + match.group(3)  # Remove the [n] part
            if base_name not in columns_dict:
                columns_dict[base_name] = []
            columns_dict[base_name].append(col)
    
    gdf = gdf.copy()

    # Combine columns in each group
    for base_name, cols in columns_dict.items():
        if len(cols) > 1:  # Only combine if there are multiple columns
            # Properly combine the values from multiple columns
            combined_values = []
            for idx in range(len(gdf)):
                row_values = []
                for col in cols:
                    value = gdf.iloc[idx][col]
                    if pd.notna(value) and str(value).strip():
                        row_values.append(str(value))
                # Join non-empty values with comma and space
                combined_values.append(', '.join(row_values) if row_values else None)
            
            gdf[base_name] = combined_values
            gdf.drop(columns=cols, inplace=True)

    return gdf