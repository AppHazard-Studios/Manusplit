from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    ('assets', ['assets/icon.png', 'assets/icon.icns']),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns',
    'plist': {
        'CFBundleName': 'Manusplit',
        'CFBundleDisplayName': 'Manusplit',
        'CFBundleIdentifier': 'com.apphazardstudios.manusplit',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
    'packages': ['PyQt6', 'docx'],
    'includes': [
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'PyQt6.sip',
    ],
    # Explicitly exclude troublesome modules
    'excludes': [
        'tkinter', 'matplotlib', 'PyQt5',
        'requests', 'urllib3', 'charset_normalizer'  # Exclude all HTTP-related modules
    ],
    'qt_plugins': ['imageformats', 'platforms'],
}

setup(
    name='Manusplit',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)