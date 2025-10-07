import requests
from PyQt5.QtWidgets import QMessageBox, QApplication
import json, certifi
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from qgis.core import QgsMessageLog, Qgis
from PyQt5.QtWidgets import QMessageBox, QApplication
import os
import geopandas as gpd

PRODUCTION_API_BASE = "https://api.laji.fi/v0/"
TEST_API_BASE = "https://apitest.laji.fi/v0/"
REQUEST_TIMEOUT = 60  # seconds

def get_api_base_url(params):
    """Determine the API base URL based on the test API parameter."""
    if 'use_test_api' in params:
        params = params.pop('use_test_api')
        return TEST_API_BASE, params
    else:
        return PRODUCTION_API_BASE, params

@lru_cache(maxsize=1)
def load_collection_names(lang='en'):
    """
    Load collection names from the FinBIF API.
    
    Returns:
    dict: Dictionary mapping collection IDs to collection names, or empty dict if request fails
    """
    url = f"http://laji.fi/api/collections?pageSize=1500&lang={lang}"

    response = requests.get(url)
    if response and response.status_code in [200, 201]:
        data = response.json()
        if data:
            return {item['id']: item['longName'] for item in data['results']}
    
    if response:
        QgsMessageLog.logMessage(f"Warning: Failed to load collection names: {response.status_code}", "FinBIF Plugin", Qgis.Warning)
    
    return {}

def _handle_request_error(error, context="API request"):
    """Handle common request errors with appropriate user messages."""
    QgsMessageLog.logMessage(f"Error during {context}: {error}", "FinBIF Plugin", Qgis.Critical)
    
    error_messages = {
        requests.exceptions.Timeout: f'Request timed out after {REQUEST_TIMEOUT} seconds. Please try again.',
        requests.exceptions.ConnectionError: 'Unable to connect to the FinBIF API. Check your internet connection.',
        requests.exceptions.HTTPError: f'Server error: {error}. Please try again later.',
        requests.exceptions.RequestException: f'Network error: {error}'
    }
    
    message = error_messages.get(type(error), f'Unexpected error: {error}')
    QMessageBox.warning(None, 'FinBIF_Plugin', message)

