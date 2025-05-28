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

## Architecture

The application consists of a single main file (`obsidian_clone.py`) that implements:

- **Main Window**: QMainWindow-based application with split-pane layout
- **File List Widget**: Left sidebar showing all `.md` files in the current directory
- **Markdown Editor**: Right-side QTextEdit for editing markdown content
- **Auto-save**: Timer-based auto-save every 5 seconds
- **Wiki-style Linking**: Pattern matching for `[[page]]` syntax that auto-creates new files

## Key Features

1. **File Management**: Automatically lists and updates `.md` files in the working directory
2. **Link Detection**: Uses regex pattern `\[\[([^\]]+)\]\]` to detect and create new pages
3. **Auto-save**: Saves current file every 5 seconds and on file switch/close
4. **Simple UI**: 30/70 split between file list and editor