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
        
        # Connect text change signal for callout updates
        self.textChanged.connect(self.on_internal_text_changed)
        
        # Undo/Redo stack configuration
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_items = 100
        self.last_saved_state = ""
        self.is_undoing = False
        
        # Callout folding state
        self.folded_callouts = set()  # Set of block numbers that are folded
        self.callout_blocks = {}  # Map block number to callout info
        
        # AI response blocks
        self.ai_response_blocks = {}  # Map block number to AI response info
        
        # Track manually toggled callouts to prevent auto-folding override
        self.manually_toggled_callouts = set()
        
    def mousePressEvent(self, event: QEvent) -> None:
        """
        Handle mouse press events to detect clicks on links and callout folding.
        
        In read-only mode, maps display positions back to original text positions
        to handle links with hidden brackets. In edit mode, directly checks for
        [[page]] patterns at the click position.
        
        Args:
            event: The mouse press event
        """
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            
            # Check if clicking on a callout block
            block = cursor.block()
            block_num = block.blockNumber()
            
            # Check if this is a callout and if we're clicking near the left margin
            if self.is_callout_block(block_num):
                callout_info = self.callout_blocks[block_num]
                start_block = callout_info['start']
                
                # Only allow clicking on the first line of the callout
                if block_num == start_block:
                    # Get click position relative to block
                    click_x = event.pos().x()
                    if click_x < 30:  # Click in left margin area
                        self.toggle_callout_fold(block_num)
                        event.accept()
                        return
            
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
        Handle mouse move events to change cursor when hovering over links and callout fold indicators.
        
        Changes the cursor to a pointing hand when hovering over clickable links or fold indicators,
        and back to an I-beam cursor otherwise.
        
        Args:
            event: The mouse move event
        """
        cursor = self.cursorForPosition(event.pos())
        position = cursor.position()
        
        # Check if hovering over callout fold indicator
        if event.pos().x() < 30:  # In left margin area
            block = cursor.block()
            block_num = block.blockNumber()
            if self.is_callout_block(block_num):
                callout_info = self.callout_blocks[block_num]
                if block_num == callout_info['start']:  # Only on first line of callout
                    self.viewport().setCursor(Qt.PointingHandCursor)
                    super().mouseMoveEvent(event)
                    return
        
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
        # Also clear folded callouts and manual toggle tracking when loading new file
        self.folded_callouts.clear()
        self.manually_toggled_callouts.clear()
    
    def setPlainText(self, text: str) -> None:
        """
        Override setPlainText to handle undo state management.
        
        Args:
            text: The text to set in the editor
        """
        super().setPlainText(text)
        # Update callout blocks and AI responses
        self.find_callout_blocks()
        self.find_ai_response_blocks()
        self.update_block_visibility()
        # Don't save undo state if we're in the middle of undoing/redoing
        if not self.is_undoing and self.parent_window and hasattr(self.parent_window, 'is_read_only') and not self.parent_window.is_read_only:
            # Save initial state when setting new text
            if not self.undo_stack or (self.undo_stack and self.undo_stack[-1]['text'] != text):
                self.save_undo_state()
                
    def find_callout_blocks(self) -> None:
        """Find all callout blocks in the document."""
        self.callout_blocks.clear()
        document = self.document()
        
        current_callout_start = None
        is_thinking_callout = False
        
        for block_num in range(document.blockCount()):
            block = document.findBlockByNumber(block_num)
            text = block.text()
            
            # Check if line starts with > (callout)
            if text.strip().startswith('>'):
                if current_callout_start is None:
                    current_callout_start = block_num
                    # Check if this is a "thinking..." callout
                    if text.strip().lower() == '> thinking...':
                        is_thinking_callout = True
            else:
                # Not a callout line - end current callout if exists
                if current_callout_start is not None:
                    # Store callout block info
                    for i in range(current_callout_start, block_num):
                        self.callout_blocks[i] = {
                            'start': current_callout_start,
                            'end': block_num - 1
                        }
                    
                    # Auto-fold thinking callouts (only if not manually toggled)
                    if (is_thinking_callout and 
                        current_callout_start not in self.manually_toggled_callouts and
                        current_callout_start not in self.folded_callouts):
                        self.folded_callouts.add(current_callout_start)
                    
                    current_callout_start = None
                    is_thinking_callout = False
        
        # Handle callout that extends to end of document
        if current_callout_start is not None:
            for i in range(current_callout_start, document.blockCount()):
                self.callout_blocks[i] = {
                    'start': current_callout_start,
                    'end': document.blockCount() - 1
                }
            
            # Auto-fold thinking callouts (only if not manually toggled)
            if (is_thinking_callout and 
                current_callout_start not in self.manually_toggled_callouts and
                current_callout_start not in self.folded_callouts):
                self.folded_callouts.add(current_callout_start)
                
    def is_callout_block(self, block_num: int) -> bool:
        """Check if a block is part of a callout."""
        return block_num in self.callout_blocks
        
    def toggle_callout_fold(self, block_num: int) -> None:
        """Toggle the fold state of a callout block."""
        if block_num not in self.callout_blocks:
            return
            
        callout_info = self.callout_blocks[block_num]
        start_block = callout_info['start']
        
        # Mark this callout as manually toggled
        self.manually_toggled_callouts.add(start_block)
        
        if start_block in self.folded_callouts:
            self.folded_callouts.remove(start_block)
        else:
            self.folded_callouts.add(start_block)
            
        # Update visibility for all blocks
        self.update_block_visibility()
        
        # Trigger repaint and re-layout
        self.viewport().update()
        
        # Force document re-layout
        document = self.document()
        document.markContentsDirty(0, document.characterCount())
        
    def paintEvent(self, event: QEvent) -> None:
        """Override paint event to draw callout backgrounds and hide AI markers."""
        # Only update visibility if blocks have changed, not on every paint
        # This prevents interfering with manual fold/unfold actions
        
        # First, let the base class draw the text
        super().paintEvent(event)
        
        # Update callout blocks and AI responses
        self.find_callout_blocks()
        self.find_ai_response_blocks()
        
        # Draw callout and AI response backgrounds
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Light yellow color for callouts
        callout_color = QColor(255, 250, 205, 80)  # Light yellow with transparency
        # Light green color for AI responses
        ai_response_color = QColor(205, 255, 205, 80)  # Light green with transparency
        
        document = self.document()
        
        # Track which callouts we've already drawn
        drawn_callouts = set()
        
        for block_num in range(document.blockCount()):
            if block_num in self.callout_blocks:
                callout_info = self.callout_blocks[block_num]
                start_block = callout_info['start']
                end_block = callout_info['end']
                
                # Only draw each callout once (at its start block)
                if block_num != start_block:
                    continue
                    
                # Skip if we've already drawn this callout
                if start_block in drawn_callouts:
                    continue
                drawn_callouts.add(start_block)
                
                # Get the rectangle for the entire callout
                start_block_obj = document.findBlockByNumber(start_block)
                
                # Determine the actual end block based on fold state
                if start_block in self.folded_callouts:
                    # If folded, only show the first line
                    actual_end_block = start_block
                else:
                    # If not folded, show all lines
                    actual_end_block = end_block
                
                end_block_obj = document.findBlockByNumber(actual_end_block)
                
                # Get block layout coordinates
                start_cursor = QTextCursor(start_block_obj)
                end_cursor = QTextCursor(end_block_obj)
                end_cursor.movePosition(QTextCursor.EndOfBlock)
                
                start_rect = self.cursorRect(start_cursor)
                end_rect = self.cursorRect(end_cursor)
                
                # Create rectangle covering the callout
                callout_rect = QRectF(
                    start_rect.left() - 5,
                    start_rect.top(),
                    self.viewport().width() - 10,
                    end_rect.bottom() - start_rect.top()
                )
                
                # Draw rounded rectangle background
                painter.setBrush(QBrush(callout_color))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(callout_rect, 5, 5)
                
                # Draw fold indicator on the first line
                if block_num == start_block:
                    # Draw a small triangle or arrow
                    indicator_rect = QRectF(5, start_rect.top() + 5, 10, 10)
                    painter.setBrush(QBrush(QColor(100, 100, 100)))
                    
                    if start_block in self.folded_callouts:
                        # Draw right-pointing triangle for folded
                        triangle = QPolygonF([
                            QPointF(indicator_rect.left(), indicator_rect.top()),
                            QPointF(indicator_rect.left(), indicator_rect.bottom()),
                            QPointF(indicator_rect.right(), indicator_rect.center().y())
                        ])
                    else:
                        # Draw down-pointing triangle for unfolded
                        triangle = QPolygonF([
                            QPointF(indicator_rect.left(), indicator_rect.top()),
                            QPointF(indicator_rect.right(), indicator_rect.top()),
                            QPointF(indicator_rect.center().x(), indicator_rect.bottom())
                        ])
                    painter.drawPolygon(triangle)
        
        # Draw AI response backgrounds
        drawn_ai_responses = set()
        
        for block_num in range(document.blockCount()):
            if block_num in self.ai_response_blocks:
                ai_info = self.ai_response_blocks[block_num]
                start_block = ai_info['start']
                end_block = ai_info['end']
                
                # Only draw each AI response once (at its start block)
                if block_num != start_block:
                    continue
                    
                # Skip if we've already drawn this AI response
                if start_block in drawn_ai_responses:
                    continue
                drawn_ai_responses.add(start_block)
                
                # Get the actual visible content blocks (skip markers)
                visible_start = start_block + 1  # Skip start marker
                visible_end = end_block - 1  # Skip end marker
                
                # Only draw if there's visible content
                if visible_start <= visible_end:
                    start_block_obj = document.findBlockByNumber(visible_start)
                    end_block_obj = document.findBlockByNumber(visible_end)
                    
                    # Get block layout coordinates
                    start_cursor = QTextCursor(start_block_obj)
                    end_cursor = QTextCursor(end_block_obj)
                    end_cursor.movePosition(QTextCursor.EndOfBlock)
                    
                    start_rect = self.cursorRect(start_cursor)
                    end_rect = self.cursorRect(end_cursor)
                    
                    # Create rectangle covering the AI response
                    ai_rect = QRectF(
                        start_rect.left() - 5,
                        start_rect.top(),
                        self.viewport().width() - 10,
                        end_rect.bottom() - start_rect.top()
                    )
                    
                    # Draw rounded rectangle background
                    painter.setBrush(QBrush(ai_response_color))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(ai_rect, 5, 5)
                
        painter.end()
        
    def on_internal_text_changed(self) -> None:
        """Handle internal text changes to update callout blocks and AI responses."""
        self.find_callout_blocks()
        self.find_ai_response_blocks()
        self.update_block_visibility()
        self.viewport().update()
        
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
                
    def update_block_visibility(self) -> None:
        """Update the visibility of all blocks based on folding state and markers."""
        document = self.document()
        
        for block_num in range(document.blockCount()):
            block = document.findBlockByNumber(block_num)
            text = block.text().strip()
            
            # Always hide AI response marker blocks
            if text in ["§§§AI_RESPONSE_START§§§", "§§§AI_RESPONSE_END§§§"]:
                block.setVisible(False)
            else:
                # Handle callout folding
                if block_num in self.callout_blocks:
                    callout_info = self.callout_blocks[block_num]
                    start_block = callout_info['start']
                    
                    # Hide non-first lines of folded callouts
                    if start_block in self.folded_callouts and block_num > start_block:
                        block.setVisible(False)
                    else:
                        block.setVisible(True)
                else:
                    # Regular blocks are always visible
                    block.setVisible(True)