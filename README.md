# Obsidian Clone

A simple Obsidian-like note-taking application built with Python and PyQt5.

## Features

- Split-pane interface with file list on the left and markdown editor on the right
- Automatic file creation when typing `[[page]]` syntax
- Auto-save every 5 seconds
- Save on file switch or application close
- Lists all `.md` files in the current directory

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
- Type in the editor on the right
- Create new pages by typing `[[pagename]]` - this will automatically create `pagename.md`
- Files are automatically saved every 5 seconds
- Files are also saved when switching to another file or closing the application