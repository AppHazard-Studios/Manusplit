"""Simple script to build Manusplit for your current platform"""
import os
import sys
import subprocess
from pathlib import Path

# Get platform
if sys.platform.startswith('win'):
    platform = 'windows'
    icon = 'assets/icon.ico'
elif sys.platform.startswith('darwin'):
    platform = 'macos'
    icon = 'assets/icon.icns'
else:
    platform = 'linux'
    icon = 'assets/icon.png'

print(f"Building for {platform} using icon {icon}")

# Basic command (customize as needed)
cmd = [
    'pyinstaller',
    '--clean',
    '--windowed',
    '--onefile',
    '--name=Manusplit',
    f'--add-data=assets/*:assets'
]

# Add icon if it exists
if os.path.exists(icon):
    cmd.append(f'--icon={icon}')
else:
    print(f"Warning: Icon {icon} not found - app will use default icon")

# Add main script
cmd.append('main.py')

# Run the command
print("Running PyInstaller...")
subprocess.run(cmd)

print("Done! Check the 'dist' folder for your executable.")