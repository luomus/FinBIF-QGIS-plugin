from shapely.geometry import MultiPolygon, MultiLineString, MultiPoint, Polygon, LineString, Point, GeometryCollection
import re
from shapely.ops import unary_union
import pandas as pd
import geopandas as gpd
import json

def process_countries(gdf, areas_dict):
    """ Map country names to their corresponding IDs.
    """
    if 'gathering.interpretations.country' in gdf.columns:
        gdf['gathering.interpretations.country'] = gdf['gathering.interpretations.country'].str.replace(r'http://[^/]+\.fi/', "", regex=True).map(areas_dict).fillna(gdf['gathering.interpretations.country'])

    return gdf

def process_boolean_fields(gdf):
    """ Map single value fields to their corresponding enum values.
    """
    columns_to_process = ['unit.linkings.taxon.sensitive']
    for col in columns_to_process:
        if col in gdf.columns:
            gdf[col] = gdf[col].map({'true': True, 'false': False}).fillna(gdf[col])

    return gdf

def map_single_value_fields(gdf, enums):
    columns_to_map = {'unit.atlasClass',
                      'unit.atlasCode',
                      'document.licenseId',
                      'unit.linkings.taxon.latestRedListStatusFinland.status',
                      'unit.linkings.taxon.taxonRank',
                      'document.linkings.collectionQuality',
                      'unit.linkings.taxon.threatenedStatus',
                      'unit.sex',
                      'unit.lifeStage',
                      'unit.linkings.taxon.administrativeStatuses',
                      'document.secureReasons',
                      'unit.linkings.taxon.primaryHabitat.habitat',
                      'document.sourceId',
                      'unit.recordBasis',
                      'gathering.interpretations.sourceOfCoordinates',
                      'unit.interpretations.recordQuality'
                      }
    
    # Find all columns that match the base patterns (including those with [n] suffixes)
    columns_to_process = []
    for base_col in columns_to_map:
        # Find exact matches
        if base_col in gdf.columns:
            columns_to_process.append(base_col)
        
        # Find columns with [n] suffixes
        pattern = re.compile(rf'^{re.escape(base_col)}\[\d+\]$')
        matching_cols = [col for col in gdf.columns if pattern.match(col)]
        columns_to_process.extend(matching_cols)
    
    # Process each found column
    for col in columns_to_process:
        if col in gdf.columns:  # Fixed typo: was gdf.columns.st
            gdf[col] = gdf[col].str.replace(r'http://[^/]+\.fi/', "", regex=True).map(enums).fillna(gdf[col])
    
    return gdf

def process_dates(gdf): # Not in use currently
    def combine_datetime_components(begin_date, begin_hour=None, begin_minutes=None, 
                                   end_date=None, end_hour=None, end_minutes=None):
        """
        Combine date, hour, and minute components into ISO 8601 datetime format.
        
        Returns:
            String in ISO 8601 format (date or date/date interval)
            TODO: Clean this or check if available from the API
        """
        if pd.isna(begin_date) or not str(begin_date).strip():
            return None
        
        # Build start datetime string
        start_datetime = str(begin_date).strip()
        if pd.notna(begin_hour) and str(begin_hour).strip():
            hour_str = f"{int(float(begin_hour)):02d}"
            minute_str = f"{int(float(begin_minutes or 0)):02d}"
            start_datetime += f"T{hour_str}:{minute_str}"
        
        # If no end date, return just the start
        if pd.isna(end_date) or not str(end_date).strip():
            return start_datetime
        
        # Build end datetime string
        end_datetime = str(end_date).strip()
        if pd.notna(end_hour) and str(end_hour).strip():
            hour_str = f"{int(float(end_hour)):02d}"
            minute_str = f"{int(float(end_minutes or 0)):02d}"
            end_datetime += f"T{hour_str}:{minute_str}"
        
        # Return as interval
        return f"{start_datetime}/{end_datetime}"

    # Get all relevant columns
    date_cols = ['gathering.eventDate.begin', 'gathering.eventDate.end', 
                 'gathering.hourBegin', 'gathering.minutesBegin',
                 'gathering.hourEnd', 'gathering.minutesEnd']
    
    existing_cols = [col for col in date_cols if col in gdf.columns]
    
    if existing_cols:
        # Create the combined eventDate column
        gdf['eventDate'] = gdf.apply(lambda row: combine_datetime_components(
            row.get('gathering.eventDate.begin'),
            row.get('gathering.hourBegin'),
            row.get('gathering.minutesBegin'),
            row.get('gathering.eventDate.end'),
            row.get('gathering.hourEnd'),
            row.get('gathering.minutesEnd')
        ), axis=1)
        
        # Drop the individual date/time columns
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['eventDate'] = None

    return gdf

def process_event_remarks(gdf):
    cols_to_join = ['gathering.notes', 'document.notes']

    # Filter to only include columns that exist in the dataframe
    existing_cols = [col for col in cols_to_join if col in gdf.columns]

    if existing_cols:
        gdf['eventRemarks'] = (gdf[existing_cols].fillna('').agg(lambda x: ', '.join([v for v in x if v.strip() != '']), axis=1))
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['eventRemarks'] = None

    return gdf

