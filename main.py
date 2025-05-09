"""
Manusplit - A tool for splitting large documents into smaller parts.
Main entry point for the application.
"""
try:
    import impfix
except ImportError:
    pass
import os
import sys
import json
import logging
from pathlib import Path

# Local imports
from settings import Settings
from utils import setup_logging
from gui import ManusplitApp
import version

def get_resource_path():
    """Get the correct path for resources"""
    if 'MANUSPLIT_RESOURCES' in os.environ:
        return os.environ['MANUSPLIT_RESOURCES']
    return os.path.dirname(os.path.abspath(__file__))

def get_settings_path():
    """Get the correct path for settings.json"""
    return os.path.join(get_resource_path(), "settings.json")


def create_default_settings_if_needed():
    """Create default settings file if needed"""
    settings_path = get_settings_path()
    logger = logging.getLogger(__name__)

    # Only create if settings file doesn't exist
    if not os.path.exists(settings_path):
        try:
            # Import Settings class defaults
            default_settings = Settings.DEFAULT_SETTINGS.copy()

            # Only override output path
            default_output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")
            default_settings["output_folder"] = default_output_path

            # Create folder if needed
            os.makedirs(default_output_path, exist_ok=True)

            # Write settings file
            with open(settings_path, "w") as f:
                json.dump(default_settings, f, indent=4)

            logger.info(f"Created settings with output folder: {default_output_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to create settings: {str(e)}")
            return False
    return True  # Settings already exist


def main():
    """Main entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting Manusplit v{version.get_version()}")

    try:
        # Create PyQt application
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)

        # Use appropriate icon format based on platform
        if sys.platform == 'darwin':  # macOS
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon2.icns")
        else:  # Windows/Linux
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")

        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_path))

        # Create default settings if needed (without showing any dialog)
        create_default_settings_if_needed()

        # Load settings
        settings = Settings()
        logger.info("Settings loaded")

        # Ensure output directory exists
        output_dir = Path(settings.get("output_folder"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Set application style
        app.setStyle("Fusion")

        # Create and show the main window
        window = ManusplitApp(settings)
        window.show()

        # Run the application
        sys.exit(app.exec())

    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        # In GUI mode, we've already shown error dialogs
        sys.exit(1)


if __name__ == "__main__":
    main()