# Obsidian Clone

A simple Obsidian-like note-taking application built with Python and PyQt5.

## Features

- Split-pane interface with file list on the left and markdown editor on the right
- Automatic file creation when typing `[[page]]` syntax
- Auto-save every 5 seconds
- Save on file switch or application close
- Lists all `.md` files in the data directory
- Read-only mode by default with toggle to edit mode
- Daily journal entries with automatic date-based organization
- Configurable data directory location via environment variable

## Requirements

- Python 3.9 or higher (tested with 3.9 and 3.12)
- PyQt5

## Installation

### Option 1: Run from Source

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

### Option 2: Windows Installer

#### Pre-built Installer
1. Download the latest `ObsidianClone-Setup-*.exe` from the releases page
2. Run the installer and follow the prompts
3. Launch ObsidianClone from the Start Menu or Desktop shortcut

#### Build Your Own Windows Executable

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Build the executable:
```bash
python setup_windows.py
# or use PyInstaller directly:
pyinstaller obsidianclone.spec
```

3. The executable will be in the `dist` folder as `ObsidianClone.exe`

#### Create Windows Installer (Optional)

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Open `installer_windows.iss` in Inno Setup
3. Compile the script (Build → Compile)
4. The installer will be created in the `dist` folder

### Option 3: macOS App Bundle

See the "Building macOS App (for Dock)" section below for macOS installation instructions.

## Usage

- Click on any `.md` file in the left sidebar to open it
- Click "Edit" button to switch from read-only to edit mode
- Type in the editor on the right (when in edit mode)
- Create new pages by typing `[[pagename]]` - this will automatically create `pagename.md`
- Click "Today" button to create/open today's journal entry
- Files are automatically saved every 5 seconds
- Files are also saved when switching to another file or closing the application

## Data Directory

By default, all notes are stored in an `obclonedata` subdirectory in the current working directory. You can change this location using the `OBCLONEDATA` environment variable:

```bash
# Use default location (./obclonedata)
python obsidian_clone.py

# Use custom location
export OBCLONEDATA=/home/user/Documents
python obsidian_clone.py

# Or set it inline
OBCLONEDATA=/path/to/notes python obsidian_clone.py
```

## Building macOS App (for Dock)

To create a proper macOS application that can be added to the Dock and receives all events correctly:

1. Install py2app:
```bash
pip install py2app
```

2. Build the app bundle:
```bash
make app
# or
python setup.py py2app
```

3. The app will be created in `dist/Obsidian Clone.app`

4. To install to your Applications folder:
   - Drag `dist/Obsidian Clone.app` to your Applications folder
   - Or run: `make install` (requires admin password)

5. To add to Dock:
   - Open Applications folder
   - Drag "Obsidian Clone" to your Dock
   - Now clicking the Dock icon will launch the app directly and all events will work properly

### Setting Custom Data Directory for macOS App

There are three ways to set a custom `OBCLONEDATA` directory for the Dock app:

#### Method 1: Default Location (Built into App)
The app is pre-configured to use `~/Documents/ObsidianClone` as the default location. Just build and install the app normally.

#### Method 2: Create Custom Launcher
Create a custom app with a specific data directory:
```bash
./create_custom_launcher.sh /path/to/your/notes
# Example: ./create_custom_launcher.sh ~/Dropbox/Notes
```
This creates a new app that will always use your specified directory.

#### Method 3: Edit After Installation
Edit the installed app's configuration:
```bash
# After installing to /Applications
/usr/libexec/PlistBuddy -c "Set :LSEnvironment:OBCLONEDATA '/your/custom/path'" "/Applications/Obsidian Clone.app/Contents/Info.plist"
```

### Alternative: Command Line Alias

If you prefer not to build an app bundle, you can create an alias:

```bash
# Add to your ~/.zshrc or ~/.bash_profile
alias obsidian-clone='python /path/to/obsidian_clone.py'
```

## User notes

You can call ollama like this:

```
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.1:8b",
  "messages": [
{"role": "system","content": "You are an agent that accepts user text and thinks about it, and makes a positive spin on anything sent to it. You evaluate the text for sentiment and truthfulness. Make a list of the elements that you think are not truth or of a negative sentiment. Then make a list of the opposite - where things are false, you correct them, and where something is negative, you turn it around and give it a positive attitude. Summarize what you want to say, and send back to the user as comments. Be sure to point out false or wrong items, and correct the user. After thinking, analysing, and planning what you want to say, surround the comments with the tag strings <AdviceNowABC> ... </AdviceNowABC>."},
{"role": "user", "content": "I am feeling so miserable today. I have got nothing to look forward to. England, which is currently in Africa, is covered in sand like the desert."}
]}'
```