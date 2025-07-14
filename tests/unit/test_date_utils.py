"""
Unit tests for date utility functions.
"""

import unittest
from datetime import datetime

from src.utils.date_utils import (
    get_ordinal_suffix, format_journal_date,
    get_journal_path_components, create_journal_header
)


class TestDateUtils(unittest.TestCase):
    """Test cases for date utility functions."""
    
    def test_get_ordinal_suffix(self):
        """Test ordinal suffix generation."""
        self.assertEqual(get_ordinal_suffix(1), 'st')
        self.assertEqual(get_ordinal_suffix(2), 'nd')
        self.assertEqual(get_ordinal_suffix(3), 'rd')
        self.assertEqual(get_ordinal_suffix(4), 'th')
        self.assertEqual(get_ordinal_suffix(11), 'th')
        self.assertEqual(get_ordinal_suffix(12), 'th')
        self.assertEqual(get_ordinal_suffix(13), 'th')
        self.assertEqual(get_ordinal_suffix(21), 'st')
        self.assertEqual(get_ordinal_suffix(22), 'nd')
        self.assertEqual(get_ordinal_suffix(23), 'rd')
    
    def test_format_journal_date(self):
        """Test journal date formatting."""
        test_date = datetime(2025, 5, 29)  # Thursday, May 29, 2025
        result = format_journal_date(test_date)
        self.assertEqual(result, "Thursday 29th May 2025")
        
        test_date = datetime(2025, 1, 1)  # Wednesday, January 1, 2025
        result = format_journal_date(test_date)
        self.assertEqual(result, "Wednesday 1st January 2025")
    
    def test_get_journal_path_components(self):
        """Test journal path component extraction."""
        test_date = datetime(2025, 5, 29)
        year, month, day = get_journal_path_components(test_date)
        
        self.assertEqual(year, "2025")
        self.assertEqual(month, "05")
        self.assertEqual(day, "29")
    
    def test_create_journal_header(self):
        """Test journal header creation."""
        test_date = datetime(2025, 5, 29)
        header = create_journal_header(test_date)
        expected = "# Thursday 29th May 2025\n\n"
        self.assertEqual(header, expected)


if __name__ == '__main__':
    unittest.main()