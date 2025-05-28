#!/usr/bin/env python3
import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, 
                             QListWidget, QTextEdit, QVBoxLayout, 
                             QWidget, QListWidgetItem, QPushButton)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor


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
            # Sanitize the link text for filename
            sanitized_name = self.parent_window.sanitize_filename(link_text)
            filename = f"{sanitized_name}.md"
            file_path = os.path.join(self.parent_window.notes_dir, filename)
            
            # Save current file first
            self.parent_window.save_current_file()
            
            # If file doesn't exist, create it
            if not os.path.exists(file_path):
                open(file_path, 'a').close()
                self.parent_window.load_files()
            
            # Open the linked file
            for i in range(self.parent_window.file_list.count()):
                item = self.parent_window.file_list.item(i)
                item_path = item.data(Qt.UserRole)
                if item_path == file_path:
                    self.parent_window.file_list.setCurrentItem(item)
                    self.parent_window.on_file_selected(item)
                    break
    
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
        self.notes_dir = os.path.join(os.getcwd(), "obsidianclone")
        self.current_file = None
        self.original_content = ""  # Store original content for mode switching
        self.is_read_only = False  # Start in edit mode
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(5000)  # 5 seconds
        self.setup_notes_directory()
        self.init_ui()
        self.load_files()
        self.open_default_file()
    
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
        
        # Left side - File list and button
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        left_layout.addWidget(self.file_list)
        
        # Mode toggle button
        self.mode_button = QPushButton("Read Only")
        self.mode_button.clicked.connect(self.toggle_mode)
        left_layout.addWidget(self.mode_button)
        
        splitter.addWidget(left_widget)
        
        # Right side - Markdown editor
        self.editor = ClickableTextEdit(self)
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.textChanged.connect(self.on_text_changed)
        splitter.addWidget(self.editor)
        
        # Set splitter sizes (30% for file list, 70% for editor)
        splitter.setSizes([360, 840])
        
    def load_files(self):
        """Load all .md files from notes directory"""
        self.file_list.clear()
        
        if os.path.exists(self.notes_dir):
            for filename in os.listdir(self.notes_dir):
                if filename.endswith('.md'):
                    file_path = os.path.join(self.notes_dir, filename)
                    item = QListWidgetItem(filename)
                    item.setData(Qt.UserRole, file_path)
                    self.file_list.addItem(item)
            
    def open_default_file(self):
        """Open home.md by default"""
        home_file = os.path.join(self.notes_dir, "home.md")
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == home_file:
                self.file_list.setCurrentItem(item)
                self.on_file_selected(item)
                break
    
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
            
    def on_file_selected(self, item):
        """Handle file selection from the list"""
        # Save current file before switching
        if self.current_file:
            self.save_current_file()
            
        # Load selected file
        file_path = item.data(Qt.UserRole)
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
        
        text = self.editor.toPlainText()
        
        # Find all [[page]] patterns
        pattern = r'\[\[([^\]]+)\]\]'
        matches = re.findall(pattern, text)
        
        for match in matches:
            # Create file if it doesn't exist
            sanitized_name = self.sanitize_filename(match)
            filename = f"{sanitized_name}.md"
            file_path = os.path.join(self.notes_dir, filename)
            
            if not os.path.exists(file_path):
                open(file_path, 'a').close()
                # Reload file list to show new file
                self.load_files()
        
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
        
        for match in re.finditer(pattern, text):
            # Add text before the match
            if match.start() > last_end:
                new_cursor.insertText(text[last_end:match.start()])
            
            # Add the link text without brackets
            link_text = match.group(1)
            link_format = QTextCharFormat()
            link_format.setForeground(QColor(0, 0, 255))
            link_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            new_cursor.insertText(link_text, link_format)
            
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            new_cursor.insertText(text[last_end:])
        
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