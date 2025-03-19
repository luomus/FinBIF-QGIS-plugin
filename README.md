# QGIS plugin for FinBIF API

## Overview

The FinBIF API Plugin for QGIS allows users to fetch data from the FinBIF API and load it directly into QGIS. This plugin provides a user-friendly interface to query the FinBIF API and visualize the data on a map.

## Features

- Fetch data from the [data warehouse endpoint of FinBIF API](https://api.laji.fi/explorer/#!/Warehouse/get_warehouse_query_unit_list)
- Load data into QGIS as vector layers
- Support for various query parameters including taxon, geographical, and quality parameters
- User-friendly interface

## Installation

1. Download the [plugin.zip](https://github.com/luomus/FinBIF-QGIS-plugin/blob/main/plugin.zip) file from the repository.
2. Open QGIS and go to `Plugins` > `Manage and Install Plugins`.
3. Click on the `Install from ZIP` button and select the downloaded plugin ZIP file.
4. Click `Install Plugin`.
5. The plugin should be visible on the QGIS toolbar

![image](https://github.com/user-attachments/assets/4ee7d5fe-7558-4b9c-8541-f07d330b2f46)



## Usage

1. Open QGIS and click plugin to open it
2. Enter your FinBIF API access token in the `General` tab. If you don't have any, you can request one from the "Get API KEY" button.
3. Configure the desired query parameters across the different tabs (General, Taxon, Administrative, Geographical, Quality, Others). If you need more parameters (that are not pre-defined), you can add them on the `Others` tab using format `parameterName=parameterValue1`. If multiple new parameters, separate by `&` character. Find all possible parameters from `https://api.laji.fi/explorer/#!/Warehouse/get_warehouse_query_unit_list`. 
4. Click the `Submit` button to fetch data from the FinBIF API. Avoid fetching too much data at one query.
5. The fetched data will be loaded into QGIS as vector layers.

![image](https://github.com/user-attachments/assets/5d27573d-8e2b-46b9-9738-6387080bb4b9)

## Author

Alpo Turunen

## License

This plugin is free to use and edit for all purposes
