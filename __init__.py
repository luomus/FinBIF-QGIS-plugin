from importlib.util import find_spec


def classFactory(iface):
    required = (
        "numpy", "pandas", "geopandas", "shapely",
        "requests", "certifi", "urllib3",
    )
    missing = [name for name in required if find_spec(name) is None]

    if missing:
        from qgis.PyQt.QtWidgets import QMessageBox

        message = (
            "FinBIF plugin cannot start because these Python packages are missing:\n\n"
            + ", ".join(missing)
            + "\n\nInstall them in the Python environment used by QGIS, "
              "then restart QGIS and enable the plugin again.\n\n"
              "For OSGeo4W, use the OSGeo4W installer. For a system-packaged "
              "QGIS on Linux, use your distribution's package manager. "
              "For other installations, consult the QGIS distributor's instructions."
        )
        QMessageBox.critical(iface.mainWindow(), "FinBIF dependencies", message)
        raise RuntimeError("Missing FinBIF dependencies: " + ", ".join(missing))

    from .src.main import FinBIF_API_Plugin
    return FinBIF_API_Plugin(iface)
