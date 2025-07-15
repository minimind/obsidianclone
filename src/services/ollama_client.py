"""
Ollama API client for the Obsidian Clone application.

This module provides functionality to interact with Ollama's local LLM API
for processing prompts and generating responses.
"""

import json
import urllib.request
import urllib.parse
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Optional, Any
from urllib.error import URLError, HTTPError


class OllamaClient:
    """
    Client for interacting with Ollama API.
    
    This class provides methods to send prompts to Ollama and receive responses.
    It handles the HTTP communication and response parsing.
    
    Attributes:
        base_url: Base URL for the Ollama API
        default_model: Default model to use for completions
        timeout: Request timeout in seconds
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", 
                 default_model: str = "llama3.1:8b", timeout: int = 30):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for the Ollama API
            default_model: Default model to use for completions
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self.timeout = timeout
        
        # Setup logging to temp directory
        log_dir = tempfile.gettempdir()
        log_file = os.path.join(log_dir, f"ollama_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Configure logger
        self.logger = logging.getLogger(f"OllamaClient_{id(self)}")
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
        
        # Store log file path for easy access
        self.log_file_path = log_file
        
        self.logger.info(f"Ollama logging initialized. Log file: {log_file}")
        print(f"Ollama prompts and responses will be logged to: {log_file}")
    
    def is_available(self) -> bool:
        """
        Check if Ollama is available and responding.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except (URLError, HTTPError, Exception):
            return False
    
    def generate_completion(self, prompt: str, model: Optional[str] = None, 
                          stream: bool = False) -> Optional[str]:
        """
        Generate a completion using Ollama.
        
        Args:
            prompt: The prompt to send to the model
            model: Model to use (defaults to default_model)
            stream: Whether to use streaming (not implemented in this version)
            
        Returns:
            Generated response text, or None if request failed
        """
        if model is None:
            model = self.default_model
        
        # Prepare the request data
        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        try:
            # Convert data to JSON
            json_data = json.dumps(data).encode('utf-8')
            
            # Create the request
            url = f"{self.base_url}/api/generate"
            req = urllib.request.Request(
                url,
                data=json_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Send the request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    response_data = response.read().decode('utf-8')
                    
                    if stream:
                        # Handle streaming response (multiple JSON objects)
                        full_response = ""
                        for line in response_data.strip().split('\n'):
                            if line:
                                try:
                                    json_obj = json.loads(line)
                                    if 'response' in json_obj:
                                        full_response += json_obj['response']
                                except json.JSONDecodeError:
                                    continue
                        return full_response
                    else:
                        # Handle single response
                        try:
                            json_response = json.loads(response_data)
                            return json_response.get('response', '')
                        except json.JSONDecodeError:
                            return None
                else:
                    print(f"Ollama API error: HTTP {response.status}")
                    return None
                    
        except URLError as e:
            print(f"Ollama connection error: {e}")
            return None
        except HTTPError as e:
            print(f"Ollama HTTP error: {e}")
            return None
        except Exception as e:
            print(f"Ollama request error: {e}")
            return None
    
    def process_prompt_with_files(self, user_text: str, prompt_files: Dict[str, str], 
                                 model: Optional[str] = None) -> Optional[str]:
        """
        Process user text using prompt file.
        
        Uses the single prompt file as the system prompt and sends the user text
        for processing.
        
        Args:
            user_text: User's input text to process
            prompt_files: Dictionary with single prompt file (filename -> content)
            model: Model to use (defaults to default_model)
            
        Returns:
            Generated response, or None if processing failed
        """
        self.logger.info("="*80)
        self.logger.info("NEW PROMPT REQUEST")
        self.logger.info("="*80)
        
        # Get the system prompt from the single file
        system_prompt = ""
        
        # There should be exactly one file in prompt_files
        for filename, content in prompt_files.items():
            self.logger.info(f"\n--- SYSTEM PROMPT (from {filename}) ---")
            self.logger.info(content)
            self.logger.info("--- END SYSTEM PROMPT ---\n")
            system_prompt = content
            break  # Only one file expected
        
        # Log user text
        self.logger.info("\n--- USER TEXT ---")
        self.logger.info(user_text)
        self.logger.info("--- END USER TEXT ---\n")
        
        # Combine system prompt and user text
        full_prompt = f"{system_prompt}\n\nUser text to process:\n{user_text}"
        
        # Log the full combined prompt
        self.logger.info("\n--- FULL COMBINED PROMPT SENT TO OLLAMA ---")
        self.logger.info(full_prompt)
        self.logger.info("--- END FULL PROMPT ---\n")
        
        # Call generate_completion and log the response
        response = self.generate_completion(full_prompt, model)
        
        if response:
            self.logger.info("\n--- OLLAMA RESPONSE ---")
            self.logger.info(response)
            self.logger.info("--- END OLLAMA RESPONSE ---\n")
        else:
            self.logger.error("OLLAMA RESPONSE: None (request failed)")
        
        self.logger.info("="*80)
        self.logger.info("END OF REQUEST")
        self.logger.info("="*80 + "\n\n")
        
        return response
    
    def get_available_models(self) -> list:
        """
        Get list of available models from Ollama.
        
        Returns:
            List of available model names, empty list if request failed
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    response_data = response.read().decode('utf-8')
                    json_response = json.loads(response_data)
                    
                    models = []
                    if 'models' in json_response:
                        for model in json_response['models']:
                            if 'name' in model:
                                models.append(model['name'])
                    
                    return models
                else:
                    return []
                    
        except Exception as e:
            print(f"Error getting available models: {e}")
            return []
    
    def get_log_file_path(self) -> str:
        """
        Get the path to the current log file.
        
        Returns:
            Path to the log file where prompts and responses are logged
        """
        return self.log_file_path