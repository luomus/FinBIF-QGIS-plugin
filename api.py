import requests
from PyQt5.QtWidgets import QMessageBox, QApplication
import json, certifi

def fetch_data(params, progress_bar):
    base_url = "https://api.laji.fi/v0/warehouse/query/unit/list"

    params["format"] = "geojson"
    params["page"] = 1
    params["pageSize"] = 1000

    all_features = []
    last_page = None

    while True:
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
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

def request_api_key(email, dialog):
    if not email:
        return 
    
    url = "https://api.laji.fi/v0/api-users"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = json.dumps({"email": email})
    
    try:
        response = requests.post(url, headers=headers, data=data, verify=certifi.where())
        if response.status_code in [200, 201]:
            QMessageBox.information(None, 'FinBIF_Plugin', 'API key request sent. Check your email for further instructions.')
        else:
            QMessageBox.warning(None, 'FinBIF_Plugin', f"Error: {response.status_code}, {response.text}")
    except requests.exceptions.SSLError as ssl_error:
        QMessageBox.warning(None, 'FinBIF_Plugin', f'SSL Error: {ssl_error}')
    except Exception as e:
        QMessageBox.warning(None, 'FinBIF_Plugin', f"Mystery error: {e}. Check your email or try again later?")
    
    dialog.accept()
