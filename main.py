#!/usr/bin/env python3
"""
Obsidian Clone - A simple note-taking application with wiki-style linking.

This is the main entry point for the application. It performs system checks
and launches the PyQt5-based GUI application.
"""

import sys
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def check_python_version():
    """
    Check if the Python version meets minimum requirements.
    
    Requires Python 3.9 or higher for full compatibility.
    """
    if sys.version_info < (3, 9):
        print(f"Error: Python 3.9 or higher is required. "
              f"You are using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        sys.exit(1)


def main():
    """
    Main entry point for the application.
    
    Performs system checks, creates the Qt application instance,
    and shows the main window.
    """
    # Check Python version
    check_python_version()
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Obsidian Clone")
    app.setOrganizationName("ObsidianClone")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()