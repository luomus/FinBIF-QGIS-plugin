from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox
from ..validators import validate_email
from ..api import request_api_key


def open_api_key_dialog(self):
    dialog = QDialog()
    dialog.setWindowTitle("Get token")
    layout = QVBoxLayout()

    email_input = QLineEdit()
    email_input.setPlaceholderText("Enter your email")
    layout.addWidget(email_input)
    
    def on_accept():
        email = email_input.text().strip()
        if not validate_email(email, dialog):
            return
        request_api_key(email, dialog) # sends the email to the API
        dialog.accept()

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    button_box.accepted.connect(on_accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)
    
    dialog.setLayout(layout)
    dialog.exec()