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

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python obsidian_clone.py
```

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