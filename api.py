import requests
from PyQt5.QtWidgets import QMessageBox, QApplication
import json, certifi

def fetch_data(params, progress_bar):
    if 'use_test_api' in params:
        api_base_url = "https://apitest.laji.fi/v0/"
        params.pop('use_test_api')
    else:
        api_base_url = "https://api.laji.fi/v0/"
    base_url = api_base_url + "warehouse/query/unit/list"
    
    params["format"] = "geojson"
    params["page"] = 1
    params["pageSize"] = 10000
    params["selected"] = "document.linkings.collectionQuality,document.loadDate,unit.linkings.taxon.threatenedStatus,unit.linkings.originalTaxon.administrativeStatuses,unit.linkings.taxon.taxonomicOrder,unit.linkings.originalTaxon.latestRedListStatusFinland.status,gathering.displayDateTime,gathering.interpretations.biogeographicalProvinceDisplayname,gathering.interpretations.coordinateAccuracy,unit.abundanceUnit,unit.atlasCode,unit.atlasClass,gathering.locality,unit.unitId,unit.linkings.taxon.scientificName,unit.interpretations.individualCount,unit.interpretations.recordQuality,unit.abundanceString,gathering.eventDate.begin,gathering.eventDate.end,gathering.gatheringId,document.collectionId,unit.det,unit.lifeStage,unit.linkings.taxon.id,unit.notes,unit.sex,document.documentId,document.notes,document.secureReasons,gathering.notes,gathering.team,unit.keywords,unit.linkings.taxon.nameSwedish,unit.linkings.taxon.nameEnglish,document.dataSource"



    all_features = []
    last_page = None

    while True:
        try:
            response = requests.get(base_url, params=params)
            if response.status_code in [200, 201]:
                data = response.json()
                if not last_page:
                    last_page = data.get('lastPage')
                    progress_bar.setMaximum(last_page)

                    total_records = data.get('total')
                    if total_records > 1000000:
                        QMessageBox.warning(None, 'FinBIF_Plugin', 'The number of features exceeds 1 million. Please refine your parameters.')
                        break
                features = data.get('features', [])
                all_features.extend(features)

                params["page"] += 1
                progress_bar.setValue(params["page"])  # Update progress bar
                if not data.get('nextPage'):
                    break
            else:
                QMessageBox.warning(None, 'FinBIF_Plugin', f'API Query Failed: {response.status_code} {response.text}')
                break
            QApplication.processEvents()  # Keep UI responsive

        except requests.exceptions.SSLError as ssl_error:
            QMessageBox.warning(None, 'FinBIF_Plugin', f'SSL Error: {ssl_error}')
            break
        except Exception as e:
            QMessageBox.warning(None, 'FinBIF_Plugin', f'Unexpected error: {e}')
            break
    return all_features

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

def get_total_obs(url):
    """
    Get the last page number from the API response with retry logic.

    Parameters:
    url (str): The URL of the Warehouse API endpoint.

    Returns:
    int: Total numbers of occurrences from the API.
    """
    url = url.replace('/list/', '/count/').replace('&geoJSON=true&featureType=ORIGINAL_FEATURE', '')
    api_response = requests.get(url).json()
    if api_response:
        return api_response.get('total')
    else:
        return None