def process_other_catalog_numbers(gdf):
    cols_to_join = ['unit.keywords', 'document.keywords']

    # Filter to only include columns that exist in the dataframe
    existing_cols = [col for col in cols_to_join if col in gdf.columns]

    if existing_cols:
        gdf['otherCatalogNumbers'] = (gdf[existing_cols].fillna('').agg(lambda x: ', '.join([v for v in x if v.strip() != '']), axis=1))
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['otherCatalogNumbers'] = None

    return gdf

def process_taxon_preferred_habitat(gdf):
    cols_to_join = ['unit.linkings.taxon.primaryHabitat.habitat',
                    'unit.linkings.taxon.primaryHabitat.habitatSpecificTypes']

    # Filter to only include columns that exist in the dataframe
    existing_cols = [col for col in cols_to_join if col in gdf.columns]

    if existing_cols:
        gdf['taxonPreferredHabitat'] = (gdf[existing_cols].fillna('').agg(lambda x: ', '.join([v for v in x if v.strip() != '']), axis=1))
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['taxonPreferredHabitat'] = None

    return gdf

def process_quality_issues(gdf):
    cols_to_join = ['document.quality.issue.issue',
                    'document.quality.issue.message',
                    'document.quality.issue.source',
                    'gathering.quality.issue.issue',
                    'gathering.quality.issue.message',
                    'gathering.quality.issue.source',
                    'gathering.quality.locationIssue.issue',
                    'gathering.quality.locationIssue.message',
                    'gathering.quality.locationIssue.source',
                    'gathering.quality.timeIssue.issue',
                    'gathering.quality.timeIssue.message',
                    'gathering.quality.timeIssue.source',
                    'unit.quality.issue.issue',
                    'unit.quality.issue.message',
                    'unit.quality.issue.source']

    # Filter to only include columns that exist in the dataframe
    existing_cols = [col for col in cols_to_join if col in gdf.columns]

    if existing_cols:
        gdf['qualityIssues'] = (gdf[existing_cols].fillna('').agg(lambda x: ', '.join([v for v in x if v.strip() != '']), axis=1))
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['qualityIssues'] = None

    return gdf

def process_dynamic_properties(gdf):
    cols_to_join = ['gathering.accurateArea', 
                    'gathering.gatheringSection', 
                    'unit.alive', 
                    'unit.individualId', 
                    'unit.plantStatusCode', 
                    'unit.wild']

    # Filter to only include columns that exist in the dataframe
    existing_cols = [col for col in cols_to_join if col in gdf.columns]

    if existing_cols:
        def create_dynamic_properties_json(row):
            properties_dict = {}
            for col in existing_cols:
                value = row[col]
                if pd.notna(value) and str(value).strip():
                    # Use the column name without the prefix as the key
                    key = col.split('.')[-1]  # Gets the last part after the dot
                    properties_dict[key] = value
            
            # Return JSON string if there are properties, otherwise None
            return json.dumps(properties_dict) if properties_dict else None
        
        gdf['dynamicProperties'] = gdf.apply(create_dynamic_properties_json, axis=1)
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['dynamicProperties'] = None
    
    return gdf

def process_verbatim_location_values(gdf):
    cols_to_join = ['gathering.biogeographicalProvince', 
                    'gathering.country', 
                    'gathering.higherGeography', 
                    'gathering.interpretations.countryDisplayname', 
                    'gathering.municipality', 
                    'gathering.province',
                    'gathering.locality',]

    # Filter to only include columns that exist in the dataframe
    existing_cols = [col for col in cols_to_join if col in gdf.columns]

    if existing_cols:
        def combine_unique_values(row):
            # Collect all non-empty values
            values = [str(v).strip() for v in row[existing_cols] if pd.notna(v) and str(v).strip() != '']
            # Remove duplicates while preserving order
            unique_values = list(dict.fromkeys(values))
            return ', '.join(unique_values) if unique_values else None
        
        gdf['verbatimLocality'] = gdf.apply(combine_unique_values, axis=1)
        gdf = gdf.drop(columns=existing_cols)
    else:
        gdf['verbatimLocality'] = None
    
    return gdf

def map_collection_id(gdf, collection_names):
    """Map collection IDs to collection names
    """
    gdf['datasetName'] = gdf['document.collectionId'].str.split('/').str[-1].map(collection_names)
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
    pattern = re.compile(r'^(.+?)(\[\d+\])(.*)$')
    columns_dict = {}

    for col in gdf.columns:
        match = pattern.match(col)
        if match:
            base_name = match.group(1) + match.group(3)
            columns_dict.setdefault(base_name, []).append(col)

    gdf = gdf.copy()

    for base_name, cols in columns_dict.items():
        if len(cols) > 1:
            # Vectorized row-wise combine
            gdf[base_name] = gdf[cols].apply(
                lambda row: ', '.join([str(v).strip() for v in row if pd.notna(v) and str(v).strip()]) or None,
                axis=1
            )
            gdf.drop(columns=cols, inplace=True)
        else:
            gdf.rename(columns={cols[0]: base_name}, inplace=True)

    return gdf

def translate_column_names(gdf, lookup_df, style='dwc'):
    column_mapping = dict(zip(lookup_df['api'], lookup_df[style]))
    gdf = gdf.rename(columns=column_mapping)
    return gdf