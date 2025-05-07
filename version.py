"""
Version information and update checking for Manusplit.
"""
import logging
import requests
from datetime import datetime, timedelta

# Current version
VERSION = "1.0.0"
BUILD_DATE = "2025-05-07"

# GitHub URL for version checking
VERSION_URL = "https://raw.githubusercontent.com/yourname/manusplit/main/version.txt"

# Cache for version check
last_check = None
latest_version = None


def get_version():
    """Get current version string."""
    return VERSION


def get_build_date():
    """Get build date string."""
    return BUILD_DATE


def check_for_updates(force=False, timeout=5):
    """
    Check for updates from GitHub.
    
    Args:
        force (bool): Force check even if recently checked
        timeout (int): Request timeout in seconds
        
    Returns:
        tuple: (bool update_available, str latest_version, str current_version)
    """
    global last_check, latest_version
    logger = logging.getLogger(__name__)
    
    # Return cached result if checked within last 24 hours
    if not force and last_check and (datetime.now() - last_check) < timedelta(hours=24):
        if latest_version:
            return _compare_versions(latest_version, VERSION)
        return False, VERSION, VERSION

    try:
        # Request new version
        response = requests.get(VERSION_URL, timeout=timeout)
        
        # Check if request was successful
        if response.status_code == 200:
            # Update cache
            latest_version = response.text.strip()
            last_check = datetime.now()
            
            # Compare versions
            return _compare_versions(latest_version, VERSION)
        else:
            logger.warning(f"Failed to check for updates: HTTP {response.status_code}")
            return False, VERSION, VERSION
            
    except requests.RequestException as e:
        logger.warning(f"Error checking for updates: {str(e)}")
        return False, VERSION, VERSION


def _compare_versions(latest, current):
    """
    Compare version strings.
    
    Args:
        latest (str): Latest version string
        current (str): Current version string
        
    Returns:
        tuple: (bool update_available, str latest_version, str current_version)
    """
    try:
        # Convert version strings to tuples for comparison
        latest_parts = [int(x) for x in latest.split('.')]
        current_parts = [int(x) for x in current.split('.')]
        
        # Pad shorter version with zeros
        while len(latest_parts) < len(current_parts):
            latest_parts.append(0)
        while len(current_parts) < len(latest_parts):
            current_parts.append(0)
            
        # Compare versions
        update_available = latest_parts > current_parts
        
        return update_available, latest, current
    except (ValueError, AttributeError):
        # If parsing fails, assume no update
        return False, latest, current


def get_github_url():
    """Get GitHub URL for the project."""
    return "https://github.com/yourname/manusplit"
