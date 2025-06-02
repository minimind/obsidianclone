"""
Setup.py for building macOS app bundle using py2app
"""
from setuptools import setup

APP = ['obsidian_clone.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'Obsidian Clone',
        'CFBundleDisplayName': 'Obsidian Clone',
        'CFBundleGetInfoString': "A simple Obsidian-like note-taking app",
        'CFBundleIdentifier': "com.example.obsidianclone",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': u"Copyright © 2025",
        'NSRequiresAquaSystemAppearance': False,
        'LSUIElement': False,
    },
    'packages': ['PyQt5'],
    'includes': ['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    'excludes': ['matplotlib', 'numpy', 'scipy'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)