"""
Date and time utility functions for the Obsidian Clone application.

This module provides functions for date formatting and journal entry creation.
"""

from datetime import datetime
from typing import Tuple


def get_ordinal_suffix(day: int) -> str:
    """
    Get ordinal suffix for a day number (1st, 2nd, 3rd, 4th, etc.).
    
    Args:
        day: Day number (1-31)
        
    Returns:
        Ordinal suffix ('st', 'nd', 'rd', or 'th')
    """
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return suffix


def format_journal_date(date: datetime) -> str:
    """
    Format a date for journal entry header.
    
    Format: "Thursday 29th May 2025"
    
    Args:
        date: Date to format
        
    Returns:
        Formatted date string
    """
    day_of_week = date.strftime("%A")
    day_num = date.day
    month_name = date.strftime("%B")
    year_str = date.strftime("%Y")
    suffix = get_ordinal_suffix(day_num)
    
    return f"{day_of_week} {day_num}{suffix} {month_name} {year_str}"


def get_journal_path_components(date: datetime) -> Tuple[str, str, str]:
    """
    Get the path components for a journal entry.
    
    Args:
        date: Date for the journal entry
        
    Returns:
        Tuple of (year, month, day) as strings
    """
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")
    
    return year, month, day


def create_journal_header(date: datetime) -> str:
    """
    Create the markdown header for a new journal entry.
    
    Args:
        date: Date for the journal entry
        
    Returns:
        Markdown header string
    """
    date_header = format_journal_date(date)
    return f"# {date_header}\n\n"