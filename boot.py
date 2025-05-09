import os
import sys

# Force Qt to use macOS native styles
os.environ['QT_MAC_WANTS_LAYER'] = '1'
os.environ['QT_QPA_PLATFORM'] = 'cocoa'

# Path handling
if getattr(sys, 'frozen', False):
    # Running in a bundle
    bundle_dir = os.path.dirname(sys.executable)
    # Check if we're in the .app structure or running the raw executable
    if os.path.basename(os.path.dirname(bundle_dir)) == 'Contents':
        # We're in the .app bundle
        contents_dir = os.path.dirname(bundle_dir)
        resources_dir = os.path.join(contents_dir, 'Resources')
    else:
        # We're running the raw executable from dist/Manusplit/
        resources_dir = bundle_dir

    # Set resource path
    os.environ['MANUSPLIT_RESOURCES'] = resources_dir

    # Change to resources directory if it exists
    if os.path.exists(resources_dir):
        os.chdir(resources_dir)
else:
    # Running in development mode - just use current directory
    resources_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ['MANUSPLIT_RESOURCES'] = resources_dir

# Import and run main
import main