"""
Configuration management for Manusplit application.
Handles loading, saving, and validating user settings.
"""
import json
import os
import logging
from pathlib import Path


class Settings:
    """Manages application settings with validation and persistence."""
    
    # Default settings - updated to set preserve_formatting and skip_under_limit to False
    DEFAULT_SETTINGS = {
        "max_words": 50000,
        "output_folder": "./output",
        "preserve_formatting": False,  # Changed from True
        "skip_under_limit": False,     # Changed from True
        "dark_mode": None,  # None = system default
        "check_updates": True
    }

    # Setting constraints
    CONSTRAINTS = {
        "max_words": {
            "min": 1000,
            "max": 100000,
            "type": int
        }
    }

    def __init__(self, config_path=None):
        """Initialize settings with optional custom config path."""
        self.logger = logging.getLogger(__name__)

        if config_path is None:
            # Use default path in same directory as script
            self.config_path = Path(os.path.dirname(os.path.abspath(__file__))) / "settings.json"
        else:
            self.config_path = Path(config_path)

        # Current settings dict
        self.settings = self.DEFAULT_SETTINGS.copy()

        # Load settings if file exists
        self.load()

    def load(self):
        """Load settings from file, falling back to defaults if necessary."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)

                # Update settings with loaded values (keeping defaults for missing keys)
                for key, value in loaded_settings.items():
                    if key in self.settings:
                        # Validate the setting before accepting it
                        if self._validate_setting(key, value):
                            self.settings[key] = value
                        else:
                            self.logger.warning(f"Invalid setting value for {key}: {value}, using default")

                self.logger.info("Settings loaded successfully")
            else:
                self.logger.info("No settings file found, using defaults")
                # Create output folder if it doesn't exist
                self._ensure_output_folder()

        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error loading settings: {str(e)}")
            # Continue with defaults

    def save(self):
        """Save current settings to file."""
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)

            self.logger.info("Settings saved successfully")
            return True
        except IOError as e:
            self.logger.error(f"Error saving settings: {str(e)}")
            return False

    def get(self, key, default=None):
        """Get a setting value with optional default."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value with validation."""
        if key not in self.settings:
            self.logger.warning(f"Attempted to set unknown setting: {key}")
            return False

        if not self._validate_setting(key, value):
            self.logger.warning(f"Invalid value for setting {key}: {value}")
            return False

        self.settings[key] = value

        # Create output folder if needed
        if key == "output_folder":
            self._ensure_output_folder()

        return True

    def reset(self):
        """Reset all settings to defaults."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.save()
        self._ensure_output_folder()

    def _validate_setting(self, key, value):
        """Validate setting against constraints."""
        if key not in self.settings:
            return False

        # Apply specific constraints if defined
        if key in self.CONSTRAINTS:
            constraints = self.CONSTRAINTS[key]

            # Check type
            if "type" in constraints and not isinstance(value, constraints["type"]):
                return False

            # Check min/max for numeric values
            if isinstance(value, (int, float)):
                if "min" in constraints and value < constraints["min"]:
                    return False
                if "max" in constraints and value > constraints["max"]:
                    return False

        return True

    def _ensure_output_folder(self):
        """Ensure the output folder exists."""
        try:
            output_path = Path(self.settings["output_folder"])
            output_path.mkdir(parents=True, exist_ok=True)
        except (OSError, IOError) as e:
            self.logger.error(f"Failed to create output folder: {str(e)}")
            # Fall back to default if there's an issue
            self.settings["output_folder"] = self.DEFAULT_SETTINGS["output_folder"]
            # Try again with default
            Path(self.settings["output_folder"]).mkdir(parents=True, exist_ok=True)