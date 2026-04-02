"""Entry Point for the Patrimony App. Made with Reflex!"""

# Import all the pages.
import reflex as rx

from .backend.config.logging_config import setup_backend_logging
from .frontend.config.logging_config import setup_frontend_logging
from .frontend.styles import styles
from .frontend.pages import *  # noqa: F403

# Configure logging before anything else runs
setup_backend_logging()
setup_frontend_logging()

# Create the app.
app = rx.App(
    style=styles.base_style,
    stylesheets=styles.base_stylesheets,
)
