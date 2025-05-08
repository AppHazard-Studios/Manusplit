"""
Manusplit - A tool for splitting large documents into smaller parts.
Main entry point for the application.
"""
import os
import sys
import logging
from pathlib import Path

# Local imports
from settings import Settings
from utils import setup_logging
from gui import ManusplitApp  # Updated to use the new class name
import version


def main():
    """Main entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting Manusplit v{version.get_version()}")

    try:
        # Create PyQt application
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_path))

        # Load settings
        settings = Settings()
        logger.info("Settings loaded")

        # Ensure output directory exists
        output_dir = Path(settings.get("output_folder"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Set application style
        app.setStyle("Fusion")

        # Create and show the main window
        window = ManusplitApp(settings)  # Use the new class name here too
        window.show()

        # Run the application
        sys.exit(app.exec())

    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        # In GUI mode, we've already shown error dialogs
        sys.exit(1)


if __name__ == "__main__":
    main()