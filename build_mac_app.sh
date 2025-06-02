#!/bin/bash

echo "Cleaning up previous builds..."
rm -rf build dist *.egg-info
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
find . -name ".DS_Store" -delete

echo "Creating clean virtual environment..."
python3 -m venv venv_build
source venv_build/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install PyQt5
pip install py2app

echo "Building app..."
python setup.py py2app --force

echo "Cleaning up virtual environment..."
deactivate
rm -rf venv_build

if [ -d "dist/Obsidian Clone.app" ]; then
    echo "Build successful!"
    echo "App location: dist/Obsidian Clone.app"
    echo ""
    echo "To install:"
    echo "1. Drag 'dist/Obsidian Clone.app' to your Applications folder"
    echo "2. Then drag from Applications to your Dock"
else
    echo "Build failed!"
fi