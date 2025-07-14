"""
Link parsing and formatting utilities for the Obsidian Clone application.

This module provides functions for parsing, formatting, and manipulating
wiki-style [[page]] links within markdown content.
"""

import re
import os
from typing import List, Tuple, Optional, Dict, Any

# Regular expression pattern for wiki-style links
LINK_PATTERN = r'\[\[([^\]]+)\]\]'


def find_all_links(text: str) -> List[Tuple[int, int, str]]:
    """
    Find all wiki-style links in the given text.
    
    Args:
        text: Text to search for links
        
    Returns:
        List of tuples containing (start_pos, end_pos, link_text)
    """
    links = []
    for match in re.finditer(LINK_PATTERN, text):
        links.append((match.start(), match.end(), match.group(1)))
    return links


def extract_link_text(link: str) -> str:
    """
    Extract the text from a wiki-style link.
    
    Args:
        link: Full link text including brackets (e.g., "[[page]]")
        
    Returns:
        Link text without brackets (e.g., "page")
    """
    match = re.match(LINK_PATTERN, link)
    if match:
        return match.group(1)
    return link


def create_wiki_link(text: str) -> str:
    """
    Create a wiki-style link from plain text.
    
    Args:
        text: Text to convert to a link
        
    Returns:
        Wiki-style link (e.g., "[[text]]")
    """
    return f"[[{text}]]"


def link_to_filepath(link_text: str, base_dir: str, sanitize_func) -> str:
    """
    Convert a link text to a file path.
    
    Handles both simple filenames and subdirectory paths.
    
    Args:
        link_text: Text inside the [[...]] link
        base_dir: Base directory for notes
        sanitize_func: Function to sanitize filenames
        
    Returns:
        Full file path for the linked note
    """
    if '/' in link_text:
        # Handle subdirectory path
        parts = link_text.split('/')
        # Sanitize each part
        sanitized_parts = [sanitize_func(part) for part in parts]
        # Add .md to the last part
        sanitized_parts[-1] = f"{sanitized_parts[-1]}.md"
        file_path = os.path.join(base_dir, *sanitized_parts)
    else:
        # Simple filename in root
        sanitized_name = sanitize_func(link_text)
        filename = f"{sanitized_name}.md"
        file_path = os.path.join(base_dir, filename)
    
    return file_path


def filepath_to_link(file_path: str, base_dir: str) -> str:
    """
    Convert a file path to link text.
    
    Args:
        file_path: Full path to the markdown file
        base_dir: Base directory for notes
        
    Returns:
        Link text suitable for wiki-style links
    """
    # Get relative path
    rel_path = os.path.relpath(file_path, base_dir)
    
    # Convert to forward slashes
    rel_path = rel_path.replace(os.sep, '/')
    
    # Remove .md extension
    if rel_path.endswith('.md'):
        rel_path = rel_path[:-3]
    
    # Convert underscores back to spaces in filename part only
    parts = rel_path.split('/')
    parts[-1] = parts[-1].replace('_', ' ')
    
    return '/'.join(parts)


def update_link_references(content: str, old_path: str, new_path: str, 
                          base_dir: str, sanitize_func) -> str:
    """
    Update all link references in content when a file is moved or renamed.
    
    Args:
        content: Markdown content containing links
        old_path: Original file path
        new_path: New file path
        base_dir: Base directory for notes
        sanitize_func: Function to sanitize filenames
        
    Returns:
        Updated content with corrected links
    """
    updated_content = content
    
    # Find all links in the content
    for match in re.finditer(LINK_PATTERN, content):
        link_text = match.group(1)
        
        # Convert link to file path
        link_file_path = link_to_filepath(link_text, base_dir, sanitize_func)
        
        # Normalize paths for comparison
        link_file_path = os.path.normpath(link_file_path)
        old_path_norm = os.path.normpath(old_path)
        
        # If this link pointed to the moved file, update it
        if link_file_path == old_path_norm:
            # Create new link text
            new_link_text = filepath_to_link(new_path, base_dir)
            
            # Replace the old link with the new one
            old_link_full = match.group(0)
            new_link = create_wiki_link(new_link_text)
            updated_content = updated_content.replace(old_link_full, new_link)
    
    return updated_content


def remove_link_brackets(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Remove wiki-style link brackets for display purposes.
    
    Args:
        text: Text containing wiki-style links
        
    Returns:
        Tuple of (text without brackets, list of link positions)
        Link positions contain {'start': int, 'end': int, 'text': str}
    """
    result_text = ""
    link_positions = []
    last_end = 0
    
    for match in re.finditer(LINK_PATTERN, text):
        # Add text before the match
        result_text += text[last_end:match.start()]
        
        # Record link position in result text
        link_start = len(result_text)
        link_text = match.group(1)
        result_text += link_text
        link_end = len(result_text)
        
        link_positions.append({
            'start': link_start,
            'end': link_end,
            'text': link_text,
            'original_start': match.start(),
            'original_end': match.end()
        })
        
        last_end = match.end()
    
    # Add remaining text
    result_text += text[last_end:]
    
    return result_text, link_positions


def is_position_in_link(position: int, links: List[Tuple[int, int, str]]) -> Optional[str]:
    """
    Check if a position falls within any link in the list.
    
    Args:
        position: Text position to check
        links: List of link tuples from find_all_links
        
    Returns:
        Link text if position is within a link, None otherwise
    """
    for start, end, link_text in links:
        if start <= position <= end:
            return link_text
    return None