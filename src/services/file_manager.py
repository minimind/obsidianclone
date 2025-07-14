"""
File management service for the Obsidian Clone application.

This module provides a centralized service for managing markdown files,
including creation, deletion, renaming, and organization of notes.
"""

import os
import shutil
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from ..utils.file_utils import (
    sanitize_filename, ensure_directory_exists, get_unique_filepath,
    create_empty_file, is_markdown_file, remove_markdown_extension,
    add_markdown_extension, normalize_path
)
from ..utils.link_utils import update_link_references
from ..utils.date_utils import get_journal_path_components, create_journal_header


class FileManager:
    """
    Manages file operations for the note-taking application.
    
    This class provides methods for:
    - Creating and organizing note files
    - Managing the notes directory structure
    - Handling file movements and renames
    - Managing trash and journal directories
    
    Attributes:
        notes_dir: Base directory for all notes
        trash_dir: Directory for deleted files
        journal_dir: Directory for journal entries
        keys_dir: Directory for key-value storage and metadata (recreated from template on startup)
        keys_template_dir: Template directory that gets copied to .keys on startup
    """
    
    def __init__(self, notes_dir: str):
        """
        Initialize the file manager.
        
        Args:
            notes_dir: Base directory for storing notes
        """
        self.notes_dir = notes_dir
        self.trash_dir = os.path.join(notes_dir, ".trash")
        self.journal_dir = os.path.join(notes_dir, ".journal")
        self.keys_dir = os.path.join(notes_dir, ".keys")
        
        # Find the keys template directory (in the project root)
        # Go up from src/services to find the project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        self.keys_template_dir = os.path.join(project_root, "keys")
        
        self._setup_directories()
    
    def _setup_directories(self) -> None:
        """Create required directories if they don't exist."""
        ensure_directory_exists(self.notes_dir)
        ensure_directory_exists(self.trash_dir)
        ensure_directory_exists(self.journal_dir)
        
        # Handle .keys directory: delete and recreate from template
        self._setup_keys_directory()
        
        # Discover available prompts
        self.available_prompts = self._discover_prompts()
        
        # Create default home.md file
        home_file = os.path.join(self.notes_dir, "home.md")
        if not os.path.exists(home_file):
            create_empty_file(home_file)
    
    def _setup_keys_directory(self) -> None:
        """
        Setup the .keys directory by copying from the keys template.
        
        This method:
        1. Removes any existing .keys directory
        2. Copies the entire keys template directory to .keys
        3. Creates an empty .keys directory if template doesn't exist
        """
        # Remove existing .keys directory if it exists
        if os.path.exists(self.keys_dir):
            try:
                shutil.rmtree(self.keys_dir)
            except Exception as e:
                print(f"Warning: Could not remove existing .keys directory: {e}")
        
        # Copy from template if it exists
        if os.path.exists(self.keys_template_dir):
            try:
                shutil.copytree(self.keys_template_dir, self.keys_dir)
            except Exception as e:
                print(f"Warning: Could not copy keys template: {e}")
                # Fallback: create empty .keys directory
                ensure_directory_exists(self.keys_dir)
        else:
            # Template doesn't exist, create empty .keys directory
            ensure_directory_exists(self.keys_dir)
    
    def _discover_prompts(self) -> List[str]:
        """
        Discover available prompt names by scanning keys template directory.
        
        Returns:
            List of prompt names (subdirectory names in keys template)
        """
        prompts = []
        
        if os.path.exists(self.keys_template_dir):
            try:
                for item in os.listdir(self.keys_template_dir):
                    item_path = os.path.join(self.keys_template_dir, item)
                    if os.path.isdir(item_path):
                        prompts.append(item)
            except Exception as e:
                print(f"Warning: Could not discover prompts: {e}")
        
        return sorted(prompts)
    
    def get_prompt_files(self, prompt_name: str) -> Dict[str, str]:
        """
        Get all files for a specific prompt.
        
        Args:
            prompt_name: Name of the prompt (subdirectory name)
            
        Returns:
            Dictionary mapping filename to file content
        """
        prompt_files = {}
        
        if prompt_name not in self.available_prompts:
            return prompt_files
        
        # Look in the runtime .keys directory
        prompt_dir = os.path.join(self.keys_dir, prompt_name)
        
        if os.path.exists(prompt_dir):
            try:
                for filename in os.listdir(prompt_dir):
                    file_path = os.path.join(prompt_dir, filename)
                    if os.path.isfile(file_path) and is_markdown_file(filename):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompt_files[filename] = f.read()
            except Exception as e:
                print(f"Warning: Could not read prompt files for {prompt_name}: {e}")
        
        return prompt_files
    
    def get_all_notes(self) -> List[Dict[str, str]]:
        """
        Get all markdown files in the notes directory.
        
        Returns:
            List of dictionaries containing file information:
            - path: Full file path
            - name: Display name (without .md extension)
            - type: 'file', 'directory', 'trash', or 'journal'
            - parent: Parent directory path
        """
        notes = []
        self._scan_directory(self.notes_dir, notes)
        return notes
    
    def _scan_directory(self, directory: str, notes_list: List[Dict[str, str]], 
                       parent_type: Optional[str] = None) -> None:
        """
        Recursively scan a directory for markdown files and subdirectories.
        
        Args:
            directory: Directory to scan
            notes_list: List to append found items to
            parent_type: Type of parent directory (for special handling)
        """
        try:
            items = sorted(os.listdir(directory))
            
            for item in items:
                full_path = os.path.join(directory, item)
                
                if os.path.isdir(full_path):
                    # Determine directory type
                    if item == ".trash" and directory == self.notes_dir:
                        dir_type = "trash"
                    elif item == ".journal" and directory == self.notes_dir:
                        dir_type = "journal"
                    elif item == ".keys" and directory == self.notes_dir:
                        dir_type = "keys"
                    else:
                        dir_type = "directory"
                    
                    notes_list.append({
                        'path': full_path,
                        'name': item,
                        'type': dir_type,
                        'parent': directory
                    })
                    
                    # Recursively scan subdirectory
                    self._scan_directory(full_path, notes_list, dir_type)
                    
                elif is_markdown_file(item):
                    notes_list.append({
                        'path': full_path,
                        'name': remove_markdown_extension(item),
                        'type': 'file',
                        'parent': directory
                    })
                    
        except PermissionError:
            pass
    
    def create_note(self, name: str, directory: Optional[str] = None, 
                   content: str = "") -> str:
        """
        Create a new note file.
        
        Args:
            name: Name for the note (without .md extension)
            directory: Directory to create the note in (defaults to notes_dir)
            content: Initial content for the note
            
        Returns:
            Path to the created note file
        """
        if directory is None:
            directory = self.notes_dir
        
        sanitized_name = sanitize_filename(name)
        filename = add_markdown_extension(sanitized_name)
        file_path = os.path.join(directory, filename)
        
        # Create directory if needed
        ensure_directory_exists(directory)
        
        # Write content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def create_note_from_link(self, link_text: str) -> str:
        """
        Create a note file from a wiki-style link.
        
        Handles subdirectory paths in the link.
        
        Args:
            link_text: Text from inside [[...]] link
            
        Returns:
            Path to the created note file
        """
        if '/' in link_text:
            # Handle subdirectory path
            parts = link_text.split('/')
            sanitized_parts = [sanitize_filename(part) for part in parts]
            
            # Create directory structure
            dir_path = self.notes_dir
            for part in sanitized_parts[:-1]:
                dir_path = os.path.join(dir_path, part)
                ensure_directory_exists(dir_path)
            
            # Create file
            filename = add_markdown_extension(sanitized_parts[-1])
            file_path = os.path.join(dir_path, filename)
        else:
            # Simple filename in root
            sanitized_name = sanitize_filename(link_text)
            filename = add_markdown_extension(sanitized_name)
            file_path = os.path.join(self.notes_dir, filename)
        
        create_empty_file(file_path)
        return file_path
    
    def delete_note(self, file_path: str) -> bool:
        """
        Move a note to the trash directory.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(file_path):
            return False
        
        filename = os.path.basename(file_path)
        trash_path = get_unique_filepath(self.trash_dir, filename)
        
        try:
            shutil.move(file_path, trash_path)
            return True
        except Exception:
            return False
    
    def delete_directory(self, dir_path: str) -> bool:
        """
        Delete an empty directory.
        
        Args:
            dir_path: Path to the directory to delete
            
        Returns:
            True if successful, False if directory not empty or error
        """
        try:
            if os.listdir(dir_path):
                return False  # Directory not empty
            os.rmdir(dir_path)
            return True
        except Exception:
            return False
    
    def rename_note(self, old_path: str, new_name: str) -> Tuple[bool, Optional[str]]:
        """
        Rename a note file.
        
        Args:
            old_path: Current path to the file
            new_name: New name for the file (without .md extension)
            
        Returns:
            Tuple of (success, new_path)
        """
        directory = os.path.dirname(old_path)
        sanitized_name = sanitize_filename(new_name)
        new_filename = add_markdown_extension(sanitized_name)
        new_path = os.path.join(directory, new_filename)
        
        # Check if target exists
        if os.path.exists(new_path) and normalize_path(new_path) != normalize_path(old_path):
            return False, None
        
        try:
            os.rename(old_path, new_path)
            return True, new_path
        except Exception:
            return False, None
    
    def rename_directory(self, old_path: str, new_name: str) -> Tuple[bool, Optional[str]]:
        """
        Rename a directory.
        
        Args:
            old_path: Current path to the directory
            new_name: New name for the directory
            
        Returns:
            Tuple of (success, new_path)
        """
        parent_dir = os.path.dirname(old_path)
        sanitized_name = sanitize_filename(new_name)
        new_path = os.path.join(parent_dir, sanitized_name)
        
        # Check if target exists
        if os.path.exists(new_path) and normalize_path(new_path) != normalize_path(old_path):
            return False, None
        
        try:
            os.rename(old_path, new_path)
            return True, new_path
        except Exception:
            return False, None
    
    def move_note(self, source_path: str, target_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Move a note to a different directory.
        
        Args:
            source_path: Current path to the file
            target_dir: Target directory path
            
        Returns:
            Tuple of (success, new_path)
        """
        filename = os.path.basename(source_path)
        dest_path = os.path.join(target_dir, filename)
        
        # Don't move to same location
        if normalize_path(source_path) == normalize_path(dest_path):
            return False, None
        
        try:
            shutil.move(source_path, dest_path)
            return True, dest_path
        except Exception:
            return False, None
    
    def update_all_links(self, old_path: str, new_path: str) -> None:
        """
        Update all link references when a file is moved or renamed.
        
        Args:
            old_path: Original file path
            new_path: New file path
        """
        # Walk through all .md files and update links
        for root, dirs, files in os.walk(self.notes_dir):
            for filename in files:
                if is_markdown_file(filename):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        updated_content = update_link_references(
                            content, old_path, new_path, self.notes_dir, sanitize_filename
                        )
                        
                        # Write back if content changed
                        if updated_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(updated_content)
                                
                    except Exception:
                        pass
    
    def create_journal_entry(self, date: Optional[datetime] = None) -> str:
        """
        Create a journal entry for the specified date.
        
        Args:
            date: Date for the journal entry (defaults to today)
            
        Returns:
            Path to the journal file
        """
        if date is None:
            date = datetime.now()
        
        year, month, day = get_journal_path_components(date)
        
        # Create journal directory structure
        journal_dir = os.path.join(self.journal_dir, year, month)
        ensure_directory_exists(journal_dir)
        
        # Create journal file
        journal_file = os.path.join(journal_dir, f"{day}.md")
        
        if not os.path.exists(journal_file):
            content = create_journal_header(date)
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return journal_file
    
    def read_note(self, file_path: str) -> str:
        """
        Read the content of a note file.
        
        Args:
            file_path: Path to the note file
            
        Returns:
            Content of the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def save_note(self, file_path: str, content: str) -> bool:
        """
        Save content to a note file.
        
        Args:
            file_path: Path to the note file
            content: Content to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    def is_special_directory(self, path: str) -> bool:
        """
        Check if a path is a special directory (trash, journal, or keys).
        
        Args:
            path: Path to check
            
        Returns:
            True if the path is trash, journal, or keys directory
        """
        norm_path = normalize_path(path)
        return (norm_path == normalize_path(self.trash_dir) or 
                norm_path == normalize_path(self.journal_dir) or
                norm_path == normalize_path(self.keys_dir))
    
    def is_in_trash(self, path: str) -> bool:
        """
        Check if a path is inside the trash directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path is in trash
        """
        norm_path = normalize_path(path)
        norm_trash = normalize_path(self.trash_dir)
        return norm_path.startswith(norm_trash)