def fetch_data(params, progress_bar, epsg_string):
    """
    Fetch data from FinBIF API and return as GeoDataFrame.
    
    Parameters:
    params (dict): API parameters
    progress_bar: Progress bar widget to update
    
    Yields:
    gpd.GeoDataFrame: GeoDataFrame for each page of results
    """
    api_base_url, params = get_api_base_url(params)
    full_url = api_base_url + "warehouse/query/unit/list"
    
    # Set required parameters
    params.update({
        "format": "geojson",
        "page": 1,
        "pageSize": 10000,
        "selected": "document.linkings.collectionQuality,document.loadDate,unit.linkings.taxon.threatenedStatus,unit.linkings.originalTaxon.administrativeStatuses,unit.linkings.taxon.taxonomicOrder,unit.linkings.originalTaxon.latestRedListStatusFinland.status,gathering.displayDateTime,gathering.interpretations.biogeographicalProvinceDisplayname,gathering.interpretations.coordinateAccuracy,unit.abundanceUnit,unit.atlasCode,unit.atlasClass,gathering.locality,unit.unitId,unit.linkings.taxon.scientificName,unit.interpretations.individualCount,unit.interpretations.recordQuality,unit.abundanceString,gathering.eventDate.begin,gathering.eventDate.end,gathering.gatheringId,document.collectionId,unit.det,unit.lifeStage,unit.linkings.taxon.id,unit.notes,unit.sex,document.documentId,document.notes,document.secureReasons,gathering.notes,gathering.team,unit.keywords,unit.linkings.taxon.nameSwedish,unit.linkings.taxon.nameEnglish,document.dataSource"
    })
    
    session = requests.Session()
    
    try:
        while True:
            try:
                response = session.get(full_url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                
                # Set up progress bar on first request
                if params["page"] == 1:
                    total_pages = data.get('lastPage', 1)
                    progress_bar.setMaximum(total_pages)
                
                # Convert to GeoDataFrame if features exist
                features = data.get('features', [])
                if features:
                    # Create GeoDataFrame directly from GeoJSON
                    gdf = gpd.GeoDataFrame.from_features(features, crs=epsg_string)
                    yield gdf
                
                # Update progress and check for next page
                progress_bar.setValue(params["page"])
                QApplication.processEvents()
                
                if not data.get('nextPage'):
                    break
                    
                params["page"] += 1
                
            except requests.exceptions.RequestException as e:
                _handle_request_error(e, "data fetching")
                break
                
    finally:
        session.close()

def request_api_key(email: str, dialog):
    """
    Request an API key from the FinBIF API.
    Parameters:
        email: The email address to send the API key request to.
        dialog: The dialog window to close after the request is made.
    """
    if not email:
        return
    
    url = "https://api.laji.fi/v0/api-users"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = json.dumps({"email": email})
    
    try:
        response = requests.post(url, headers=headers, data=data, verify=certifi.where())
        if response.status_code in [200, 201]:
            QMessageBox.information(None, 'FinBIF_Plugin', 'API key request sent. Check your email for further instructions.')
        elif response.status_code == 400 and "This email has been registered already" in response.text:
            renew_api_key(email, dialog)
        else:
            QMessageBox.warning(None, 'FinBIF_Plugin', f"Error: {response.status_code}, {response.text}")
    except requests.exceptions.SSLError as ssl_error:
        try:
            response = requests.post(url, headers=headers, data=data, verify=False)
            if response.status_code in [200, 201]:
                QMessageBox.information(None, 'FinBIF_Plugin', 'API key request sent. Check your email for further instructions.')
            elif response.status_code == 400 and "This email has been registered already" in response.text:
                renew_api_key(email, dialog)
            else:
                QMessageBox.warning(None, 'FinBIF_Plugin', f"Error: {response.status_code}, {response.text}")
        except Exception as fallback_error:
            QMessageBox.warning(
                None, "FinBIF Plugin",
                f"Queries with and without SSL verification failed:\n{fallback_error}"
            )
    except Exception as e:
        QMessageBox.warning(None, 'FinBIF_Plugin', f"Unexpected error: {e}. Check your email, contact helpdesk@laji.fi or try again later?")
    
    dialog.accept()

def renew_api_key(email: str, dialog):
    """
    Renew an API key for the FinBIF API.
    Parameters:
        email: The email address associated with the API key to renew.
        dialog: The dialog window to close after the renewal is made.
    """
    choice = QMessageBox.question(
        None, 
        'FinBIF_Plugin', 
        f'An API KEY already exists for this email.\n\nIf you did not find it from your email, do you want to request a new one?',
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )

    if choice == QMessageBox.Yes:
        url = "https://api.laji.fi/v0/api-users/renew"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        data = json.dumps({"email": email})
        try:
            response = requests.post(url, headers=headers, data=data, verify=certifi.where())
            if response.status_code in [200, 201]:
                QMessageBox.information(None, 'FinBIF_Plugin', 'New API key request sent. Check your email.')
            else:
                QMessageBox.warning(None, 'FinBIF_Plugin', f"Retry failed: {response.status_code}, {response.text}")
        except requests.exceptions.SSLError as ssl_error:
            try:
                response = requests.post(url, headers=headers, data=data, verify=False)
                if response.status_code in [200, 201]:
                    QMessageBox.information(None, 'FinBIF_Plugin', 'New API key request sent. Check your email.')
                else:
                    QMessageBox.warning(None, 'FinBIF_Plugin', f"Retry failed: {response.status_code}, {response.text}")
            except Exception as fallback_error:
                QMessageBox.warning(None, "FinBIF Plugin", f"Queries with and without SSL verification failed:\n{fallback_error}")
        except Exception as e:
            QMessageBox.warning(None, 'FinBIF_Plugin', f"Failed to resend API key request:\n{e}")
    else:
        QMessageBox.information(None, 'FinBIF_Plugin', 'Please check your email to find the current API KEY or contact helpdesk@laji.fi.')

    dialog.accept()

def get_total_obs(params):
    """
    Get the total number of observations from the API response.

    Parameters:
    params (dict): The parameters dictionary for the API request.

    Returns:
    int: Total numbers of occurrences from the API.
    """
    api_base_url, params = get_api_base_url(params)
    full_url = api_base_url + "warehouse/query/unit/count"
    
    try:
        response = requests.get(full_url, params=params)
        if response.status_code in [200, 201]:
            api_response = response.json()
            return api_response.get('total')
        else:
            return None
    except Exception as e:
        return None