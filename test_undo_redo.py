#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt

# Import our custom text editor
from obsidian_clone import ClickableTextEdit

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_read_only = False  # Always in edit mode for testing
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Undo/Redo Test")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Instructions
        instructions = QLabel("Test Instructions:\n"
                            "1. Type some text\n"
                            "2. Press Ctrl+Z to undo\n"
                            "3. Press Ctrl+Y or Ctrl+Shift+Z to redo\n"
                            "4. Check console for debug output")
        layout.addWidget(instructions)
        
        # Text editor
        self.editor = ClickableTextEdit(self)
        self.editor.setPlainText("Initial text")
        self.editor.save_undo_state()
        layout.addWidget(self.editor)
        
        # Debug buttons
        debug_btn = QPushButton("Show Stack Sizes")
        debug_btn.clicked.connect(self.show_stack_sizes)
        layout.addWidget(debug_btn)
        
    def show_stack_sizes(self):
        print(f"Undo stack size: {len(self.editor.undo_stack)}")
        print(f"Redo stack size: {len(self.editor.redo_stack)}")
        print(f"Current text: '{self.editor.toPlainText()}'")
        
    def format_links(self):
        pass  # Stub method
        
    def format_for_read_only(self):
        pass  # Stub method

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())