"""
Unit tests for link utility functions.
"""

import unittest
import os
from unittest.mock import patch

from src.utils.link_utils import (
    find_all_links, extract_link_text, create_wiki_link,
    link_to_filepath, filepath_to_link, update_link_references,
    remove_link_brackets, is_position_in_link
)


class TestLinkUtils(unittest.TestCase):
    """Test cases for link utility functions."""
    
    def test_find_all_links(self):
        """Test finding all links in text."""
        text = "This is [[link1]] and [[link2]] with text."
        links = find_all_links(text)
        
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0], (8, 17, 'link1'))
        self.assertEqual(links[1], (22, 31, 'link2'))
    
    def test_extract_link_text(self):
        """Test extracting link text."""
        self.assertEqual(extract_link_text("[[test page]]"), "test page")
        self.assertEqual(extract_link_text("test page"), "test page")
    
    def test_create_wiki_link(self):
        """Test creating wiki-style links."""
        self.assertEqual(create_wiki_link("test page"), "[[test page]]")
    
    def test_link_to_filepath(self):
        """Test converting link text to file path."""
        def mock_sanitize(text):
            return text.replace(' ', '_')
        
        base_dir = "/notes"
        
        # Simple link
        result = link_to_filepath("test page", base_dir, mock_sanitize)
        expected = "/notes/test_page.md"
        self.assertEqual(result, expected)
        
        # Subdirectory link
        result = link_to_filepath("folder/test page", base_dir, mock_sanitize)
        expected = "/notes/folder/test_page.md"
        self.assertEqual(result, expected)
    
    def test_filepath_to_link(self):
        """Test converting file path to link text."""
        base_dir = "/notes"
        file_path = "/notes/folder/test_file.md"
        
        result = filepath_to_link(file_path, base_dir)
        self.assertEqual(result, "folder/test file")
    
    def test_update_link_references(self):
        """Test updating link references when files move."""
        def mock_sanitize(text):
            return text.replace(' ', '_')
        
        content = "See [[old page]] for details."
        old_path = "/notes/old_page.md"
        new_path = "/notes/new_page.md"
        base_dir = "/notes"
        
        result = update_link_references(content, old_path, new_path, base_dir, mock_sanitize)
        self.assertEqual(result, "See [[new page]] for details.")
    
    def test_remove_link_brackets(self):
        """Test removing link brackets for display."""
        text = "This is [[link1]] and [[link2]] text."
        result_text, positions = remove_link_brackets(text)
        
        self.assertEqual(result_text, "This is link1 and link2 text.")
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0]['text'], 'link1')
        self.assertEqual(positions[1]['text'], 'link2')
    
    def test_is_position_in_link(self):
        """Test checking if position is within a link."""
        links = [(8, 17, 'link1'), (22, 31, 'link2')]
        
        self.assertEqual(is_position_in_link(10, links), 'link1')
        self.assertEqual(is_position_in_link(25, links), 'link2')
        self.assertIsNone(is_position_in_link(5, links))
        self.assertIsNone(is_position_in_link(35, links))


if __name__ == '__main__':
    unittest.main()