"""
Main window for the Obsidian Clone application.

This module implements the main application window with a split-pane interface
containing a file tree sidebar and a markdown editor.
"""

import os
import sys
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem, 
    QTreeWidgetItemIterator, QVBoxLayout, QWidget, QPushButton, 
    QMenu, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

from .widgets.clickable_text_edit import ClickableTextEdit
from ..services.file_manager import FileManager
from ..utils.file_utils import sanitize_filename, expand_user_path
from ..utils.link_utils import (
    find_all_links, link_to_filepath, create_wiki_link,
    remove_link_brackets, LINK_PATTERN
)


class MainWindow(QMainWindow):
    """
    Main application window for the Obsidian Clone.
    
    This window provides:
    - File tree navigation in the left sidebar
    - Markdown editor on the right
    - Mode toggle between read-only and edit modes
    - Auto-save functionality
    - Journal entries
    - File management operations
    
    Attributes:
        file_manager: Service for file operations
        current_file: Path to the currently open file
        original_content: Original content of the file (for mode switching)
        is_read_only: Current editor mode (read-only vs edit)
        auto_save_timer: Timer for periodic auto-saves
        file_tree: Tree widget showing file structure
        editor: Text editor widget
        mode_button: Button to toggle between modes
        today_button: Button to open today's journal entry
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Setup file manager
        base_dir = os.environ.get('OBCLONEDATA', os.getcwd())
        base_dir = expand_user_path(base_dir)
        notes_dir = os.path.join(base_dir, "obclonedata")
        self.file_manager = FileManager(notes_dir)
        
        # Initialize state
        self.current_file = None
        self.original_content = ""
        self.is_read_only = True  # Start in read-only mode
        
        # Setup auto-save
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(5000)  # 5 seconds
        
        # Setup UI
        self.init_ui()
        self.load_files()
        self.open_default_file()
    
    def event(self, event: QEvent) -> bool:
        """
        Override event handler to catch macOS dock icon clicks.
        
        Args:
            event: The event to handle
            
        Returns:
            True if event was handled
        """
        if sys.platform == 'darwin' and event.type() == QEvent.ApplicationActivate:
            # Force window to front on macOS
            self.show()
            self.raise_()
            self.activateWindow()
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        return super().event(event)
    
    def init_ui(self) -> None:
        """Initialize the user interface components."""
        self.setWindowTitle("Obsidian Clone")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create splitter for two-pane layout
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - File tree and buttons
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # File tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Files")
        self.file_tree.itemClicked.connect(self.on_file_selected)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.file_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.file_tree.setDefaultDropAction(Qt.MoveAction)
        self.file_tree.dropEvent = self.tree_drop_event
        left_layout.addWidget(self.file_tree)
        
        # Mode toggle button
        self.mode_button = QPushButton("Edit")
        self.mode_button.clicked.connect(self.toggle_mode)
        left_layout.addWidget(self.mode_button)
        
        # Today button
        self.today_button = QPushButton("Today")
        self.today_button.clicked.connect(self.open_today_journal)
        left_layout.addWidget(self.today_button)
        
        splitter.addWidget(left_widget)
        
        # Right side - Markdown editor
        self.editor = ClickableTextEdit(self)
        self.editor.setFont(QFont("Consolas", 14))
        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.setReadOnly(True)  # Start in read-only mode
        splitter.addWidget(self.editor)
        
        # Set splitter sizes (30% for file list, 70% for editor)
        splitter.setSizes([360, 840])
    
    def load_files(self) -> None:
        """Load all files and directories into the file tree."""
        self.file_tree.clear()
        
        # Get all notes from file manager
        notes = self.file_manager.get_all_notes()
        
        # Build tree structure
        item_map = {}  # Map paths to tree items
        
        for note in notes:
            parent_path = note['parent']
            
            # Find parent item
            if parent_path in item_map:
                parent_item = item_map[parent_path]
            elif parent_path == self.file_manager.notes_dir:
                parent_item = self.file_tree.invisibleRootItem()
            else:
                continue  # Skip if parent not found
            
            # Create tree item
            display_name = note['name']
            if note['type'] == 'file':
                display_name = note['name']  # Already has .md removed
            
            tree_item = QTreeWidgetItem(parent_item, [display_name])
            tree_item.setData(0, Qt.UserRole, note['path'])
            tree_item.setData(0, Qt.UserRole + 1, note['type'])
            
            # Apply styling based on type
            if note['type'] == 'directory':
                font = tree_item.font(0)
                font.setItalic(True)
                tree_item.setFont(0, font)
            elif note['type'] == 'trash':
                tree_item.setForeground(0, QColor(150, 150, 150))
                font = tree_item.font(0)
                font.setItalic(True)
                tree_item.setFont(0, font)
            elif note['type'] == 'journal':
                tree_item.setForeground(0, QColor(0, 100, 200))
                font = tree_item.font(0)
                font.setItalic(True)
                tree_item.setFont(0, font)
            
            # Add to map for building hierarchy
            if note['type'] in ['directory', 'trash', 'journal']:
                item_map[note['path']] = tree_item
    
    def open_default_file(self) -> None:
        """Open the default home.md file."""
        home_file = os.path.join(self.file_manager.notes_dir, "home.md")
        
        # Find and select home.md in the tree
        iterator = QTreeWidgetItemIterator(self.file_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole) == home_file:
                self.file_tree.setCurrentItem(item)
                self.on_file_selected(item, 0)
                break
            iterator += 1
    
    def open_today_journal(self) -> None:
        """Open or create today's journal entry."""
        # Save current file first
        self.save_current_file()
        
        # Create journal entry
        journal_file = self.file_manager.create_journal_entry()
        
        # Reload files to show new journal entry
        self.load_files()
        
        # Find and select the journal file in the tree
        iterator = QTreeWidgetItemIterator(self.file_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole) == journal_file:
                # Expand parent nodes to make the file visible
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                
                self.file_tree.setCurrentItem(item)
                self.on_file_selected(item, 0)
                break
            iterator += 1
    
    def show_context_menu(self, position) -> None:
        """
        Show context menu for file operations.
        
        Args:
            position: Position where the menu should appear
        """
        menu = QMenu()
        create_dir_action = menu.addAction("Create Subdirectory")
        
        # Add rename and delete actions if an item is selected
        current_item = self.file_tree.currentItem()
        rename_action = None
        delete_action = None
        
        if current_item:
            item_type = current_item.data(0, Qt.UserRole + 1)
            if item_type in ["file", "directory"]:
                menu.addSeparator()
                rename_action = menu.addAction("Rename")
                delete_action = menu.addAction("Delete")
        
        action = menu.exec_(self.file_tree.mapToGlobal(position))
        
        if action == create_dir_action:
            self.create_subdirectory()
        elif action == rename_action:
            self.rename_item()
        elif action == delete_action:
            self.delete_item()
    
    def create_subdirectory(self) -> None:
        """Create a new subdirectory in the file tree."""
        current_item = self.file_tree.currentItem()
        
        # Determine parent directory
        if current_item:
            item_type = current_item.data(0, Qt.UserRole + 1)
            if item_type in ["directory", "trash", "journal"]:
                parent_path = current_item.data(0, Qt.UserRole)
                parent_item = current_item
            else:
                # If a file is selected, use its parent directory
                parent_item = current_item.parent() or self.file_tree.invisibleRootItem()
                if parent_item == self.file_tree.invisibleRootItem():
                    parent_path = self.file_manager.notes_dir
                else:
                    parent_path = parent_item.data(0, Qt.UserRole)
        else:
            parent_path = self.file_manager.notes_dir
            parent_item = self.file_tree.invisibleRootItem()
        
        # Get directory name from user
        name, ok = QInputDialog.getText(self, "Create Subdirectory", "Directory name:")
        if ok and name:
            sanitized_name = sanitize_filename(name)
            new_dir_path = os.path.join(parent_path, sanitized_name)
            
            try:
                os.makedirs(new_dir_path, exist_ok=True)
                self.load_files()
                # Expand the parent item
                if parent_item != self.file_tree.invisibleRootItem():
                    parent_item.setExpanded(True)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create directory: {str(e)}")
    
    def delete_item(self) -> None:
        """Delete the selected file or directory."""
        current_item = self.file_tree.currentItem()
        if not current_item:
            return
        
        item_type = current_item.data(0, Qt.UserRole + 1)
        item_path = current_item.data(0, Qt.UserRole)
        
        # Don't allow deleting special directories
        if self.file_manager.is_special_directory(item_path):
            QMessageBox.warning(self, "Cannot Delete", 
                              f"The {os.path.basename(item_path)} directory cannot be deleted.")
            return
        
        if item_type == "file":
            # Move file to trash
            if self.file_manager.delete_note(item_path):
                # If this was the current file, clear the editor
                if item_path == self.current_file:
                    self.current_file = None
                    self.editor.clear()
                    self.original_content = ""
                self.load_files()
            else:
                QMessageBox.warning(self, "Error", "Could not move file to trash.")
                
        elif item_type == "directory":
            # Try to delete directory
            if self.file_manager.delete_directory(item_path):
                self.load_files()
            else:
                QMessageBox.warning(self, "Cannot Delete", "Directory is not empty.")
    
    def rename_item(self) -> None:
        """Rename the selected file or directory."""
        current_item = self.file_tree.currentItem()
        if not current_item:
            return
        
        item_type = current_item.data(0, Qt.UserRole + 1)
        item_path = current_item.data(0, Qt.UserRole)
        old_name = os.path.basename(item_path)
        
        # Don't allow renaming special directories
        if self.file_manager.is_special_directory(item_path):
            QMessageBox.warning(self, "Cannot Rename", 
                              f"The {old_name} directory cannot be renamed.")
            return
        
        # Get new name from user
        if item_type == "file":
            # For files, show name without .md extension
            display_name = old_name[:-3] if old_name.endswith('.md') else old_name
            new_name, ok = QInputDialog.getText(self, "Rename File", 
                                               "New name:", text=display_name)
            if ok and new_name:
                success, new_path = self.file_manager.rename_note(item_path, new_name)
                if success:
                    # Update links
                    self.file_manager.update_all_links(item_path, new_path)
                    # Update current file path if needed
                    if item_path == self.current_file:
                        self.current_file = new_path
                    self.load_files()
                else:
                    QMessageBox.warning(self, "Cannot Rename", 
                                      "A file with that name already exists.")
        else:
            # For directories
            new_name, ok = QInputDialog.getText(self, "Rename Directory", 
                                               "New name:", text=old_name)
            if ok and new_name:
                success, new_path = self.file_manager.rename_directory(item_path, new_name)
                if success:
                    self.load_files()
                else:
                    QMessageBox.warning(self, "Cannot Rename", 
                                      "A directory with that name already exists.")
    
    def tree_drop_event(self, event) -> None:
        """
        Handle file drops in the tree for moving files.
        
        Args:
            event: The drop event
        """
        # Get the item being dragged
        dragged_item = self.file_tree.currentItem()
        if not dragged_item or dragged_item.data(0, Qt.UserRole + 1) != "file":
            event.ignore()
            return
        
        # Get drop target
        target_item = self.file_tree.itemAt(event.pos())
        
        # Determine target directory
        if target_item:
            item_type = target_item.data(0, Qt.UserRole + 1)
            
            # Don't allow drops on special directories
            if item_type in ["trash", "journal"]:
                event.ignore()
                return
                
            if item_type in ["directory", "trash", "journal"]:
                target_dir = target_item.data(0, Qt.UserRole)
            else:
                # Dropped on a file, use its parent directory
                parent = target_item.parent()
                if parent:
                    target_dir = parent.data(0, Qt.UserRole)
                else:
                    target_dir = self.file_manager.notes_dir
        else:
            target_dir = self.file_manager.notes_dir
        
        # Get source file info
        source_path = dragged_item.data(0, Qt.UserRole)
        
        # Move the file
        success, new_path = self.file_manager.move_note(source_path, target_dir)
        if success:
            # Update links
            self.file_manager.update_all_links(source_path, new_path)
            
            # Update current file path if needed
            if self.current_file == source_path:
                self.current_file = new_path
            
            self.load_files()
            event.accept()
        else:
            event.ignore()
    
    def toggle_mode(self) -> None:
        """Toggle between edit and read-only mode."""
        self.is_read_only = not self.is_read_only
        
        if self.is_read_only:
            # Save current content before switching to read-only
            self.original_content = self.editor.toPlainText()
            self.mode_button.setText("Edit")
            self.editor.setReadOnly(True)
            # Apply read-only formatting
            self.format_for_read_only()
        else:
            self.mode_button.setText("Read Only")
            self.editor.setReadOnly(False)
            # Restore original content
            self.editor.setPlainText(self.original_content)
            # Restore edit mode formatting
            self.format_links()
    
    def on_file_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Handle file selection from the tree.
        
        Args:
            item: Selected tree item
            column: Column clicked
        """
        # Only process files, not directories
        if item.data(0, Qt.UserRole + 1) != "file":
            return
            
        # Don't allow editing files in trash
        file_path = item.data(0, Qt.UserRole)
        if self.file_manager.is_in_trash(file_path):
            return
            
        # Save current file before switching
        if self.current_file:
            self.save_current_file()
            
        # Load selected file
        self.current_file = file_path
        content = self.file_manager.read_note(file_path)
        self.original_content = content
        
        # Clear undo history before setting new content
        self.editor.clear_undo_history()
        self.editor.setPlainText(content)
        
        if self.is_read_only:
            self.format_for_read_only()
        else:
            self.format_links()
    
    def on_text_changed(self) -> None:
        """Handle text changes in the editor."""
        if not self.current_file or self.is_read_only:
            return
            
        # Update stored original content in edit mode
        self.original_content = self.editor.toPlainText()
        
        # Save undo state after text changes
        if not self.editor.is_undoing:
            self.editor.save_undo_state()
        
        # Apply link formatting
        self.format_links()
    
    def format_links(self) -> None:
        """Apply visual formatting to [[page]] links in edit mode."""
        # Temporarily disconnect the textChanged signal to avoid recursion
        self.editor.textChanged.disconnect()
        
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        
        # Save cursor position
        saved_position = cursor.position()
        
        # Reset formatting
        cursor.select(QTextCursor.Document)
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        
        # Find and format all links
        text = self.editor.toPlainText()
        links = find_all_links(text)
        
        for start, end, link_text in links:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            
            # Apply link formatting
            link_format = QTextCharFormat()
            link_format.setForeground(QColor(0, 0, 255))  # Blue color
            link_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            cursor.setCharFormat(link_format)
        
        cursor.endEditBlock()
        
        # Restore cursor position
        cursor.setPosition(saved_position)
        self.editor.setTextCursor(cursor)
        
        # Reconnect the signal
        self.editor.textChanged.connect(self.on_text_changed)
    
    def format_for_read_only(self) -> None:
        """Format text for read-only mode - hide [[ ]] brackets."""
        # Temporarily disconnect the textChanged signal
        self.editor.textChanged.disconnect()
        
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        
        # Get the full text and remove brackets
        text = self.editor.toPlainText()
        display_text, link_positions = remove_link_brackets(text)
        
        # Clear and set new text
        cursor.select(QTextCursor.Document)
        cursor.removeSelectedText()
        cursor.insertText(display_text)
        
        # Apply link formatting
        for link_info in link_positions:
            cursor.setPosition(link_info['start'])
            cursor.setPosition(link_info['end'], QTextCursor.KeepAnchor)
            
            link_format = QTextCharFormat()
            link_format.setForeground(QColor(0, 0, 255))
            link_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            cursor.setCharFormat(link_format)
        
        cursor.endEditBlock()
        
        # Reconnect the signal
        self.editor.textChanged.connect(self.on_text_changed)
    
    def handle_link_click(self, link_text: str) -> None:
        """
        Handle clicks on wiki-style links.
        
        Creates the file if it doesn't exist and navigates to it.
        
        Args:
            link_text: Text inside the [[...]] link
        """
        # Save current file first
        self.save_current_file()
        
        # Create file if it doesn't exist
        file_path = link_to_filepath(link_text, self.file_manager.notes_dir, sanitize_filename)
        if not os.path.exists(file_path):
            self.file_manager.create_note_from_link(link_text)
            self.load_files()
        
        # Find and open the file in the tree
        iterator = QTreeWidgetItemIterator(self.file_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole) == file_path:
                self.file_tree.setCurrentItem(item)
                self.on_file_selected(item, 0)
                break
            iterator += 1
    
    def save_current_file(self) -> None:
        """Save the current file."""
        if self.current_file:
            # Use original content if in read-only mode
            if self.is_read_only:
                content = self.original_content
            else:
                content = self.editor.toPlainText()
                self.original_content = content  # Update stored content
            
            self.file_manager.save_note(self.current_file, content)
    
    def auto_save(self) -> None:
        """Auto-save the current file."""
        self.save_current_file()
    
    def closeEvent(self, event) -> None:
        """
        Save before closing the application.
        
        Args:
            event: Close event
        """
        self.save_current_file()
        event.accept()