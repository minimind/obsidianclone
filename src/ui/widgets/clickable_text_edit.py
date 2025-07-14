"""
Clickable text editor widget for the Obsidian Clone application.

This module provides a custom QTextEdit widget that supports clickable wiki-style
links, undo/redo functionality, and different display modes for reading and editing.
"""

import re
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor


class ClickableTextEdit(QTextEdit):
    """
    A custom text editor widget that supports clickable wiki-style links.
    
    This widget extends QTextEdit to provide:
    - Clickable [[page]] style links
    - Custom undo/redo stack management
    - Different display modes for reading vs editing
    - Link highlighting and cursor changes on hover
    
    Attributes:
        parent_window: Reference to the main window for accessing application state
        anchor_at_cursor: Stores the link text under the cursor
        undo_stack: List of editor states for undo functionality
        redo_stack: List of editor states for redo functionality
        max_undo_items: Maximum number of undo states to maintain
        last_saved_state: Content state at last save point
        is_undoing: Flag to prevent recursive undo state saves
    """
    
    def __init__(self, parent=None):
        """
        Initialize the clickable text editor.
        
        Args:
            parent: Parent widget, typically the main window
        """
        super().__init__(parent)
        self.parent_window = parent
        self.setMouseTracking(True)
        self.viewport().setCursor(Qt.IBeamCursor)
        self.anchor_at_cursor = None
        
        # Undo/Redo stack configuration
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_items = 100
        self.last_saved_state = ""
        self.is_undoing = False
        
    def mousePressEvent(self, event: QEvent) -> None:
        """
        Handle mouse press events to detect clicks on links.
        
        In read-only mode, maps display positions back to original text positions
        to handle links with hidden brackets. In edit mode, directly checks for
        [[page]] patterns at the click position.
        
        Args:
            event: The mouse press event
        """
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            
            # Handle read-only mode where brackets are hidden
            if self.parent_window and self.parent_window.is_read_only:
                # Map position in displayed text back to original text
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
    
    def handle_link_click(self, link_text: str) -> None:
        """
        Handle clicks on wiki-style links.
        
        Creates the linked file if it doesn't exist and navigates to it.
        Supports both simple filenames and subdirectory paths.
        
        Args:
            link_text: The text inside the [[...]] link
        """
        if self.parent_window and hasattr(self.parent_window, 'handle_link_click'):
            self.parent_window.handle_link_click(link_text)
    
    def mouseMoveEvent(self, event: QEvent) -> None:
        """
        Handle mouse move events to change cursor when hovering over links.
        
        Changes the cursor to a pointing hand when hovering over clickable links,
        and back to an I-beam cursor otherwise.
        
        Args:
            event: The mouse move event
        """
        cursor = self.cursorForPosition(event.pos())
        position = cursor.position()
        
        hovering_on_link = False
        
        # Check if hovering over a link
        if self.parent_window and self.parent_window.is_read_only:
            # Read-only mode position mapping
            original_text = self.parent_window.original_content
            pattern = r'\[\[([^\]]+)\]\]'
            offset = 0
            
            for match in re.finditer(pattern, original_text):
                link_text = match.group(1)
                display_start = match.start() - offset
                display_end = display_start + len(link_text)
                
                if display_start <= position <= display_end:
                    hovering_on_link = True
                    break
                
                offset += 4
        else:
            # Normal edit mode
            text = self.toPlainText()
            pattern = r'\[\[([^\]]+)\]\]'
            for match in re.finditer(pattern, text):
                if match.start() <= position <= match.end():
                    hovering_on_link = True
                    break
        
        # Update cursor appearance
        if hovering_on_link:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
            
        super().mouseMoveEvent(event)
    
    def save_undo_state(self) -> None:
        """
        Save the current editor state to the undo stack.
        
        Captures the current text content and cursor position. Avoids saving
        duplicate states and manages stack size limits.
        """
        if self.is_undoing:
            return
            
        current_state = {
            'text': self.toPlainText(),
            'cursor_position': self.textCursor().position()
        }
        
        # Don't save if text hasn't changed
        if self.undo_stack and self.undo_stack[-1]['text'] == current_state['text']:
            return
            
        self.undo_stack.append(current_state)
        
        # Limit undo stack size
        if len(self.undo_stack) > self.max_undo_items:
            self.undo_stack.pop(0)
            
        # Clear redo stack when new edit is made
        self.redo_stack.clear()
    
    def undo(self) -> None:
        """
        Undo the last edit operation.
        
        Restores the previous editor state from the undo stack and moves
        the current state to the redo stack.
        """
        if len(self.undo_stack) <= 1:
            return  # Nothing to undo
            
        # Save current state to redo stack
        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)
        
        # Get the previous state
        previous_state = self.undo_stack[-1]
            
        # Apply the undo
        self.is_undoing = True
        self.setPlainText(previous_state['text'])
        cursor = self.textCursor()
        # Ensure cursor position is within bounds
        max_position = len(previous_state['text'])
        cursor_pos = min(previous_state['cursor_position'], max_position)
        cursor.setPosition(cursor_pos)
        self.setTextCursor(cursor)
        self.is_undoing = False
        
        # Trigger formatting update
        if self.parent_window and hasattr(self.parent_window, 'format_links'):
            if self.parent_window.is_read_only:
                self.parent_window.format_for_read_only()
            else:
                self.parent_window.format_links()
    
    def redo(self) -> None:
        """
        Redo the last undone edit operation.
        
        Restores a state from the redo stack and moves it back to the undo stack.
        """
        if not self.redo_stack:
            return
            
        # Pop from redo stack and push to undo stack
        redo_state = self.redo_stack.pop()
        self.undo_stack.append(redo_state)
        
        # Apply the redo
        self.is_undoing = True
        self.setPlainText(redo_state['text'])
        cursor = self.textCursor()
        # Ensure cursor position is within bounds
        max_position = len(redo_state['text'])
        cursor_pos = min(redo_state['cursor_position'], max_position)
        cursor.setPosition(cursor_pos)
        self.setTextCursor(cursor)
        self.is_undoing = False
        
        # Trigger formatting update
        if self.parent_window and hasattr(self.parent_window, 'format_links'):
            if self.parent_window.is_read_only:
                self.parent_window.format_for_read_only()
            else:
                self.parent_window.format_links()
    
    def keyPressEvent(self, event: QEvent) -> None:
        """
        Handle keyboard shortcuts for undo/redo operations.
        
        Supports:
        - Ctrl+Z for undo
        - Ctrl+Y or Ctrl+Shift+Z for redo
        
        Args:
            event: The key press event
        """
        # Check for Ctrl+Z (undo)
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            # Only allow undo in edit mode
            if self.parent_window and not self.parent_window.is_read_only:
                self.undo()
            event.accept()
            return
            
        # Check for Ctrl+Y or Ctrl+Shift+Z (redo)
        if ((event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Y) or
            (event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_Z)):
            # Only allow redo in edit mode
            if self.parent_window and not self.parent_window.is_read_only:
                self.redo()
            event.accept()
            return
            
        # Save state before certain key operations
        if not self.is_undoing and event.key() != Qt.Key_Control:
            # For certain keys, save state immediately
            if event.key() in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Delete, Qt.Key_Backspace]:
                self.save_undo_state()
            elif event.text() and event.text().isprintable():
                # For regular typing, we'll save after text changes
                pass
                
        super().keyPressEvent(event)
    
    def clear_undo_history(self) -> None:
        """Clear both undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.last_saved_state = self.toPlainText()
    
    def setPlainText(self, text: str) -> None:
        """
        Override setPlainText to handle undo state management.
        
        Args:
            text: The text to set in the editor
        """
        super().setPlainText(text)
        # Don't save undo state if we're in the middle of undoing/redoing
        if not self.is_undoing and self.parent_window and hasattr(self.parent_window, 'is_read_only') and not self.parent_window.is_read_only:
            # Save initial state when setting new text
            if not self.undo_stack or (self.undo_stack and self.undo_stack[-1]['text'] != text):
                self.save_undo_state()