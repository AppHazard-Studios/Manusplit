"""
Helper functions for Manusplit application.
Provides common utility functions for validation, error handling, etc.
"""
import os
import logging
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Set up logging with rotation."""
    log_path = Path(os.path.dirname(os.path.abspath(__file__))) / "manusplit.log"
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create rotating file handler (1MB max, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger


def sanitize_filename(filename):
    """
    Clean up a filename to ensure it's valid on all platforms.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    
    # Trim whitespace and periods from the end (Windows issue)
    sanitized = sanitized.strip().rstrip(".")
    
    # If empty after sanitization, use a default name
    if not sanitized:
        sanitized = "untitled"
        
    return sanitized


def get_output_filename(original_path, part_num, output_folder, max_length=200):
    """
    Generate an output filename for a split document part.
    
    Args:
        original_path (str): Path to the original document
        part_num (int): Part number (1-based)
        output_folder (str): Destination folder
        max_length (int): Maximum filename length
        
    Returns:
        Path: Complete path to the output file
    """
    # Extract just the filename without path
    original_name = os.path.basename(original_path)
    
    # Get base name without extension
    base_name, extension = os.path.splitext(original_name)
    
    # Truncate if too long
    if len(base_name) > max_length - 15:  # Account for " - Part X" and extension
        base_name = base_name[:max_length - 15] + "..."
    
    # Create the new filename with part number
    new_filename = f"{base_name} - Part {part_num}{extension}"
    
    # Sanitize it
    new_filename = sanitize_filename(new_filename)
    
    # Join with output folder
    return Path(output_folder) / new_filename


def count_words(text):
    """
    Count words in a text.
    
    Args:
        text (str): Input text
        
    Returns:
        int: Word count
    """
    if not text:
        return 0
        
    # Simple whitespace-based splitting
    words = text.split()
    return len(words)


def format_word_count(count):
    """
    Format a word count with commas.
    
    Args:
        count (int): Word count
        
    Returns:
        str: Formatted word count
    """
    return f"{count:,}"


def check_file_access(filepath):
    """
    Check if a file can be accessed for reading.
    
    Args:
        filepath (str): Path to file
        
    Returns:
        tuple: (bool success, str error_message)
    """
    path = Path(filepath)
    
    if not path.exists():
        return False, "File not found"
        
    if not path.is_file():
        return False, "Not a file"
        
    try:
        # Try opening for reading
        with open(path, 'rb'):
            pass
        return True, ""
    except PermissionError:
        return False, "Permission denied"
    except IOError:
        return False, "I/O error (file may be locked)"
