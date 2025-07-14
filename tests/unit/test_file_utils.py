"""
Unit tests for file utility functions.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch

from src.utils.file_utils import (
    sanitize_filename, ensure_directory_exists, get_unique_filepath,
    get_relative_path, normalize_path, expand_user_path, create_empty_file,
    is_markdown_file, remove_markdown_extension, add_markdown_extension
)


class TestFileUtils(unittest.TestCase):
    """Test cases for file utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        self.assertEqual(sanitize_filename("hello world"), "hello_world")
        self.assertEqual(sanitize_filename("test\nfile"), "test_file")
        self.assertEqual(sanitize_filename("  spaced  "), "spaced")
        self.assertEqual(sanitize_filename("multiple   spaces"), "multiple_spaces")
    
    def test_ensure_directory_exists(self):
        """Test directory creation."""
        test_path = os.path.join(self.test_dir, "test_subdir")
        self.assertFalse(os.path.exists(test_path))
        
        ensure_directory_exists(test_path)
        self.assertTrue(os.path.exists(test_path))
        self.assertTrue(os.path.isdir(test_path))
    
    def test_get_unique_filepath(self):
        """Test unique filepath generation."""
        # Create a test file
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # Get unique filepath
        unique_path = get_unique_filepath(self.test_dir, "test.txt")
        expected_path = os.path.join(self.test_dir, "test_1.txt")
        self.assertEqual(unique_path, expected_path)
    
    def test_get_relative_path(self):
        """Test relative path calculation."""
        base_dir = "/home/user/notes"
        file_path = "/home/user/notes/subdir/file.md"
        
        rel_path = get_relative_path(file_path, base_dir)
        self.assertEqual(rel_path, "subdir/file.md")
    
    def test_normalize_path(self):
        """Test path normalization."""
        test_path = "/home/user//notes/./file.md"
        normalized = normalize_path(test_path)
        expected = os.path.normpath(test_path)
        self.assertEqual(normalized, expected)
    
    @patch('os.path.expanduser')
    def test_expand_user_path(self, mock_expanduser):
        """Test user path expansion."""
        mock_expanduser.return_value = "/home/user/Documents"
        result = expand_user_path("~/Documents")
        mock_expanduser.assert_called_once_with("~/Documents")
        self.assertEqual(result, "/home/user/Documents")
    
    def test_create_empty_file(self):
        """Test empty file creation."""
        test_file = os.path.join(self.test_dir, "empty.md")
        self.assertFalse(os.path.exists(test_file))
        
        create_empty_file(test_file)
        self.assertTrue(os.path.exists(test_file))
        
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "")
    
    def test_is_markdown_file(self):
        """Test markdown file detection."""
        self.assertTrue(is_markdown_file("test.md"))
        self.assertTrue(is_markdown_file("test.MD"))
        self.assertFalse(is_markdown_file("test.txt"))
        self.assertFalse(is_markdown_file("test"))
    
    def test_remove_markdown_extension(self):
        """Test markdown extension removal."""
        self.assertEqual(remove_markdown_extension("test.md"), "test")
        self.assertEqual(remove_markdown_extension("test.MD"), "test")
        self.assertEqual(remove_markdown_extension("test.txt"), "test.txt")
        self.assertEqual(remove_markdown_extension("test"), "test")
    
    def test_add_markdown_extension(self):
        """Test markdown extension addition."""
        self.assertEqual(add_markdown_extension("test"), "test.md")
        self.assertEqual(add_markdown_extension("test.md"), "test.md")
        self.assertEqual(add_markdown_extension("test.MD"), "test.MD")


if __name__ == '__main__':
    unittest.main()