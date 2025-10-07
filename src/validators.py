import re
from PyQt5.QtWidgets import QMessageBox

def validate_email(email, parent=None):
    """Validate email format and show error if invalid."""
    if not email or not email.strip():
        QMessageBox.warning(parent, "Invalid Email", "Please enter a valid email address.")
        return False
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
        QMessageBox.warning(parent, "Invalid Email", "Please enter a valid email address.")
        return False
    return True

def validate_wild_card(wild_card, parent=None):
    """Validate wild card parameter format (key=value)."""
    if not wild_card or not wild_card.strip():
        return True, None, None  # Empty is valid
    
    try:
        key, value = wild_card.split('=', 1)
        if key.strip() and value.strip():
            return True, key.strip(), value.strip()
    except ValueError:
        pass
    
    QMessageBox.warning(parent, "Invalid Wild Card", "Please enter a valid wild card parameter (key=value).")
    return False, None, None