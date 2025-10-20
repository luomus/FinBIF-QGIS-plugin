from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, QCheckBox, QTabWidget, QWidget, QLabel, QProgressBar, QSlider, QMessageBox
from PyQt5.QtCore import QSettings, Qt
import pandas as pd
from ..api import *
from qgis.core import QgsCoordinateReferenceSystem
from .custom_widgets import *
from ..prosessors import *
from ..validators import *
from ..create_layer import create_layer
from .api_key_dialog import open_api_key_dialog

# Constants
MAX_OBSERVATIONS_LIMIT = 500000
EPSG_MAPPINGS = {
    'EUREF': 'EPSG:3067',
    'YKJ': 'EPSG:2393',
    'WGS84': 'EPSG:4326'
}
CRS_MAPPINGS = {
    'ETRS-TM35FIN (for Finnish)': 'EUREF',
    'YKJ (for Finnish)': 'YKJ',
    'WGS84 (for global)': 'WGS84'
}

class FinBIFDialog(QDialog):
    def __init__(self, iface, areas, ranges, collection_names, informal_taxon_names):
        super().__init__()
        self.iface = iface
        self.areas = areas
        self.ranges = ranges
        self.collection_names = collection_names
        self.informal_taxon_names = informal_taxon_names
        self.settings = QSettings()
        self.is_running = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('FinBIF API Query Parameters')

        layout = QVBoxLayout()
        tab_widget = QTabWidget()

        intro_label = QLabel("This plugin allows you to fetch open data from the FinBIF API and load it into QGIS.")
        layout.addWidget(intro_label)

        # General Parameters Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        general_form_layout = QFormLayout()

        # Access Token Input and Get API Key Button on the Same Row
        access_token_layout = QHBoxLayout()
        
        self.access_token_input = QLineEdit()
        self.access_token_input.setText(self.settings.value("FinBIF_API_Plugin/access_token", ""))
        self.access_token_input.setToolTip('Your API access token. See more https://api.laji.fi/explorer/#/APIUser')
        
        self.get_api_key_button = QPushButton("Get API KEY")
        self.get_api_key_button.clicked.connect(lambda: open_api_key_dialog(self))
        
        access_token_layout.addWidget(self.access_token_input)
        access_token_layout.addWidget(self.get_api_key_button)
        
        general_form_layout.addRow(QLabel('Access token: (mandatory)'), access_token_layout)
        
        general_layout.addLayout(general_form_layout)
        general_tab.setLayout(general_layout)

        self.crs_combo = QComboBox()
        self.crs_combo.addItems(['ETRS-TM35FIN (for Finnish)', 'YKJ (for Finnish)', 'WGS84 (for global)',])
        self.crs_combo.setToolTip('Coordinate Reference System. Note: ETRS-TM35FIN and YKJ only for Finnish data!')
        general_form_layout.addRow(QLabel('CRS:'), self.crs_combo)

        self.geom_type_combo = QComboBox()
        self.geom_type_combo.addItems(['CENTER_POINT', 'ENVELOPE', 'ORIGINAL_FEATURE'])
        self.geom_type_combo.setToolTip('Type of geometry to use')
        general_form_layout.addRow(QLabel('Geometry Type:'), self.geom_type_combo)

        self.collection_id_input = QLineEdit()
        self.collection_id_input.setToolTip("""ID of the collection. E.g. HR.48. Multiple values are seperated by ','.""")
        general_form_layout.addRow(QLabel('Collection ID:'), self.collection_id_input)

        self.collection_id_not_input = QLineEdit()
        self.collection_id_not_input.setToolTip("""ID of the collection to exclude. E.g. HR.48. Multiple values are seperated by ','.""")
        general_form_layout.addRow(QLabel('Collection ID Not:'), self.collection_id_not_input)

        self.time_input = DateRangeInput()
        general_form_layout.addRow(QLabel('Observation date:'), self.time_input)

        general_layout.addLayout(general_form_layout)
        general_tab.setLayout(general_layout)
        tab_widget.addTab(general_tab, "General")

        # Taxon Parameters Tab
        taxon_tab = QWidget()
        taxon_layout = QVBoxLayout()
        taxon_form_layout = QFormLayout()

        self.taxon_id_input = QLineEdit()
        self.taxon_id_input.setToolTip("""ID or the name of the taxon. E.g. MX.36308, parus major or talitiainen. Multiple values are seperated by ','.""")
        taxon_form_layout.addRow(QLabel('Taxon ID or name:'), self.taxon_id_input)

        self.informal_taxon_group_id_input = QLineEdit()
        self.informal_taxon_group_id_input.setToolTip("""ID of the informal taxon group. E.g. MX.37580. Multiple values are seperated by ','.""")
        taxon_form_layout.addRow(QLabel('Informal Taxon Group ID:'), self.informal_taxon_group_id_input)

        self.informal_taxon_group_id_not_input = QLineEdit()
        self.informal_taxon_group_id_not_input.setToolTip("""ID of the informal taxon group to exclude. E.g. MX.37580'. Multiple values are seperated by ','.""")
        taxon_form_layout.addRow(QLabel('Informal Taxon Group ID Not:'), self.informal_taxon_group_id_not_input)

        self.finnish_checkbox = QCheckBox()
        self.finnish_checkbox.setToolTip('True for Finnish taxa')
        taxon_form_layout.addRow(QLabel('Finnish:'), self.finnish_checkbox)

        self.invasive_checkbox = QCheckBox()
        self.invasive_checkbox.setToolTip('True for invasive taxa')
        taxon_form_layout.addRow(QLabel('Invasive:'), self.invasive_checkbox)

        self.wild_combo = CheckableComboBox()
        self.wild_combo.addItems(['WILD', 'WILD_UNKNOWN', 'NON_WILD'])
        self.wild_combo.setToolTip('Wild status of the taxa. If multiple, this is OR search.')
        taxon_form_layout.addRow(QLabel('Wild:'), self.wild_combo)

        taxon_layout.addLayout(taxon_form_layout)
        taxon_tab.setLayout(taxon_layout)
        tab_widget.addTab(taxon_tab, "Taxon")

        # Administrative Parameters Tab
        administrative_tab = QWidget()
        administrative_layout = QVBoxLayout()
        administrative_form_layout = QFormLayout()

        self.administrative_status_id_combo = CheckableComboBox()
        self.administrative_status_id_combo.addItems(list(self.ranges['MX.adminStatusEnum'].keys()))
        administrative_form_layout.addRow(QLabel('Administrative statuses:'), self.administrative_status_id_combo)
        self.administrative_status_id_combo.setToolTip('Select administrative status. If multiple, this is OR search.')

        self.red_list_status_id_combo = CheckableComboBox()
        self.red_list_status_id_combo.addItems(list(self.ranges['MX.iucnStatuses'].keys()))
        administrative_form_layout.addRow(QLabel('Red list statuses:'), self.red_list_status_id_combo)
        self.red_list_status_id_combo.setToolTip('Select red list status. If multiple, this is OR search.')

        self.taxon_admin_filters_operator_combo = QComboBox()
        self.taxon_admin_filters_operator_combo.addItems(['OR', 'AND'])
        self.taxon_admin_filters_operator_combo.setToolTip('Operator for taxon admin filters. If multiple, this is OR search.')
        administrative_form_layout.addRow(QLabel('Taxon Admin Filters Operator:'), self.taxon_admin_filters_operator_combo)

        self.atlas_code_combo = CheckableComboBox()
        self.atlas_code_combo.addItems(list(self.ranges['MY.atlasCodeEnum'].keys()))
        administrative_form_layout.addRow(QLabel('Atlas codes'), self.atlas_code_combo)
        self.atlas_code_combo.setToolTip('Select atlas code. If multiple, this is OR search.')

        self.atlas_class_combo = CheckableComboBox()
        self.atlas_class_combo.addItems(list(self.ranges['MY.atlasClassEnum'].keys()))
        administrative_form_layout.addRow(QLabel('Atlas classes:'), self.atlas_class_combo)
        self.atlas_class_combo.setToolTip('Select atlas class. If multiple, this is OR search.')

        administrative_layout.addLayout(administrative_form_layout)
        administrative_tab.setLayout(administrative_layout)
        tab_widget.addTab(administrative_tab, "Administrative")

        # Geographical Parameters Tab
        geographical_tab = QWidget()
        geographical_layout = QVBoxLayout()
        geographical_form_layout = QFormLayout()

        self.country_id_combo = CheckableComboBox()
        self.country_id_combo.addItems(sorted(list(self.areas['countries'].keys())))
        geographical_form_layout.addRow(QLabel('Country:'), self.country_id_combo)
        self.country_id_combo.setToolTip('Select country name')

        self.finnish_municipality_id_combo = CheckableComboBox()
        self.finnish_municipality_id_combo.addItems(sorted(list(self.areas['municipalities'].keys())))
        self.finnish_municipality_id_combo.setToolTip('Name of the Finnish municipality')
        geographical_form_layout.addRow(QLabel('Finnish Municipality:'), self.finnish_municipality_id_combo)

        self.biogeographical_province_id_combo = CheckableComboBox()
        self.biogeographical_province_id_combo.addItems(sorted(list(self.areas['biogeographical_areas'].keys())))
        self.biogeographical_province_id_combo.setToolTip('Name of the biogeographical province')
        geographical_form_layout.addRow(QLabel('Biogeographical Province:'), self.biogeographical_province_id_combo)

        self.ely_centre_id_combo = CheckableComboBox()
        self.ely_centre_id_combo.addItems(sorted(list(self.areas['ely_centers'].keys())))
        self.ely_centre_id_combo.setToolTip('Name of the ELY centre')
        geographical_form_layout.addRow(QLabel('ELY Centre area:'), self.ely_centre_id_combo)

        self.province_id_combo = CheckableComboBox()
        self.province_id_combo.addItems(sorted(list(self.areas['provinces'].keys())))
        self.province_id_combo.setToolTip('Finnish province')
        geographical_form_layout.addRow(QLabel('Province:'), self.province_id_combo)

        self.bird_association_area_id_combo = CheckableComboBox()
        self.bird_association_area_id_combo.addItems(sorted(list(self.areas['bird_association_areas'].keys())))
        self.bird_association_area_id_combo.setToolTip('Name of the bird association area')
        geographical_form_layout.addRow(QLabel('Bird Association Area:'), self.bird_association_area_id_combo)

        self.area_input = QLineEdit()
        self.area_input.setToolTip("""Filter using name of country, municipality, province or locality. Multiple values are seperated by ','.""")
        geographical_form_layout.addRow(QLabel('Area:'), self.area_input)

        self.named_place_id_input = QLineEdit()
        self.named_place_id_input.setToolTip("""Filter based on URI or Qname identifier of a NamedPlace. Use NamedPlace-API to find identifiers. Multiple values are seperated by ','. API resource: /named-places""")
        geographical_form_layout.addRow(QLabel('Named Place ID:'), self.named_place_id_input)

        self.coordinate_accuracy_max_slider = QSlider(Qt.Horizontal)
        self.coordinate_accuracy_max_slider.setMinimum(0)
        self.coordinate_accuracy_max_slider.setPageStep(100)
        self.coordinate_accuracy_max_slider.setMaximum(10000)
        self.coordinate_accuracy_max_slider.setSingleStep(100)
        self.coordinate_accuracy_max_slider.setPageStep(1000)
        self.coordinate_accuracy_label = QLabel('Not set')
        self.coordinate_accuracy_max_slider.setToolTip('Exclude coordinates that are less accurate or equal than the provided value (inclusive). Value is meters.')
        self.coordinate_accuracy_max_slider.valueChanged.connect(lambda value: self.coordinate_accuracy_label.setText(str(value)))
        geographical_form_layout.addRow(QLabel('Coordinate Accuracy Max:'), self.coordinate_accuracy_max_slider)
        geographical_form_layout.addRow(self.coordinate_accuracy_label)

        self.source_of_coordinates_combo = CheckableComboBox()
        self.source_of_coordinates_combo.addItems(['COORDINATES', 'COORDINATES_CENTERPOINT', 'REPORTED_VALUE', 'FINNISH_MUNICIPALITY', 'FINNISH_OLD_MUNICIPALITY'])
        self.source_of_coordinates_combo.setToolTip('Filter based on source of the coordinates')
        geographical_form_layout.addRow(QLabel('Source of Coordinates:'), self.source_of_coordinates_combo)

        geographical_layout.addLayout(geographical_form_layout)
        geographical_tab.setLayout(geographical_layout)
        tab_widget.addTab(geographical_tab, "Geographical")

        # Quality Parameters Tab
        quality_tab = QWidget()
        quality_layout = QVBoxLayout()
        quality_form_layout = QFormLayout()

        self.collection_quality_combo = CheckableComboBox()
        self.collection_quality_combo.addItems(['PROFESSIONAL', 'HOBBYIST', 'AMATEUR'])
        self.collection_quality_combo.setToolTip('Filter based on quality rating of collections.')
        quality_form_layout.addRow(QLabel('Collection Quality:'), self.collection_quality_combo)

        self.record_quality_combo = CheckableComboBox()
        self.record_quality_combo.addItems(['EXPERT_VERIFIED', 'COMMUNITY_VERIFIED', 'NEUTRAL', 'UNCERTAIN', 'ERRONEOUS'])
        self.record_quality_combo.setToolTip('Filter using quality rating of the occurrence')
        quality_form_layout.addRow(QLabel('Record Quality:'), self.record_quality_combo)

        quality_layout.addLayout(quality_form_layout)
        quality_tab.setLayout(quality_layout)
        tab_widget.addTab(quality_tab, "Quality")

        layout.addWidget(tab_widget)

        # Others Parameters Tab
        others_tab = QWidget()
        others_layout = QVBoxLayout()
        others_form_layout = QFormLayout()

        self.wild_card_input = QLineEdit()
        self.wild_card_input.setToolTip('Pass filters that are not defined in this dialog but can be used in https://api.laji.fi/explorer/#!/Warehouse/get_warehouse_query_unit_list. Use format "parameterName=parameterValue". For example, "annotated=true".')
        others_form_layout.addRow(QLabel('Other api.laji.fi filters:'), self.wild_card_input)

        self.use_test_api_checkbox = QCheckBox("Use Test API")
        self.use_test_api_checkbox.setToolTip('For testing purposes only. Remember to change your API KEY.')
        others_form_layout.addRow(self.use_test_api_checkbox)

        restricted_label = QLabel(
            '<p>Do you need sensitive and not-coarsened data? '
            '<a href="https://info.laji.fi/etusivu/aineistopyynnot/" style="color:blue; text-decoration:none;">Make a data request</a>.</p>'
        )
        restricted_label.setOpenExternalLinks(True)
        others_form_layout.addWidget(restricted_label)

        feedback_label = QLabel(
            '<p>Do you have feedback or questions? Please send an email to '
            '<a href="mailto:alpo.turunen@helsinki.fi" style="color:blue; text-decoration:none;">helpdesk@laji.fi</a>.</p>'
        )
        feedback_label.setOpenExternalLinks(True)
        others_form_layout.addWidget(feedback_label)

        others_layout.addLayout(others_form_layout)
        others_tab.setLayout(others_layout)

        tab_widget.addTab(others_tab, "Others")

        # Widgets in all tabs
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        layout.addWidget(self.progress_bar)

        self.reset_button = QPushButton('Reset values')
        self.reset_button.clicked.connect(self.reset)
        layout.addWidget(self.reset_button)

        self.submit_button = QPushButton('Submit')
        self.submit_button.clicked.connect(self.run)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    
    def reset(self):
        """When user clicks reset values button"""
        self.crs_combo.setCurrentIndex(0)
        self.geom_type_combo.setCurrentIndex(0)
        self.collection_id_input.clear()
        self.collection_id_not_input.clear()
        self.time_input.reset() 
        self.wild_card_input.clear()
        self.taxon_id_input.clear()
        self.informal_taxon_group_id_input.clear()
        self.informal_taxon_group_id_not_input.clear()
        self.finnish_checkbox.setChecked(False)
        self.invasive_checkbox.setChecked(False)
        self.wild_combo.setCurrentIndex(0)
        self.taxon_admin_filters_operator_combo.setCurrentIndex(0)
        self.administrative_status_id_combo.clearSelection()
        self.red_list_status_id_combo.clearSelection()
        self.atlas_code_combo.clearSelection()
        self.atlas_class_combo.clearSelection()
        self.country_id_combo.clearSelection()
        self.finnish_municipality_id_combo.clearSelection()
        self.biogeographical_province_id_combo.clearSelection()
        self.ely_centre_id_combo.clearSelection()
        self.province_id_combo.clearSelection()
        self.bird_association_area_id_combo.clearSelection()
        self.area_input.clear()
        self.named_place_id_input.clear()
        self.coordinate_accuracy_max_slider.setValue(0)
        self.source_of_coordinates_combo.setCurrentIndex(0)
        self.collection_quality_combo.setCurrentIndex(0)
        self.record_quality_combo.setCurrentIndex(0)
        self.use_test_api_checkbox.setChecked(False)

    def run(self):
        """When user clicks submit button"""
        if self.is_running:
            self.is_running = False
            self.submit_button.setText('Submit')
            return
        else:
            self.is_running = True
            self.submit_button.setText('Cancel')

        crs = self.crs_combo.currentText()
        geom_type = self.geom_type_combo.currentText()
        collection_id = self.collection_id_input.text()
        collection_id_not = self.collection_id_not_input.text()
        time = self.time_input.get_selected_dates()
        taxon_id = self.taxon_id_input.text()
        informal_taxon_group_id = self.informal_taxon_group_id_input.text()
        informal_taxon_group_id_not = self.informal_taxon_group_id_not_input.text()
        finnish = self.finnish_checkbox.isChecked()
        invasive = self.invasive_checkbox.isChecked()
        wild = self.wild_combo.currentText()
        taxon_admin_filters_operator = self.taxon_admin_filters_operator_combo.currentText()
        wild_card = self.wild_card_input.text()
        area = self.area_input.text()
        named_place_id = self.named_place_id_input.text()
        coordinate_accuracy_max = self.coordinate_accuracy_max_slider.value()
        source_of_coordinates = self.source_of_coordinates_combo.currentText()
        collection_quality = self.collection_quality_combo.currentText()
        record_quality = self.record_quality_combo.currentText()
        access_token = self.access_token_input.text()
        use_test_api = self.use_test_api_checkbox.isChecked()
    
        administrative_status_id = map_values(self.administrative_status_id_combo, self.ranges['MX.adminStatusEnum'])
        red_list_status_id = map_values(self.red_list_status_id_combo, self.ranges['MX.iucnStatuses'])
        atlas_code = map_values(self.atlas_code_combo, self.ranges['MY.atlasCodeEnum'])
        atlas_class = map_values(self.atlas_class_combo, self.ranges['MY.atlasClassEnum'])
        country_id = map_values(self.country_id_combo, self.areas['countries'])
        finnish_municipality_id = map_values(self.finnish_municipality_id_combo, self.areas['municipalities'])
        biogeographical_province_id = map_values(self.biogeographical_province_id_combo, self.areas['biogeographical_areas'])
        ely_centre_id = map_values(self.ely_centre_id_combo, self.areas['ely_centers'])
        province_id = map_values(self.province_id_combo, self.areas['provinces'])
        bird_association_area_id = map_values(self.bird_association_area_id_combo, self.areas['bird_association_areas'])
    
        params = {
            "crs": CRS_MAPPINGS.get(crs, 'WGS84'),
            "featureType": geom_type,
            "access_token": access_token
        }

        if collection_id:
            params["collectionId"] = collection_id
        if collection_id_not:
            params["collectionIdNot"] = collection_id_not
        if time:
            params["time"] = time
        if taxon_id:
            params["target"] = taxon_id
        if informal_taxon_group_id:
            params["informalTaxonGroupId"] = informal_taxon_group_id
        if informal_taxon_group_id_not:
            params["informalTaxonGroupIdNot"] = informal_taxon_group_id_not
        if finnish:
            params["finnish"] = finnish
        if invasive:
            params["invasive"] = invasive
        if use_test_api:
            params["use_test_api"] = use_test_api
        if wild:
            params["wild"] = wild
        if administrative_status_id:
            params["administrativeStatusId"] = administrative_status_id
        if red_list_status_id:
            params["redListStatusId"] = red_list_status_id
        if taxon_admin_filters_operator:
            params["taxonAdminFiltersOperator"] = taxon_admin_filters_operator
        if atlas_code:
            params["atlasCode"] = atlas_code
        if atlas_class:
            params["atlasClass"] = atlas_class
        if country_id:
            params["countryId"] = country_id
        if finnish_municipality_id:
            params["finnishMunicipalityId"] = finnish_municipality_id
        if biogeographical_province_id:
            params["biogeographicalProvinceId"] = biogeographical_province_id
        if ely_centre_id:
            params["elyCentreId"] = ely_centre_id
        if province_id:
            params["provinceId"] = province_id
        if area:
            params["area"] = area
        if named_place_id:
            params["namedPlaceId"] = named_place_id
        if bird_association_area_id:
            params["birdAssociationAreaId"] = bird_association_area_id
        if coordinate_accuracy_max:
            params["coordinateAccuracyMax"] = coordinate_accuracy_max
        if source_of_coordinates:
            params["sourceOfCoordinates"] = source_of_coordinates
        if collection_quality:
            params["collectionQuality"] = collection_quality
        if record_quality:
            params["recordQuality"] = record_quality
        if wild_card:
            if not validate_wild_card(wild_card, self):
                return
            key, value = wild_card.split('=')
            params[key] = value

        if not params["access_token"]:
            QMessageBox.warning(None, 'FinBIF_Plugin', 'Access token is mandatory.')
            self.is_running = False
            self.submit_button.setText('Submit')
            return
        
        self.settings.setValue("FinBIF_API_Plugin/access_token", params["access_token"])
        
        total_obs = get_total_obs(params)
        param_text = "\n".join(f"{key}: {value}" for key, value in params.items() if key != "access_token")

        if total_obs and total_obs > MAX_OBSERVATIONS_LIMIT:
            QMessageBox.warning(
                None, 
                'FinBIF_Plugin', 
                f'Error: You are trying to fetch {total_obs:,} occurrences, which exceeds '
                f'the maximum limit of {MAX_OBSERVATIONS_LIMIT:,} records.\n\n'
                f'Please refine your search parameters to reduce the number of results.\n\n'
                f'Parameters:\n{param_text}',
                QMessageBox.Ok
            )
            self.is_running = False
            self.submit_button.setText('Submit')
            return
        else:
            reply = QMessageBox.question(
                None, 
                'FinBIF_Plugin', 
                f'Fetching {total_obs} occurrences with the following parameters:\n\n{param_text}\n\nDo you want to continue?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

        if reply == QMessageBox.No:
            self.is_running = False
            self.submit_button.setText('Submit')
            return

        self.progress_bar.setValue(0)
        
        # Map the CRS to QGIS using constants
        epsg_string = EPSG_MAPPINGS.get(params["crs"])
        qgis_crs = QgsCoordinateReferenceSystem(epsg_string)

        # Fetch all data at once
        gdf = fetch_data(params, self.progress_bar, epsg_string)
        
        if gdf is not None and not gdf.empty:
            # Process all data at once
            gdf = merge_taxonomy_data(gdf, self.informal_taxon_names)
            gdf = map_collection_id(gdf, self.collection_names)
            gdf = combine_similar_columns(gdf)
            gdf = convert_geometry_collection_to_multipolygon(gdf)
            gdf = validate_geometry(gdf)
            
            if not gdf.empty:
                total_features = len(gdf)
                
                # Group by geometry type and create layers
                gdfs_by_type = {}
                geom_types = gdf.geometry.geom_type.unique()
                
                for geom_type in geom_types:
                    subset_gdf = gdf[gdf.geometry.geom_type == geom_type]
                    if not subset_gdf.empty:
                        gdfs_by_type[geom_type] = subset_gdf

                # Create one layer per geometry type
                for geom_type, type_gdf in gdfs_by_type.items():
                    layer_name = f"FinBIF_{geom_type}_Occurrences"
                    create_layer(type_gdf, layer_name, qgis_crs)

                QMessageBox.information(None, 'FinBIF_Plugin', f'API Query loaded {total_features} records to the map successfully.')
            else:
                QMessageBox.information(None, 'FinBIF_Plugin', 'No valid data after processing.')
        else:
            QMessageBox.information(None, 'FinBIF_Plugin', 'No data was retrieved from the API')

        self.is_running = False
        self.submit_button.setText('Submit')
        self.progress_bar.setValue(0)