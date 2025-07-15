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
import re
from datetime import datetime
from typing import Dict, Optional, Any, List
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
    
    def chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None, 
                       stream: bool = False) -> Optional[str]:
        """
        Generate a chat completion using Ollama's chat API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
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
            "messages": messages,
            "stream": stream
        }
        
        try:
            # Convert data to JSON
            json_data = json.dumps(data).encode('utf-8')
            
            # Create the request
            url = f"{self.base_url}/api/chat"
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
                                    if 'message' in json_obj and 'content' in json_obj['message']:
                                        full_response += json_obj['message']['content']
                                except json.JSONDecodeError:
                                    continue
                        return full_response
                    else:
                        # Handle single response
                        try:
                            json_response = json.loads(response_data)
                            if 'message' in json_response and 'content' in json_response['message']:
                                return json_response['message']['content']
                            return None
                        except json.JSONDecodeError:
                            return None
                else:
                    print(f"Ollama Chat API error: HTTP {response.status}")
                    return None
                    
        except URLError as e:
            print(f"Ollama chat connection error: {e}")
            return None
        except HTTPError as e:
            print(f"Ollama chat HTTP error: {e}")
            return None
        except Exception as e:
            print(f"Ollama chat request error: {e}")
            return None
    
    def process_prompt_with_files(self, user_text: str, prompt_files: Dict[str, str], 
                                 model: Optional[str] = None) -> Optional[str]:
        """
        Process user text using prompt file with chat API.
        
        Uses the single prompt file as the system prompt and sends the user text
        for processing using the chat API with proper role handling.
        
        Args:
            user_text: User's input text to process
            prompt_files: Dictionary with single prompt file (filename -> content)
            model: Model to use (defaults to default_model)
            
        Returns:
            Generated response, or None if processing failed
        """
        self.logger.info("="*80)
        self.logger.info("NEW CHAT PROMPT REQUEST")
        self.logger.info("="*80)
        
        # Parse the content to separate user and assistant messages
        messages = self._parse_text_into_messages(user_text, prompt_files)
        
        # Log message summary
        role_counts = {}
        for msg in messages:
            role_counts[msg['role']] = role_counts.get(msg['role'], 0) + 1
        
        summary = ", ".join([f"{count} {role.upper()}" for role, count in role_counts.items()])
        self.logger.info(f"\nSENDING {len(messages)} MESSAGES TO OLLAMA: {summary}")
        
        # Log all messages with roles
        for i, message in enumerate(messages):
            role = message['role'].upper()
            self.logger.info(f"\n--- MESSAGE {i+1} (ROLE: {role}) ---")
            self.logger.info(message['content'])
            self.logger.info(f"--- END MESSAGE {i+1} (ROLE: {role}) ---\n")
        
        # Call chat_completion and log the response
        response = self.chat_completion(messages, model)
        
        if response:
            self.logger.info("\n--- OLLAMA CHAT RESPONSE ---")
            self.logger.info(response)
            self.logger.info("--- END OLLAMA CHAT RESPONSE ---\n")
        else:
            self.logger.error("OLLAMA CHAT RESPONSE: None (request failed)")
        
        self.logger.info("="*80)
        self.logger.info("END OF CHAT REQUEST")
        self.logger.info("="*80 + "\n\n")
        
        return response
    
    def _parse_text_into_messages(self, text: str, prompt_files: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Parse text into messages with appropriate roles.
        
        Args:
            text: The text content to parse
            prompt_files: Dictionary with prompt file content
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        messages = []
        
        # Add system message from prompt file
        for filename, content in prompt_files.items():
            messages.append({
                "role": "system",
                "content": content.strip()
            })
            break  # Only one file expected
        
        # Split text by AI response markers to identify user vs assistant content
        ai_response_pattern = re.compile(
            r'§§§AI_RESPONSE_START§§§(.*?)§§§AI_RESPONSE_END§§§', 
            re.DOTALL
        )
        
        # Find all AI responses in the text
        ai_responses = []
        for match in ai_response_pattern.finditer(text):
            ai_responses.append((match.start(), match.end(), match.group(1).strip()))
        
        # Process text sequentially, alternating between user and assistant
        current_pos = 0
        
        if ai_responses:
            # Process conversation with AI responses
            for ai_start, ai_end, ai_content in ai_responses:
                # Add user content before this AI response
                user_content = text[current_pos:ai_start].strip()
                if user_content:
                    # Remove any @#prompt patterns from user content
                    user_content = re.sub(r'@#\w+', '', user_content).strip()
                    if user_content:
                        messages.append({
                            "role": "user",
                            "content": user_content
                        })
                
                # Add AI response
                if ai_content:
                    messages.append({
                        "role": "assistant",
                        "content": ai_content
                    })
                
                current_pos = ai_end
            
            # Add any remaining user content after the last AI response
            remaining_content = text[current_pos:].strip()
            if remaining_content:
                # Remove any @#prompt patterns from user content
                remaining_content = re.sub(r'@#\w+', '', remaining_content).strip()
                if remaining_content:
                    messages.append({
                        "role": "user",
                        "content": remaining_content
                    })
        else:
            # No AI responses found, treat all text as user content
            clean_text = re.sub(r'@#\w+', '', text).strip()
            if clean_text:
                messages.append({
                    "role": "user",
                    "content": clean_text
                })
        
        return messages
    
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