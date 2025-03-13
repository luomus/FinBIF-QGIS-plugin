import requests
from PyQt5.QtWidgets import QMessageBox, QApplication

def fetch_data(params, progress_bar):
    base_url = "https://api.laji.fi/v0/warehouse/query/unit/list"
    params["format"] = "geojson"
    params["page"] = 1
    params["pageSize"] = 100

    all_features = []
    last_page = None

    while True:
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

    return all_features
