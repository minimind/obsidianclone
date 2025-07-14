"""
File utility functions for the Obsidian Clone application.

This module provides utility functions for file and directory operations,
including sanitization, path manipulation, and file system operations.
"""

import os
import re
from typing import Optional, Tuple


def sanitize_filename(name: str) -> str:
    """
    Convert spaces and newlines to underscores in filenames.
    
    Args:
        name: The filename to sanitize
        
    Returns:
        Sanitized filename with whitespace replaced by underscores
    """
    # Replace spaces, newlines, and other whitespace with underscores
    sanitized = re.sub(r'\s+', '_', name.strip())
    return sanitized


def ensure_directory_exists(directory_path: str) -> None:
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory_path: Path to the directory to create
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)


def get_unique_filepath(directory: str, filename: str) -> str:
    """
    Generate a unique filepath by appending a counter if the file already exists.
    
    Args:
        directory: Directory path
        filename: Desired filename
        
    Returns:
        Unique filepath that doesn't conflict with existing files
    """
    filepath = os.path.join(directory, filename)
    
    if not os.path.exists(filepath):
        return filepath
    
    # Split filename and extension
    base, ext = os.path.splitext(filename)
    counter = 1
    
    while os.path.exists(filepath):
        new_filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(directory, new_filename)
        counter += 1
    
    return filepath


def get_relative_path(file_path: str, base_dir: str) -> str:
    """
    Get the relative path from base directory to file.
    
    Args:
        file_path: Full path to the file
        base_dir: Base directory to calculate relative path from
        
    Returns:
        Relative path with forward slashes
    """
    rel_path = os.path.relpath(file_path, base_dir)
    # Convert to forward slashes for consistency
    return rel_path.replace(os.sep, '/')


def normalize_path(path: str) -> str:
    """
    Normalize a file path for consistent comparison.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path
    """
    return os.path.normpath(path)


def expand_user_path(path: str) -> str:
    """
    Expand ~ to user home directory in path.
    
    Args:
        path: Path that may contain ~
        
    Returns:
        Path with ~ expanded to full home directory
    """
    return os.path.expanduser(path)


def create_empty_file(file_path: str) -> None:
    """
    Create an empty file at the specified path.
    
    Creates parent directories if they don't exist.
    
    Args:
        file_path: Path where the file should be created
    """
    directory = os.path.dirname(file_path)
    if directory:
        ensure_directory_exists(directory)
    
    # Create empty file
    open(file_path, 'a').close()


def is_markdown_file(filename: str) -> bool:
    """
    Check if a filename represents a markdown file.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if the file has a .md extension
    """
    return filename.lower().endswith('.md')


def remove_markdown_extension(filename: str) -> str:
    """
    Remove .md extension from a filename if present.
    
    Args:
        filename: Filename that may have .md extension
        
    Returns:
        Filename without .md extension
    """
    if filename.lower().endswith('.md'):
        return filename[:-3]
    return filename


def add_markdown_extension(filename: str) -> str:
    """
    Add .md extension to a filename if not present.
    
    Args:
        filename: Filename that may need .md extension
        
    Returns:
        Filename with .md extension
    """
    if not filename.lower().endswith('.md'):
        return f"{filename}.md"
    return filename