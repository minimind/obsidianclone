#!/usr/bin/env python3
import sys

# Check Python version compatibility
if sys.version_info < (3, 9):
    print(f"Error: Python 3.9 or higher is required. You are using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    sys.exit(1)

import os
import re
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, 
                             QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
                             QTextEdit, QVBoxLayout, QWidget, QPushButton, QMenu, 
                             QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QUrl, QMimeData, QEvent
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QDrag


class ClickableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setMouseTracking(True)
        self.viewport().setCursor(Qt.IBeamCursor)
        self.anchor_at_cursor = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            
            # In read-only mode, we need to check against the original text
            if self.parent_window and self.parent_window.is_read_only:
                # Map the position in the displayed text back to the original text
                original_text = self.parent_window.original_content
                displayed_text = self.toPlainText()
                
                # Find all [[page]] patterns in the original text
                pattern = r'\[\[([^\]]+)\]\]'
                offset = 0
                
                for match in re.finditer(pattern, original_text):
                    link_text = match.group(1)
                    # Calculate where this link appears in the displayed text
                    # Account for removed brackets (4 chars: [[ and ]])
                    display_start = match.start() - offset
                    display_end = display_start + len(link_text)
                    
                    if display_start <= position <= display_end:
                        self.handle_link_click(link_text)
                        return
                    
                    # Update offset for next iteration
                    offset += 4  # Account for removed [[ and ]]
            else:
                # Normal edit mode - look for [[page]] patterns
                text = self.toPlainText()
                pattern = r'\[\[([^\]]+)\]\]'
                for match in re.finditer(pattern, text):
                    if match.start() <= position <= match.end():
                        link_text = match.group(1)
                        self.handle_link_click(link_text)
                        return
        
        super().mousePressEvent(event)
    
    def handle_link_click(self, link_text):
        if self.parent_window:
            # Check if link contains subdirectory path
            if '/' in link_text:
                # Handle subdirectory path
                parts = link_text.split('/')
                # Sanitize each part
                sanitized_parts = [self.parent_window.sanitize_filename(part) for part in parts]
                # Add .md to the last part
                sanitized_parts[-1] = f"{sanitized_parts[-1]}.md"
                file_path = os.path.join(self.parent_window.notes_dir, *sanitized_parts)
            else:
                # Simple filename in root
                sanitized_name = self.parent_window.sanitize_filename(link_text)
                filename = f"{sanitized_name}.md"
                file_path = os.path.join(self.parent_window.notes_dir, filename)
            
            # Save current file first
            self.parent_window.save_current_file()
            
            # If file doesn't exist, create it (and directories if needed)
            if not os.path.exists(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                open(file_path, 'a').close()
                self.parent_window.load_files()
            
            # Open the linked file in the tree
            iterator = QTreeWidgetItemIterator(self.parent_window.file_tree)
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.UserRole) == file_path:
                    self.parent_window.file_tree.setCurrentItem(item)
                    self.parent_window.on_file_selected(item, 0)
                    break
                iterator += 1
    
    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        position = cursor.position()
        
        hovering_on_link = False
        
        # In read-only mode, check against the original text positions
        if self.parent_window and self.parent_window.is_read_only:
            original_text = self.parent_window.original_content
            pattern = r'\[\[([^\]]+)\]\]'
            offset = 0
            
            for match in re.finditer(pattern, original_text):
                link_text = match.group(1)
                # Calculate where this link appears in the displayed text
                display_start = match.start() - offset
                display_end = display_start + len(link_text)
                
                if display_start <= position <= display_end:
                    hovering_on_link = True
                    break
                
                offset += 4  # Account for removed [[ and ]]
        else:
            # Normal edit mode
            text = self.toPlainText()
            pattern = r'\[\[([^\]]+)\]\]'
            for match in re.finditer(pattern, text):
                if match.start() <= position <= match.end():
                    hovering_on_link = True
                    break
        
        if hovering_on_link:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
            
        super().mouseMoveEvent(event)


class ObsidianClone(QMainWindow):
    def __init__(self):
        super().__init__()
        # Use OBCLONEDATA environment variable if set, otherwise use current directory
        base_dir = os.environ.get('OBCLONEDATA', os.getcwd())
        self.notes_dir = os.path.join(base_dir, "obclonedata")
        self.current_file = None
        self.original_content = ""  # Store original content for mode switching
        self.is_read_only = True  # Start in read-only mode
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(5000)  # 5 seconds
        self.setup_notes_directory()
        self.init_ui()
        self.load_files()
        self.open_default_file()
    
    def event(self, event):
        """Override event handler to catch macOS dock icon clicks"""
        if sys.platform == 'darwin' and event.type() == QEvent.ApplicationActivate:
            # Force window to front
            self.show()
            self.raise_()
            self.activateWindow()
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        return super().event(event)
    
    def sanitize_filename(self, name):
        """Convert spaces and newlines to underscores in filenames"""
        # Replace spaces, newlines, and other whitespace with underscores
        sanitized = re.sub(r'\s+', '_', name.strip())
        return sanitized
        
    def setup_notes_directory(self):
        """Create notes directory and default home.md file if they don't exist"""
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)
            
        home_file = os.path.join(self.notes_dir, "home.md")
        if not os.path.exists(home_file):
            open(home_file, 'a').close()
            
        # Create .trash directory
        trash_dir = os.path.join(self.notes_dir, ".trash")
        if not os.path.exists(trash_dir):
            os.makedirs(trash_dir)
            
    def init_ui(self):
        self.setWindowTitle("Obsidian Clone")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - File tree and button
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
    def load_files(self):
        """Load all .md files and directories from notes directory"""
        self.file_tree.clear()
        
        if os.path.exists(self.notes_dir):
            self._load_directory(self.notes_dir, self.file_tree.invisibleRootItem())
    
    def _load_directory(self, dir_path, parent_item):
        """Recursively load directory contents"""
        try:
            items = []
            special_items = []
            
            # First collect all items
            for name in sorted(os.listdir(dir_path)):
                full_path = os.path.join(dir_path, name)
                is_dir = os.path.isdir(full_path)
                
                # Separate .trash and .journal for special handling
                if (name in [".trash", ".journal"]) and dir_path == self.notes_dir:
                    special_items.append((name, full_path, is_dir))
                else:
                    items.append((name, full_path, is_dir))
            
            # Add directories first (except special ones)
            for name, full_path, is_dir in items:
                if is_dir:
                    dir_item = QTreeWidgetItem(parent_item, [name])
                    dir_item.setData(0, Qt.UserRole, full_path)
                    dir_item.setData(0, Qt.UserRole + 1, "directory")
                    # Set italic font for directories
                    font = dir_item.font(0)
                    font.setItalic(True)
                    dir_item.setFont(0, font)
                    self._load_directory(full_path, dir_item)
            
            # Then add files
            for name, full_path, is_dir in items:
                if not is_dir and name.endswith('.md'):
                    display_name = name[:-3]  # Remove .md extension
                    file_item = QTreeWidgetItem(parent_item, [display_name])
                    file_item.setData(0, Qt.UserRole, full_path)
                    file_item.setData(0, Qt.UserRole + 1, "file")
            
            # Add special directories at the bottom with special styling
            for name, full_path, is_dir in special_items:
                special_item = QTreeWidgetItem(parent_item, [name])
                special_item.setData(0, Qt.UserRole, full_path)
                
                if name == ".trash":
                    special_item.setData(0, Qt.UserRole + 1, "trash")
                    # Set lighter color for trash
                    special_item.setForeground(0, QColor(150, 150, 150))
                elif name == ".journal":
                    special_item.setData(0, Qt.UserRole + 1, "journal")
                    # Set blue color for journal
                    special_item.setForeground(0, QColor(0, 100, 200))
                
                # Set italic font for special directories
                font = special_item.font(0)
                font.setItalic(True)
                special_item.setFont(0, font)
                self._load_directory(full_path, special_item)
                
        except PermissionError:
            pass
            
    def open_default_file(self):
        """Open home.md by default"""
        home_file = os.path.join(self.notes_dir, "home.md")
        # Find and select home.md in the tree
        iterator = QTreeWidgetItemIterator(self.file_tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole) == home_file:
                self.file_tree.setCurrentItem(item)
                self.on_file_selected(item, 0)
                break
            iterator += 1
    
    def get_ordinal_suffix(self, day):
        """Get ordinal suffix for a day number (1st, 2nd, 3rd, 4th, etc.)"""
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return suffix
    
    def open_today_journal(self):
        """Open today's journal entry, creating it if necessary"""
        # Get current date
        today = datetime.now()
        year = today.strftime("%Y")
        month = today.strftime("%m")
        day = today.strftime("%d")
        
        # Create journal path
        journal_dir = os.path.join(self.notes_dir, ".journal", year, month)
        journal_file = os.path.join(journal_dir, f"{day}.md")
        
        # Save current file first
        self.save_current_file()
        
        # Create directories if they don't exist
        os.makedirs(journal_dir, exist_ok=True)
        
        # Create file if it doesn't exist
        if not os.path.exists(journal_file):
            with open(journal_file, 'w', encoding='utf-8') as f:
                # Format: "Thursday 29th May 2025"
                day_of_week = today.strftime("%A")
                day_num = today.day
                month_name = today.strftime("%B")
                year_str = today.strftime("%Y")
                suffix = self.get_ordinal_suffix(day_num)
                
                date_header = f"{day_of_week} {day_num}{suffix} {month_name} {year_str}"
                f.write(f"# {date_header}\n\n")
        
        # Reload files to show new directories/files in tree
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
    
    def show_context_menu(self, position):
        """Show context menu for file operations"""
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
    
    def create_subdirectory(self):
        """Create a new subdirectory"""
        current_item = self.file_tree.currentItem()
        
        # Determine parent directory
        if current_item:
            item_type = current_item.data(0, Qt.UserRole + 1)
            if item_type == "directory":
                parent_path = current_item.data(0, Qt.UserRole)
                parent_item = current_item
            else:
                # If a file is selected, use its parent directory
                parent_item = current_item.parent() or self.file_tree.invisibleRootItem()
                if parent_item == self.file_tree.invisibleRootItem():
                    parent_path = self.notes_dir
                else:
                    parent_path = parent_item.data(0, Qt.UserRole)
        else:
            parent_path = self.notes_dir
            parent_item = self.file_tree.invisibleRootItem()
        
        # Get directory name from user
        name, ok = QInputDialog.getText(self, "Create Subdirectory", "Directory name:")
        if ok and name:
            # Sanitize directory name
            sanitized_name = self.sanitize_filename(name)
            new_dir_path = os.path.join(parent_path, sanitized_name)
            
            try:
                os.makedirs(new_dir_path, exist_ok=True)
                # Reload the tree
                self.load_files()
                # Expand the parent item
                if parent_item != self.file_tree.invisibleRootItem():
                    parent_item.setExpanded(True)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create directory: {str(e)}")
    
    def delete_item(self):
        """Delete the selected file or directory"""
        current_item = self.file_tree.currentItem()
        if not current_item:
            return
        
        item_type = current_item.data(0, Qt.UserRole + 1)
        item_path = current_item.data(0, Qt.UserRole)
        item_name = os.path.basename(item_path)
        
        if item_type in ["trash", "journal"]:
            QMessageBox.warning(self, "Cannot Delete", f"The {item_name} directory cannot be deleted.")
            return
        
        if item_type == "file":
            # Move file to trash
            trash_dir = os.path.join(self.notes_dir, ".trash")
            
            # Generate unique filename if file already exists in trash
            trash_path = os.path.join(trash_dir, item_name)
            if os.path.exists(trash_path):
                base, ext = os.path.splitext(item_name)
                counter = 1
                while os.path.exists(trash_path):
                    trash_path = os.path.join(trash_dir, f"{base}_{counter}{ext}")
                    counter += 1
            
            try:
                os.rename(item_path, trash_path)
                # If this was the current file, clear the editor
                if item_path == self.current_file:
                    self.current_file = None
                    self.editor.clear()
                    self.original_content = ""
                self.load_files()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not move file to trash: {str(e)}")
                
        elif item_type == "directory":
            # Check if directory is empty
            try:
                if os.listdir(item_path):
                    QMessageBox.warning(self, "Cannot Delete", "Directory is not empty.")
                else:
                    os.rmdir(item_path)
                    self.load_files()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete directory: {str(e)}")
    
    def rename_item(self):
        """Rename the selected file or directory"""
        current_item = self.file_tree.currentItem()
        if not current_item:
            return
        
        item_type = current_item.data(0, Qt.UserRole + 1)
        item_path = current_item.data(0, Qt.UserRole)
        old_name = os.path.basename(item_path)
        
        # Don't allow renaming special directories
        if item_type in ["trash", "journal"]:
            QMessageBox.warning(self, "Cannot Rename", f"The {old_name} directory cannot be renamed.")
            return
        
        # Get new name from user
        if item_type == "file":
            # For files, show name without .md extension
            display_name = old_name[:-3] if old_name.endswith('.md') else old_name
            new_name, ok = QInputDialog.getText(self, "Rename File", 
                                               "New name:", text=display_name)
            if ok and new_name:
                # Sanitize and add .md extension
                new_name = self.sanitize_filename(new_name)
                if not new_name.endswith('.md'):
                    new_name += '.md'
        else:
            # For directories
            new_name, ok = QInputDialog.getText(self, "Rename Directory", 
                                               "New name:", text=old_name)
            if ok and new_name:
                new_name = self.sanitize_filename(new_name)
        
        if not (ok and new_name):
            return
        
        # Check if new name is same as old
        if new_name == old_name:
            return
        
        # Construct new path
        parent_dir = os.path.dirname(item_path)
        new_path = os.path.join(parent_dir, new_name)
        
        # Check if target already exists
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Cannot Rename", 
                              f"A {'file' if item_type == 'file' else 'directory'} with that name already exists.")
            return
        
        try:
            # Rename the file/directory
            os.rename(item_path, new_path)
            
            # Update links if it's a file
            if item_type == "file":
                self.update_links_after_move(item_path, new_path)
            
            # If this was the current file, update the path
            if item_path == self.current_file:
                self.current_file = new_path
            
            # Reload the tree
            self.load_files()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not rename: {str(e)}")
    
    def tree_drop_event(self, event):
        """Handle file drops in the tree"""
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
                
            if item_type == "directory":
                target_dir = target_item.data(0, Qt.UserRole)
            else:
                # Dropped on a file, use its parent directory
                parent = target_item.parent()
                if parent:
                    target_dir = parent.data(0, Qt.UserRole)
                else:
                    target_dir = self.notes_dir
        else:
            target_dir = self.notes_dir
        
        # Get source file info
        source_path = dragged_item.data(0, Qt.UserRole)
        filename = os.path.basename(source_path)
        dest_path = os.path.join(target_dir, filename)
        
        # Don't move to same location
        if source_path == dest_path:
            event.ignore()
            return
        
        try:
            # Move the file
            os.rename(source_path, dest_path)
            
            # Update links in all files
            self.update_links_after_move(source_path, dest_path)
            
            # Reload the tree
            self.load_files()
            
            # If the moved file was open, update current file path
            if self.current_file == source_path:
                self.current_file = dest_path
            
            event.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not move file: {str(e)}")
            event.ignore()
    
    def update_links_after_move(self, old_path, new_path):
        """Update all links after a file has been moved"""
        # Walk through all .md files and update links
        for root, dirs, files in os.walk(self.notes_dir):
            for filename in files:
                if filename.endswith('.md'):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        updated_content = content
                        
                        # Find all [[...]] links
                        link_pattern = r'\[\[([^\]]+)\]\]'
                        
                        for match in re.finditer(link_pattern, content):
                            link_text = match.group(1)  # The text inside [[ ]]
                            
                            # Convert the link text to a file path
                            if '/' in link_text:
                                # Handle subdirectory path
                                parts = link_text.split('/')
                                # Sanitize each part
                                sanitized_parts = [self.sanitize_filename(part) for part in parts]
                                # Add .md to the last part
                                sanitized_parts[-1] = f"{sanitized_parts[-1]}.md"
                                link_file_path = os.path.join(self.notes_dir, *sanitized_parts)
                            else:
                                # Simple filename
                                sanitized_name = self.sanitize_filename(link_text)
                                link_file_path = os.path.join(self.notes_dir, f"{sanitized_name}.md")
                            
                            # Normalize paths for comparison
                            link_file_path = os.path.normpath(link_file_path)
                            old_path_norm = os.path.normpath(old_path)
                            
                            # If this link pointed to the moved file, update it
                            if link_file_path == old_path_norm:
                                # Get the new relative path
                                new_rel = os.path.relpath(new_path, self.notes_dir).replace(os.sep, '/')
                                if new_rel.endswith('.md'):
                                    new_rel = new_rel[:-3]
                                
                                # For the new link text, we need to "unsanitize" it
                                # by replacing underscores back to spaces in the filename part
                                new_parts = new_rel.split('/')
                                # Only unsanitize the last part (filename)
                                new_parts[-1] = new_parts[-1].replace('_', ' ')
                                new_link_text = '/'.join(new_parts)
                                
                                # Replace the old link with the new one
                                old_link_full = match.group(0)
                                new_link = f'[[{new_link_text}]]'
                                updated_content = updated_content.replace(old_link_full, new_link)
                        
                        # Write back if content changed
                        if updated_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(updated_content)
                            
                            # If this is the currently open file, reload it
                            if file_path == self.current_file:
                                self.editor.setPlainText(updated_content)
                                self.original_content = updated_content
                                if self.is_read_only:
                                    self.format_for_read_only()
                                else:
                                    self.format_links()
                    except Exception as e:
                        print(f"Error updating links in {file_path}: {e}")
    
    def toggle_mode(self):
        """Toggle between edit and read-only mode"""
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
            
    def on_file_selected(self, item, column):
        """Handle file selection from the tree"""
        # Only process files, not directories
        if item.data(0, Qt.UserRole + 1) != "file":
            return
            
        # Don't allow editing files in .trash
        file_path = item.data(0, Qt.UserRole)
        if ".trash" in file_path:
            return
            
        # Save current file before switching
        if self.current_file:
            self.save_current_file()
            
        # Load selected file
        self.current_file = file_path
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.original_content = content  # Store original content
                self.editor.setPlainText(content)
                if self.is_read_only:
                    self.format_for_read_only()
                else:
                    self.format_links()
        except FileNotFoundError:
            self.editor.clear()
            self.original_content = ""
            
    def on_text_changed(self):
        """Handle text changes in the editor"""
        if not self.current_file or self.is_read_only:
            return
            
        # Update stored original content in edit mode
        self.original_content = self.editor.toPlainText()
        
        # Apply link formatting
        self.format_links()
    
    def format_links(self):
        """Apply visual formatting to [[page]] links"""
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
        pattern = r'\[\[([^\]]+)\]\]'
        
        for match in re.finditer(pattern, text):
            start = match.start()
            end = match.end()
            
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
    
    def format_for_read_only(self):
        """Format text for read-only mode - hide [[ ]] brackets"""
        # Temporarily disconnect the textChanged signal
        self.editor.textChanged.disconnect()
        
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        
        # Get the full text
        text = self.editor.toPlainText()
        pattern = r'\[\[([^\]]+)\]\]'
        
        # Create a new document with formatted text
        new_cursor = QTextCursor(self.editor.document())
        new_cursor.select(QTextCursor.Document)
        new_cursor.removeSelectedText()
        
        last_end = 0
        
        # Create default format for regular text
        default_format = QTextCharFormat()
        
        for match in re.finditer(pattern, text):
            # Add text before the match with default format
            if match.start() > last_end:
                new_cursor.insertText(text[last_end:match.start()], default_format)
            
            # Add the link text without brackets
            link_text = match.group(1)
            link_format = QTextCharFormat()
            link_format.setForeground(QColor(0, 0, 255))
            link_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            new_cursor.insertText(link_text, link_format)
            
            last_end = match.end()
        
        # Add remaining text with default format
        if last_end < len(text):
            new_cursor.insertText(text[last_end:], default_format)
        
        cursor.endEditBlock()
        
        # Reconnect the signal
        self.editor.textChanged.connect(self.on_text_changed)
                
    def save_current_file(self):
        """Save the current file"""
        if self.current_file:
            try:
                # Use original content if in read-only mode
                if self.is_read_only:
                    content = self.original_content
                else:
                    content = self.editor.toPlainText()
                    self.original_content = content  # Update stored content
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"Error saving file: {e}")
                
    def auto_save(self):
        """Auto-save the current file"""
        self.save_current_file()
        
    def closeEvent(self, event):
        """Save before closing"""
        self.save_current_file()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = ObsidianClone()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()