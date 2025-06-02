#!/bin/bash

# Script to create a custom launcher app with specific OBCLONEDATA path

if [ $# -eq 0 ]; then
    echo "Usage: ./create_custom_launcher.sh /path/to/your/notes"
    echo "Example: ./create_custom_launcher.sh ~/Documents/MyNotes"
    exit 1
fi

NOTES_PATH="$1"
APP_NAME="Obsidian Clone - Custom"

# First build the standard app if it doesn't exist
if [ ! -d "dist/Obsidian Clone.app" ]; then
    echo "Building base app first..."
    ./build_mac_app.sh
fi

# Copy the app to a new custom version
echo "Creating custom launcher..."
cp -R "dist/Obsidian Clone.app" "dist/$APP_NAME.app"

# Update the Info.plist with custom environment variable
/usr/libexec/PlistBuddy -c "Delete :LSEnvironment" "dist/$APP_NAME.app/Contents/Info.plist" 2>/dev/null
/usr/libexec/PlistBuddy -c "Add :LSEnvironment dict" "dist/$APP_NAME.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :LSEnvironment:OBCLONEDATA string '$NOTES_PATH'" "dist/$APP_NAME.app/Contents/Info.plist"

# Update the display name
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName '$APP_NAME'" "dist/$APP_NAME.app/Contents/Info.plist"

echo "Custom launcher created: dist/$APP_NAME.app"
echo ""
echo "This app will use notes directory: $NOTES_PATH/obclonedata"
echo ""
echo "To install:"
echo "1. Drag 'dist/$APP_NAME.app' to your Applications folder"
echo "2. Then drag from Applications to your Dock"