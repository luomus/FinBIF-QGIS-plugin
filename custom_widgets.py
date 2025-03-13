from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate, qApp
from PyQt5.QtGui import QStandardItem, QFontMetrics, QPalette
from PyQt5.QtCore import Qt, QEvent, QDate
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QDateEdit, QLabel, QMessageBox, QCheckBox




class DateRangeInput(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # Checkbox to activate date selection
        self.enable_checkbox = QCheckBox("Enable date selection")
        self.enable_checkbox.stateChanged.connect(self.toggle_date_selection)

        # Date inputs (initially disabled)
        self.start_date = QDateEdit(calendarPopup=True)
        self.start_date.setEnabled(False)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setSpecialValueText("Select Date")
        #self.start_date.setDate(QDate())  # Empty by default

        self.end_date = QDateEdit(calendarPopup=True)
        self.end_date.setEnabled(False)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setSpecialValueText("Select Date")
        #self.end_date.setDate(QDate())  # Empty by default

        # Layout for date fields
        date_range_layout = QHBoxLayout()
        date_range_layout.addWidget(QLabel('Start Date:'))
        date_range_layout.addWidget(self.start_date)
        date_range_layout.addWidget(QLabel('End Date:'))
        date_range_layout.addWidget(self.end_date)

        # Add widgets to main layout
        layout.addWidget(self.enable_checkbox)
        layout.addLayout(date_range_layout)
        self.setLayout(layout)

    def toggle_date_selection(self, state):
        # Enable/disable date widgets based on checkbox state
        enabled = state == 2  # 2 means 'checked' in PyQt
        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)

    def get_selected_dates(self):
        # Return None if checkbox is not enabled
        if not self.enable_checkbox.isChecked():
            return None

        start = self.start_date.date()
        end = self.end_date.date()

        # Return None if no valid date selected
        if not start.isValid() or not end.isValid():
            return None
        

        if start > end:
            QMessageBox.warning(self, 'Input Error', 'Start date cannot be after the end date.')
            return None

        # Return date or date range
        if start == end:
            return start.toString('yyyy-MM-dd')
        return f"{start.toString('yyyy-MM-dd')}/{end.toString('yyyy-MM-dd')}"

    def reset(self):
        self.enable_checkbox.setChecked(False)
        self.start_date.setDate(QDate())
        self.end_date.setDate(QDate())
        self.start_date.setEnabled(False)
        self.end_date.setEnabled(False)

class CheckableComboBox(QComboBox):

    # Subclass Delegate to increase item height
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # Make the lineedit the same color as QPushButton
        palette = qApp.palette()
        palette.setBrush(QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)

        # Use custom delegate
        self.setItemDelegate(CheckableComboBox.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, object, event):

        if object == self.lineEdit():
            if event.type() == QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if object == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
                else:
                    item.setCheckState(Qt.Checked)
                return True
        return False

    def showPopup(self):
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        texts = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                texts.append(self.model().item(i).text())
        text = ", ".join(texts)

        # Compute elided text (with "...")
        metrics = QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, Qt.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text, data=None):
        item = QStandardItem()
        item.setText(text)
        item.setToolTip(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts, datalist=None):
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)

    def currentData(self):
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                res.append(self.model().item(i).data())
        return res
    
    def clearSelection(self):
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            item.setCheckState(Qt.Unchecked)
        self.updateText()