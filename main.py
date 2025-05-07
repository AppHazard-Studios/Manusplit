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
from gui import ManusplitGUI
import version


def main():
    """Main entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting Manusplit v{version.get_version()}")
    
    try:
        # Load settings
        settings = Settings()
        logger.info("Settings loaded")
        
        # Ensure output directory exists
        output_dir = Path(settings.get("output_folder"))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Start GUI
        logger.info("Starting GUI")
        app = ManusplitGUI(settings)
        app.run()
        
        logger.info("Application exiting normally")
        
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        # In GUI mode, we've already shown error dialogs
        sys.exit(1)


if __name__ == "__main__":
    main()
