"""Entry Point for the Patrimony App. Made with Reflex!"""

# Import all the pages.
import reflex as rx

from .frontend.styles import styles
from .frontend.pages import *

# Create the app.
app = rx.App(
    style=styles.base_style,
    stylesheets=styles.base_stylesheets,
)
