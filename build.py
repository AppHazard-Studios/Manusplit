"""Enhanced script to build Manusplit for macOS"""
import os
import sys
import subprocess
from pathlib import Path
import shutil

# Clean previous builds
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# Get platform
if sys.platform.startswith('win'):
    platform = 'windows'
    icon = 'assets/icon.ico'
elif sys.platform.startswith('darwin'):
    platform = 'macos'
    icon = 'assets/icon2.icns'
else:
    platform = 'linux'
    icon = 'assets/icon.png'

print(f"Building for {platform} using icon {icon}")

# Basic command with additional options for reliability
cmd = [
    'pyinstaller',
    '--clean',
    '--windowed',
    '--name=Manusplit',
]

# For macOS, prefer --onedir for better app bundle structure
if platform == 'macos':
    cmd.append('--onedir')
else:
    cmd.append('--onefile')

# Add data files - be more specific about paths
cmd.append('--add-data=assets:assets')

# Add hidden imports that PyInstaller might miss
cmd.extend([
    '--hidden-import=PyQt6.QtCore',
    '--hidden-import=PyQt6.QtGui',
    '--hidden-import=PyQt6.QtWidgets',
    '--hidden-import=PyQt6.QtSvg',
])

# Add icon if it exists
if os.path.exists(icon):
    cmd.append(f'--icon={icon}')
else:
    print(f"Warning: Icon {icon} not found - app will use default icon")

# Add main script
cmd.append('main.py')

# Run the command with error checking
print("Running PyInstaller...")
print(f"Command: {' '.join(cmd)}")
try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(result.stdout)

    # Special handling for macOS
    if platform == 'macos':
        print("Finalizing macOS app bundle...")
        # Copy any additional files needed for macOS
        app_path = Path('dist/Manusplit.app')
        if app_path.exists():
            # Add macOS-specific tweaks here if needed
            pass

    print("Done! Check the 'dist' folder for your executable.")
except subprocess.CalledProcessError as e:
    print(f"Error building application: {e}")
    print(f"PyInstaller output:\n{e.stdout}\n{e.stderr}")
    sys.exit(1)