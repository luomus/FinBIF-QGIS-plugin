import json, os
from pandas import read_csv

def get_lookup_table():
    return read_csv(os.path.join(os.path.dirname(__file__), 'resources/columns_lookup.csv'), sep='\t', header=0)

def load_areas():
    plugin_dir = os.path.dirname(__file__)
    areas_file_path = os.path.join(plugin_dir, 'resources/areas.json')

    with open(areas_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    countries = {}
    countries_by_id = {}
    municipalities = {}
    biogeographical_areas = {}
    provinces = {}
    ely_centers = {}
    bird_association_areas = {}

    for area in data['results']:
        area_id = area['id']
        area_name = area.get('name', '')

        if area['areaType'] == 'ML.country':
            countries[area_name] = area_id
            countries_by_id[area_id] = area.get('countryCodeISOalpha2', 'Unknown')
        elif area['areaType'] == 'ML.municipality':
            municipalities[area_name] = area_id
        elif area['areaType'] == 'ML.biogeographicalProvince':
            biogeographical_areas[area_name] = area_id
        elif area['areaType'] == 'ML.province':
            provinces[area_name] = area_id
        elif area['areaType'] == 'ML.elyCentre':
            ely_centers[area_name] = area_id
        elif area['areaType'] == 'ML.birdAssociationArea':
            bird_association_areas[area_name] = area_id

    return {
        'countries': countries,
        'countries_by_id': countries_by_id,
        'municipalities': municipalities,
        'biogeographical_areas': biogeographical_areas,
        'provinces': provinces,
        'ely_centers': ely_centers,
        'bird_association_areas': bird_association_areas
    }

def load_ranges():
    plugin_dir = os.path.dirname(__file__)
    ranges_file_path = os.path.join(plugin_dir, 'resources/ranges.json')

    with open(ranges_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    administrative_statuses = {}
    iucn_statuses = {}
    atlas_codes = {}
    atlas_classes = {}

    for category, list_of_pairs in data.items():
        if category == 'MX.adminStatusEnum':
            for status in list_of_pairs:
                administrative_statuses[status['value']] = status['id']
        elif category == 'MX.iucnStatuses':
            for status in list_of_pairs:
                iucn_statuses[status['value']] = status['id']
        elif category == 'MY.atlasCodeEnum':
            for code in list_of_pairs:
                atlas_codes[code['value']] = code['id']
        elif category == 'MY.atlasClassEnum':
            for cls in list_of_pairs:
                atlas_classes[cls['value']] = cls['id']

    return {
        'MX.adminStatusEnum': administrative_statuses,
        'MX.iucnStatuses': iucn_statuses,
        'MY.atlasCodeEnum': atlas_codes,
        'MY.atlasClassEnum': atlas_classes
    }