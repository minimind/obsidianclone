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
python main.py
# or
./main.py
```

### Run Tests
```bash
# Run all unit tests
python -m unittest discover tests/unit -v

# Run specific test module
python -m unittest tests.unit.test_file_utils -v
python -m unittest tests.unit.test_link_utils -v
python -m unittest tests.unit.test_date_utils -v
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
By default, the application creates an `obclonedata` subdirectory in the current working directory with the following structure:
- `.trash/` - Deleted files (gray color in UI)
- `.journal/` - Daily journal entries (blue color in UI)  
- `.keys/` - Key-value storage and metadata (purple color in UI, recreated from template on startup)
- `home.md` - Default starting note

### Keys Template System
The `.keys` directory is automatically recreated from the `keys/` template directory on every application startup:
- Template location: `keys/` (in project root)
- Runtime location: `obclonedata/.keys/` (copied fresh each startup)
- Initial template includes: `comment/system.md` and `comment/assistant.md`

### AI Prompt Processing
The application supports AI-powered text processing using Ollama:
- Use `@#promptname` patterns in your text (e.g., `@#comment`)
- Available prompts are discovered from subdirectories in `keys/`
- Click "Process @# Prompts" button to send text to Ollama for analysis
- Requires Ollama to be installed and running locally
- Responses are inserted after the prompt pattern with clear formatting

You can override this location using the `OBCLONEDATA` environment variable:

```bash
# Use a specific directory for data storage
export OBCLONEDATA=/home/user/Documents
python main.py

# Or set it inline
OBCLONEDATA=/path/to/data python main.py
```

When `OBCLONEDATA` is set, the application will create/use `obclonedata` as a subdirectory within the specified path.

## Architecture

The application is now structured as a modular Python package with the following components:

### Directory Structure
```
src/
├── ui/
│   ├── main_window.py          # Main application window
│   └── widgets/
│       └── clickable_text_edit.py  # Custom text editor widget
├── services/
│   └── file_manager.py         # File operations service
├── utils/
│   ├── file_utils.py          # File and path utilities
│   ├── link_utils.py          # Wiki-style link processing
│   └── date_utils.py          # Date formatting utilities
└── models/                     # Data models (future expansion)

tests/
└── unit/                      # Unit tests for all modules
```

### Key Components

- **MainWindow** (`src/ui/main_window.py`): QMainWindow-based application with split-pane layout
- **ClickableTextEdit** (`src/ui/widgets/clickable_text_edit.py`): Custom text editor with link support and undo/redo
- **FileManager** (`src/services/file_manager.py`): Centralized file operations service
- **Utility Modules**: Modular functions for file operations, link processing, and date formatting

## Key Features

1. **File Management**: Automatically lists and updates `.md` files with hierarchical directory support
2. **Link Detection**: Uses regex pattern `\[\[([^\]]+)\]\]` to detect and create new pages
3. **Auto-save**: Saves current file every 5 seconds and on file switch/close
4. **Mode Toggle**: Switch between read-only and edit modes
5. **Journal Entries**: Daily journal creation with date-based organization
6. **Drag & Drop**: File organization within the tree structure
7. **Undo/Redo**: Full undo/redo support in edit mode
8. **AI Processing**: Ollama integration for processing text with `@#promptname` patterns