"""
Build script for Manusplit.
Creates executable for the current platform.
"""
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def build_executable(version, platform=None, sign=False, package=False):
    """
    Build an executable for the specified platform.
    
    Args:
        version (str): Version string
        platform (str): Target platform (win/mac/linux or None for current)
        sign (bool): Whether to sign the executable
        package (bool): Whether to create distribution package
    """
    print(f"Building Manusplit v{version}")
    
    # Determine platform if not specified
    if platform is None:
        if sys.platform.startswith('win'):
            platform = 'win'
        elif sys.platform.startswith('darwin'):
            platform = 'mac'
        else:
            platform = 'linux'
    
    print(f"Target platform: {platform}")
    
    # Clean previous builds
    dist_dir = Path('dist')
    build_dir = Path('build')
    
    if dist_dir.exists():
        print("Cleaning dist directory...")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print("Cleaning build directory...")
        shutil.rmtree(build_dir)
    
    # Update version
    with open('version.py', 'r') as f:
        content = f.read()
    
    content = content.replace('VERSION = "1.0.0"', f'VERSION = "{version}"')
    
    with open('version.py', 'w') as f:
        f.write(content)
    
    # Build with PyInstaller
    print("Building with PyInstaller...")
    
    icon_path = Path('assets/icon.ico') if platform == 'win' else Path('assets/icon.icns')
    
    cmd = [
        'pyinstaller',
        '--clean',
        '--windowed',
        '--onefile',
        f'--name=Manusplit-{version}',
    ]
    
    if icon_path.exists():
        cmd.append(f'--icon={icon_path}')
    
    cmd.append('main.py')
    
    subprocess.run(cmd, check=True)
    
    # Platform-specific post-processing
    if platform == 'mac' and sign:
        print("Signing macOS application...")
        app_path = f'dist/Manusplit-{version}.app'
        
        # Check for credentials
        if 'APPLE_DEVELOPER_ID' in os.environ:
            developer_id = os.environ['APPLE_DEVELOPER_ID']
            
            # Sign the app
            subprocess.run([
                'codesign',
                '--force',
                '--sign',
                f"Developer ID Application: {developer_id}",
                '--deep',
                app_path
            ], check=True)
            
            # Create DMG if packaging
            if package:
                print("Creating DMG...")
                subprocess.run([
                    'hdiutil',
                    'create',
                    f'dist/Manusplit-{version}.dmg',
                    '-srcfolder',
                    app_path,
                    '-ov'
                ], check=True)
        else:
            print("Warning: APPLE_DEVELOPER_ID not set, skipping signing")
    
    elif platform == 'win' and sign:
        print("Signing Windows executable...")
        exe_path = f'dist/Manusplit-{version}.exe'
        
        # Check for credentials
        if 'WIN_CERT_PATH' in os.environ and 'WIN_CERT_PASSWORD' in os.environ:
            cert_path = os.environ['WIN_CERT_PATH']
            cert_password = os.environ['WIN_CERT_PASSWORD']
            
            # Sign the exe
            subprocess.run([
                'signtool',
                'sign',
                '/f',
                cert_path,
                '/p',
                cert_password,
                '/t',
                'http://timestamp.digicert.com',
                exe_path
            ], check=True)
            
            # Create installer if packaging
            if package:
                print("Creating installer (requires Inno Setup)...")
                # This would require an Inno Setup script, simplified here
                pass
        else:
            print("Warning: WIN_CERT_PATH or WIN_CERT_PASSWORD not set, skipping signing")
    
    elif platform == 'linux' and package:
        print("Creating AppImage...")
        # This would require AppImage tools, simplified here
        pass
    
    print("Build completed successfully!")
    print(f"Output in dist/ directory")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Manusplit executable")
    parser.add_argument("--version", default="1.0.0", help="Version number")
    parser.add_argument("--platform", choices=["win", "mac", "linux"], help="Target platform")
    parser.add_argument("--sign", action="store_true", help="Sign the executable")
    parser.add_argument("--package", action="store_true", help="Create distribution package")
    
    args = parser.parse_args()
    
    build_executable(args.version, args.platform, args.sign, args.package)
