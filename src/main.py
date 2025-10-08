from PyQt5.QtWidgets import QAction, QApplication, QProgressDialog, QMessageBox
from PyQt5.QtCore import Qt
from .ui.main_dialog import FinBIFDialog
from .mappings import load_areas, load_ranges
from .api import load_collection_names, load_informal_taxon_names

class FinBIF_API_Plugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self._data_loaded = False
        self.areas = None
        self.ranges = None
        self.collection_names = None
        self.informal_taxon_names = None

    def load_data(self):
        """Load all required data for the plugin. Called lazily when dialog is first opened."""
        if self._data_loaded:
            return
        
        # Show progress dialog
        progress = QProgressDialog("Loading plugin data...", "Cancel", 0, 4)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("FinBIF Plugin")
        progress.show()
        QApplication.processEvents()

        try:

            if progress.wasCanceled():
                return
            
            progress.setLabelText("Loading areas...")
            self.areas = load_areas()
            progress.setValue(1)
            QApplication.processEvents()

            if progress.wasCanceled():
                return

            progress.setLabelText("Loading ranges...")
            self.ranges = load_ranges()
            progress.setValue(2)
            QApplication.processEvents()

            if progress.wasCanceled():
                return
            
            progress.setLabelText("Loading collection names...")
            self.collection_names = load_collection_names()
            progress.setValue(3)
            QApplication.processEvents()

            if progress.wasCanceled():
                return
            
            progress.setLabelText("Loading informal taxon names...")
            self.informal_taxon_names = load_informal_taxon_names()
            progress.setValue(4)
            QApplication.processEvents()

            progress.close()
            self._data_loaded = True

        except Exception as e:
            progress.close()
            QMessageBox.critical(None, 'FinBIF Plugin Error', 
                               f'Failed to load plugin data: {str(e)}\n\n'
                               'Please check your internet connection and try again.')
            raise

    def initGui(self):
        self.action = QAction('FinBIF API', self.iface.mainWindow())
        self.action.triggered.connect(self.show_dialog)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def show_dialog(self):
        self.load_data()
        if self._data_loaded:
            if not self.dialog:
                self.dialog = FinBIFDialog(self.iface, self.areas, self.ranges, self.collection_names, self.informal_taxon_names)
            self.dialog.show()