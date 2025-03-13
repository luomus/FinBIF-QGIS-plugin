from .main import FinBIF_API_Plugin

def classFactory(iface):
    return FinBIF_API_Plugin(iface)

