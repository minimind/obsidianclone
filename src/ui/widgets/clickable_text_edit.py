"""
Clickable text editor widget for the Obsidian Clone application.

This module provides a custom QTextEdit widget that supports clickable wiki-style
links, undo/redo functionality, and different display modes for reading and editing.
"""

import re
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt, QEvent, QRect, QRectF, QPointF
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QTextBlock, QTextBlockFormat, QPainter, QBrush, QPolygonF


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
        
        # Connect text change signal for updates
        self.textChanged.connect(self.on_internal_text_changed)
        
        # Undo/Redo stack configuration
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_items = 100
        self.last_saved_state = ""
        self.is_undoing = False
        
        # AI response blocks (legacy)
        self.ai_response_blocks = {}  # Map block number to AI response info
        
        # Chat message blocks for new chat UI
        self.chat_message_blocks = {}  # Map block number to {'role': 'user'|'assistant', 'start': int, 'end': int}
        
        # Flag to prevent recursive formatting calls
        self.is_formatting = False
        
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
        Handle keyboard shortcuts for undo/redo operations and prevent editing in assistant blocks.
        
        Supports:
        - Ctrl+Z for undo
        - Ctrl+Y or Ctrl+Shift+Z for redo
        - Prevents editing in assistant blocks
        
        Args:
            event: The key press event
        """
        # Check if cursor is in an assistant block and prevent editing
        if self.is_cursor_in_assistant_block():
            # Allow navigation keys
            navigation_keys = [
                Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
                Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown
            ]
            
            # Allow copy operations
            if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
                super().keyPressEvent(event)
                return
            
            # Allow selection with Shift
            if event.modifiers() & Qt.ShiftModifier and event.key() in navigation_keys:
                super().keyPressEvent(event)
                return
            
            # Allow navigation without modifiers
            if event.key() in navigation_keys and not event.modifiers():
                super().keyPressEvent(event)
                return
            
            # Block all other editing operations in assistant blocks
            event.accept()
            return
        
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
        # Update AI responses and chat messages
        self.find_ai_response_blocks()
        self.find_chat_message_blocks()
        self.update_block_visibility()
        
        # Apply formatting only when loading content, not during editing
        if not self.is_undoing:
            self.apply_ai_response_formatting()
        
        # Don't save undo state if we're in the middle of undoing/redoing
        if not self.is_undoing and self.parent_window and hasattr(self.parent_window, 'is_read_only') and not self.parent_window.is_read_only:
            # Save initial state when setting new text
            if not self.undo_stack or (self.undo_stack and self.undo_stack[-1]['text'] != text):
                self.save_undo_state()
        
    def paintEvent(self, event: QEvent) -> None:
        """Paint event with hidden markers."""
        # Let the base class draw the text
        super().paintEvent(event)
        
        # Update block detection and hide markers
        self.find_ai_response_blocks()
        self.find_chat_message_blocks()
        self.update_block_visibility()
    
    
    def apply_ai_response_formatting(self) -> None:
        """Apply visual formatting to AI response blocks."""
        if self.is_formatting:
            return
        
        self.is_formatting = True
        try:
            # Create pale blue format for AI responses
            ai_format = QTextCharFormat()
            ai_format.setForeground(QColor(100, 149, 237))  # Pale blue
            
            # Go through all AI response blocks and apply formatting
            for block_num in self.ai_response_blocks:
                ai_info = self.ai_response_blocks[block_num]
                start_block = ai_info['start']
                end_block = ai_info['end']
                
                # Format all blocks in the AI response range except markers
                for i in range(start_block, end_block + 1):
                    block = self.document().findBlockByNumber(i)
                    text = block.text().strip()
                    
                    # Skip marker blocks
                    if text in ["§§§AI_RESPONSE_START§§§", "§§§AI_RESPONSE_END§§§"]:
                        continue
                    
                    # Apply format to the entire block content
                    cursor = QTextCursor(block)
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    cursor.mergeCharFormat(ai_format)
        finally:
            self.is_formatting = False
    
    def refresh_formatting(self) -> None:
        """Refresh AI response formatting - call this when content changes significantly."""
        self.find_ai_response_blocks()
        self.find_chat_message_blocks()
        self.update_block_visibility()
        self.apply_ai_response_formatting()
    
    def showEvent(self, event) -> None:
        """Apply formatting when the widget is first shown."""
        super().showEvent(event)
        # Apply formatting when the widget becomes visible
        self.refresh_formatting()
    
    def is_cursor_in_assistant_block(self, cursor_position: int = None) -> bool:
        """Check if the cursor is currently in an assistant message block."""
        if cursor_position is None:
            cursor_position = self.textCursor().position()
        
        document = self.document()
        cursor = QTextCursor(document)
        cursor.setPosition(cursor_position)
        block_number = cursor.blockNumber()
        
        # Check if this block is part of an assistant message
        if block_number in self.chat_message_blocks:
            message_info = self.chat_message_blocks[block_number]
            return message_info['role'] == 'assistant'
        
        # Also check legacy AI response blocks
        if block_number in self.ai_response_blocks:
            return True
            
        return False
    
    def get_assistant_block_range(self, cursor_position: int = None) -> tuple:
        """Get the start and end positions of the assistant block containing the cursor."""
        if cursor_position is None:
            cursor_position = self.textCursor().position()
        
        document = self.document()
        cursor = QTextCursor(document)
        cursor.setPosition(cursor_position)
        block_number = cursor.blockNumber()
        
        # Check chat message blocks first
        if block_number in self.chat_message_blocks:
            message_info = self.chat_message_blocks[block_number]
            if message_info['role'] == 'assistant':
                start_block = message_info['start']
                end_block = message_info['end']
                
                # Get actual text positions
                start_block_obj = document.findBlockByNumber(start_block)
                end_block_obj = document.findBlockByNumber(end_block)
                
                start_cursor = QTextCursor(start_block_obj)
                end_cursor = QTextCursor(end_block_obj)
                end_cursor.movePosition(QTextCursor.EndOfBlock)
                
                return (start_cursor.position(), end_cursor.position())
        
        # Check legacy AI response blocks
        if block_number in self.ai_response_blocks:
            ai_info = self.ai_response_blocks[block_number]
            start_block = ai_info['start']
            end_block = ai_info['end']
            
            start_block_obj = document.findBlockByNumber(start_block)
            end_block_obj = document.findBlockByNumber(end_block)
            
            start_cursor = QTextCursor(start_block_obj)
            end_cursor = QTextCursor(end_block_obj)
            end_cursor.movePosition(QTextCursor.EndOfBlock)
            
            return (start_cursor.position(), end_cursor.position())
        
        return (None, None)
    
        
    def on_internal_text_changed(self) -> None:
        """Handle internal text changes to update AI responses and chat messages."""
        if self.is_formatting:
            return
        
        # Only update block detection, don't apply formatting on every change
        self.find_ai_response_blocks()
        self.find_chat_message_blocks()
        self.update_block_visibility()
        
    def find_ai_response_blocks(self) -> None:
        """Find all AI response blocks marked with special markers."""
        self.ai_response_blocks.clear()
        document = self.document()
        
        in_ai_response = False
        ai_response_start = None
        
        for block_num in range(document.blockCount()):
            block = document.findBlockByNumber(block_num)
            text = block.text().strip()
            
            if text == "§§§AI_RESPONSE_START§§§":
                in_ai_response = True
                ai_response_start = block_num  # Include the marker line
            elif text == "§§§AI_RESPONSE_END§§§":
                if in_ai_response and ai_response_start is not None:
                    # Mark all blocks including markers as AI response
                    for i in range(ai_response_start, block_num + 1):
                        self.ai_response_blocks[i] = {
                            'start': ai_response_start,
                            'end': block_num
                        }
                in_ai_response = False
                ai_response_start = None
    
    def find_chat_message_blocks(self) -> None:
        """Find and classify chat message blocks for conversation UI."""
        self.chat_message_blocks.clear()
        document = self.document()
        
        current_role = 'user'  # Start with user
        current_message_start = 0
        
        for block_num in range(document.blockCount()):
            block = document.findBlockByNumber(block_num)
            text = block.text().strip()
            
            # Check for AI response markers (transition to assistant)
            if text == "§§§AI_RESPONSE_START§§§":
                # End current user message if exists
                if current_role == 'user' and block_num > current_message_start:
                    self._mark_chat_message_range(current_message_start, block_num - 1, 'user')
                
                current_role = 'assistant'
                current_message_start = block_num + 1  # Start after marker
                
            elif text == "§§§AI_RESPONSE_END§§§":
                # End current assistant message
                if current_role == 'assistant' and block_num > current_message_start:
                    self._mark_chat_message_range(current_message_start, block_num - 1, 'assistant')
                
                current_role = 'user'
                current_message_start = block_num + 1  # Start after marker
        
        # Handle final message that extends to end of document
        if current_message_start < document.blockCount():
            self._mark_chat_message_range(current_message_start, document.blockCount() - 1, current_role)
    
    def _mark_chat_message_range(self, start_block: int, end_block: int, role: str) -> None:
        """Mark a range of blocks as belonging to a chat message."""
        for i in range(start_block, end_block + 1):
            self.chat_message_blocks[i] = {
                'role': role,
                'start': start_block,
                'end': end_block
            }
                
    def update_block_visibility(self) -> None:
        """Update the visibility of all blocks based on markers."""
        document = self.document()
        
        for block_num in range(document.blockCount()):
            block = document.findBlockByNumber(block_num)
            text = block.text().strip()
            
            # Always hide AI response marker blocks
            if text in ["§§§AI_RESPONSE_START§§§", "§§§AI_RESPONSE_END§§§"]:
                block.setVisible(False)
            else:
                # Regular blocks are always visible
                block.setVisible(True)