# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a basic Obsidian clone built with Python and PyQt5. It provides a simple note-taking interface with markdown file editing and wiki-style linking.

## Development Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the Application
```bash
python obsidian_clone.py
# or
./obsidian_clone.py
```

### Build macOS App Bundle
```bash
# Install py2app
pip install py2app

# Build the app
make app
# or
python setup.py py2app

# Install to Applications
make install
```

### Data Directory Location
By default, the application creates an `obclonedata` subdirectory in the current working directory. You can override this location using the `OBCLONEDATA` environment variable:

```bash
# Use a specific directory for data storage
export OBCLONEDATA=/home/user/Documents
python obsidian_clone.py

# Or set it inline
OBCLONEDATA=/path/to/data python obsidian_clone.py
```

When `OBCLONEDATA` is set, the application will create/use `obclonedata` as a subdirectory within the specified path.

## Architecture

The application consists of a single main file (`obsidian_clone.py`) that implements:

- **Main Window**: QMainWindow-based application with split-pane layout
- **File List Widget**: Left sidebar showing all `.md` files in the obclonedata directory
- **Markdown Editor**: Right-side QTextEdit for editing markdown content
- **Auto-save**: Timer-based auto-save every 5 seconds
- **Wiki-style Linking**: Pattern matching for `[[page]]` syntax that auto-creates new files

## Key Features

1. **File Management**: Automatically lists and updates `.md` files in the working directory
2. **Link Detection**: Uses regex pattern `\[\[([^\]]+)\]\]` to detect and create new pages
3. **Auto-save**: Saves current file every 5 seconds and on file switch/close
4. **Simple UI**: 30/70 split between file list and editor