"""
Ollama API client for the Obsidian Clone application.

This module provides functionality to interact with Ollama's local LLM API
for processing prompts and generating responses.
"""

import json
import urllib.request
import urllib.parse
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
        Process user text using prompt files.
        
        Combines the prompt files into a system prompt and sends the user text
        for processing.
        
        Args:
            user_text: User's input text to process
            prompt_files: Dictionary of prompt files (filename -> content)
            model: Model to use (defaults to default_model)
            
        Returns:
            Generated response, or None if processing failed
        """
        # Combine prompt files into a system prompt
        system_prompt_parts = []
        
        # Add system.md content first if it exists
        if 'system.md' in prompt_files:
            system_prompt_parts.append(prompt_files['system.md'])
        
        # Add assistant.md content if it exists
        if 'assistant.md' in prompt_files:
            system_prompt_parts.append(prompt_files['assistant.md'])
        
        # Add any other prompt files
        for filename, content in prompt_files.items():
            if filename not in ['system.md', 'assistant.md']:
                system_prompt_parts.append(content)
        
        # Combine system prompt and user text
        system_prompt = "\n\n".join(system_prompt_parts)
        full_prompt = f"{system_prompt}\n\nUser text to process:\n{user_text}"
        
        return self.generate_completion(full_prompt, model)
    
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