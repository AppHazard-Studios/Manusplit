"""
Version information for Manusplit.
"""

# Current version
VERSION = "1.0.0"
BUILD_DATE = "2025-05-09"

def get_version():
    """Get current version string."""
    return VERSION

def get_build_date():
    """Get build date string."""
    return BUILD_DATE

# Remove dependency on requests completely
def check_for_updates(force=False, timeout=5):
    """Simplified dummy function - always returns no update available."""
    return False, VERSION, VERSION

def get_github_url():
    """Get GitHub URL for the project."""
    return "https://github.com/AppHazard-Studios/Manusplit"