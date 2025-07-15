"""
Prompt processing service for the Obsidian Clone application.

This module handles detection of @#promptname patterns in text and processes
them using Ollama with the corresponding prompt files.
"""

import re
from typing import List, Tuple, Optional, Dict
from .ollama_client import OllamaClient
from .file_manager import FileManager


class PromptProcessor:
    """
    Service for processing @#promptname patterns in text.
    
    This class detects prompt patterns in text, extracts the relevant prompt files,
    and sends them to Ollama for processing.
    
    Attributes:
        file_manager: FileManager instance for accessing prompt files
        ollama_client: OllamaClient instance for API communication
        prompt_pattern: Regex pattern for detecting @#promptname
    """
    
    def __init__(self, file_manager: FileManager, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize the prompt processor.
        
        Args:
            file_manager: FileManager instance
            ollama_client: OllamaClient instance (creates default if None)
        """
        self.file_manager = file_manager
        self.ollama_client = ollama_client or OllamaClient()
        # Pattern matches @#followed by word characters (letters, numbers, underscore)
        self.prompt_pattern = re.compile(r'@#(\w+)')
    
    def find_prompt_patterns(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Find all @#promptname patterns in text.
        
        Args:
            text: Text to search for patterns
            
        Returns:
            List of tuples (start_pos, end_pos, prompt_name)
        """
        patterns = []
        for match in self.prompt_pattern.finditer(text):
            prompt_name = match.group(1)
            # Only include if it's a valid prompt name
            if prompt_name in self.file_manager.available_prompts:
                patterns.append((match.start(), match.end(), prompt_name))
        return patterns
    
    def extract_user_text_for_prompt(self, text: str, prompt_start: int, prompt_end: int) -> str:
        """
        Extract the user text that should be processed by the prompt.
        
        This method extracts the text preceding the @#promptname pattern,
        typically the current paragraph or sentence.
        
        Args:
            text: Full text content
            prompt_start: Start position of the @#promptname pattern
            prompt_end: End position of the @#promptname pattern
            
        Returns:
            Extracted user text to be processed
        """
        # Get text before the prompt pattern
        text_before = text[:prompt_start].strip()
        
        # Find the start of the current paragraph/section
        # Look for double newlines, or start of text
        last_double_newline = text_before.rfind('\n\n')
        if last_double_newline != -1:
            user_text = text_before[last_double_newline:].strip()
        else:
            # If no double newline found, use the last line(s)
            lines = text_before.split('\n')
            if len(lines) > 3:
                # Take last 3 lines to provide some context
                user_text = '\n'.join(lines[-3:]).strip()
            else:
                user_text = text_before
        
        return user_text
    
    def process_prompt(self, prompt_name: str, user_text: str) -> Optional[str]:
        """
        Process user text using the specified prompt.
        
        Args:
            prompt_name: Name of the prompt to use
            user_text: User text to process
            
        Returns:
            Generated response from Ollama, or None if processing failed
        """
        if not self.ollama_client.is_available():
            return "Error: Ollama is not available. Please ensure Ollama is running."
        
        # Get prompt file
        prompt_files = self.file_manager.get_prompt_files(prompt_name)
        if not prompt_files:
            return f"Error: No prompt file found for '{prompt_name}'"
        
        # Process with Ollama
        response = self.ollama_client.process_prompt_with_files(user_text, prompt_files)
        
        if response is None:
            return f"Error: Failed to get response from Ollama for prompt '{prompt_name}'"
        
        return response
    
    def process_text_with_prompts(self, text: str) -> Dict[str, any]:
        """
        Process all prompt patterns found in text.
        
        Args:
            text: Text containing potential @#promptname patterns
            
        Returns:
            Dictionary with processing results:
            - 'patterns': List of found patterns
            - 'results': Dictionary mapping pattern positions to results
            - 'errors': List of any errors encountered
        """
        patterns = self.find_prompt_patterns(text)
        results = {}
        errors = []
        
        for start_pos, end_pos, prompt_name in patterns:
            try:
                # Extract user text for this prompt
                user_text = self.extract_user_text_for_prompt(text, start_pos, end_pos)
                
                if not user_text.strip():
                    errors.append(f"No user text found for prompt @#{prompt_name} at position {start_pos}")
                    continue
                
                # Process the prompt
                response = self.process_prompt(prompt_name, user_text)
                
                if response:
                    results[start_pos] = {
                        'prompt_name': prompt_name,
                        'user_text': user_text,
                        'response': response,
                        'pattern_start': start_pos,
                        'pattern_end': end_pos
                    }
                else:
                    errors.append(f"Failed to process prompt @#{prompt_name} at position {start_pos}")
                    
            except Exception as e:
                errors.append(f"Error processing @#{prompt_name} at position {start_pos}: {str(e)}")
        
        return {
            'patterns': patterns,
            'results': results,
            'errors': errors
        }
    
    def get_available_prompts(self) -> List[str]:
        """
        Get list of available prompt names.
        
        Returns:
            List of available prompt names
        """
        return self.file_manager.available_prompts.copy()
    
    def format_response_for_insertion(self, response: str, prompt_name: str) -> str:
        """
        Format the Ollama response for insertion into the document.
        
        Creates a foldable thinking section and a highlighted user section.
        
        Args:
            response: Raw response from Ollama
            prompt_name: Name of the prompt that generated the response
            
        Returns:
            Formatted response text with special markers
        """
        # Extract content between <TOUSER> tags and everything else
        touser_pattern = re.compile(r'<TOUSER>(.*?)</TOUSER>', re.DOTALL | re.IGNORECASE)
        touser_match = touser_pattern.search(response)
        
        if touser_match:
            # Get content inside TOUSER tags
            user_content = touser_match.group(1).strip()
            # Get everything outside TOUSER tags (thinking content)
            thinking_content = touser_pattern.sub('', response).strip()
        else:
            # If no TOUSER tags, treat entire response as user content
            user_content = response.strip()
            thinking_content = ""
        
        # Format the response with special markers for the editor
        formatted_parts = []
        
        # Add thinking section as a foldable callout
        if thinking_content:
            formatted_parts.append("\n\n> thinking...")
            # Add each line of thinking content with > prefix
            for line in thinking_content.split('\n'):
                if line.strip():  # Skip empty lines
                    formatted_parts.append(f"> {line}")
        
        # Add user content in a special block for green background
        if user_content:
            formatted_parts.append("\n\n§§§AI_RESPONSE_START§§§")
            formatted_parts.append(user_content)
            formatted_parts.append("§§§AI_RESPONSE_END§§§")
        
        return '\n'.join(formatted_parts)