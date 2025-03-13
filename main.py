from PyQt5.QtWidgets import QAction
from .dialog import FinBIFDialog
from .mappings import load_areas, load_ranges

class FinBIF_API_Plugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.areas = load_areas()
        self.ranges = load_ranges()

    def initGui(self):
        self.action = QAction('FinBIF API', self.iface.mainWindow())
        self.action.triggered.connect(self.show_dialog)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def show_dialog(self):
        if not self.dialog:
            self.dialog = FinBIFDialog(self.iface, self.areas, self.ranges)
        self.dialog.show()