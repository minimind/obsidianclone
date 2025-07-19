"""
Windows build configuration for ObsidianClone using PyInstaller
"""
import PyInstaller.__main__
import os
import sys

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the main script path
main_script = os.path.join(script_dir, 'main.py')

# Define the icon path (we'll create this next)
icon_path = os.path.join(script_dir, 'resources', 'obsidianclone.ico')

# PyInstaller arguments
args = [
    main_script,
    '--name=ObsidianClone',
    '--windowed',  # No console window
    '--onefile',   # Single executable
    f'--icon={icon_path}' if os.path.exists(icon_path) else '',
    '--add-data=keys:keys',  # Include the keys template directory
    '--hidden-import=PyQt5',
    '--hidden-import=PyQt5.QtCore',
    '--hidden-import=PyQt5.QtGui',
    '--hidden-import=PyQt5.QtWidgets',
    '--clean',
]

# Remove empty icon argument if icon doesn't exist
args = [arg for arg in args if arg]

print("Building ObsidianClone for Windows...")
print(f"Arguments: {args}")

# Run PyInstaller
PyInstaller.__main__.run(args)

print("\nBuild complete! Executable is in the 'dist' folder.")