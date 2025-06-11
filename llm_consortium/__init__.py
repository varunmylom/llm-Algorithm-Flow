import click
import json
import llm
from llm.cli import load_conversation  # Import from llm.cli instead of llm
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import sys
import re
import os
import pathlib
import sqlite_utils
from pydantic import BaseModel
import time  # added import for time
import concurrent.futures  # Add concurrent.futures for parallel processing
import threading  # Add threading for thread-local storage
import secrets  # New: Import secrets for generating IDs


class ConsortiumConfig(BaseModel):
    models: Dict[str, int]  # Maps model names to instance counts
    system_prompt: Optional[str] = None
    confidence_threshold: float = 0.8
    max_iterations: int = 3
    minimum_iterations: int = 1
    arbiter: Optional[str] = None

    def to_dict(self):
        return self.model_dump()

class ConsortiumOrchestrator:
    def __init__(self, config: ConsortiumConfig):
        self.models = config.models
        # Store system_prompt from config
        self.system_prompt = config.system_prompt
        self.confidence_threshold = config.confidence_threshold
        self.max_iterations = config.max_iterations
        self.minimum_iterations = config.minimum_iterations
        self.arbiter = config.arbiter or "gemini-2.0-flash"
        self.iteration_history: List[IterationContext] = []
        self.consortium_id = None  # New: Store consortium ID
        self.conversation_id = None  # New: Store conversation ID

    def orchestrate(self, prompt: str, conversation_history: str = "", consortium_id: Optional[str] = None, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        self.consortium_id = consortium_id
        self.conversation_id = conversation_id
        
        model_responses = self._get_model_responses(prompt, conversation_history)
        synthesis_result = self._synthesize_responses(prompt, model_responses)
        return synthesis_result

    def _get_model_responses(self, prompt: str, conversation_history: str) -> List[Dict[str, Any]]:
        responses = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self._get_model_response, model, prompt, instance, conversation_history): (model, instance)
                for model, count in self.models.items()
                for instance in range(count)
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                    if data:
                        responses.append(data)
                except Exception as exc:
                    model_name, instance_num = futures[future]
                    print(f'{model_name} instance {instance_num} generated an exception: {exc}')
        return responses

    def _get_model_response(self, model: str, prompt: str, instance: int, conversation_history: str) -> Dict[str, Any]:
        full_prompt = f"{conversation_history}Human: {prompt}"
        response_obj = llm.get_model(model).prompt(full_prompt)

        if self.consortium_id:
            response_obj.consortium_id = self.consortium_id
        if self.conversation_id:
            response_obj.conversation_id = self.conversation_id

        return {
            "model": model,
            "instance": instance,
            "response_text": response_obj.text(),
            "confidence": 0.9
        }

    def _synthesize_responses(self, original_prompt: str, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        arbiter_prompt_str = f"Original prompt: {original_prompt}\n\nResponses:\n"
        for resp in responses:
            arbiter_prompt_str += f"- Model {resp['model']} (instance {resp['instance']}): {resp['response_text']}\n"

        arbiter = llm.get_model(self.arbiter)
        arbiter_response = arbiter.prompt(arbiter_prompt_str)

        if self.consortium_id:
            arbiter_response.consortium_id = self.consortium_id
        if self.conversation_id:
            arbiter_response.conversation_id = self.conversation_id
            
        return {"final_response": arbiter_response.text()}


class ConsortiumModel(llm.Model):
    def execute(self, prompt, stream, response, conversation):
        # Generate consortium_id for this execution
        consortium_id = secrets.token_hex(8)
        conversation_id = conversation.id if conversation else None
        
        # Build conversation history from conversation object
        conversation_history = ""
        if conversation and hasattr(conversation, 'responses'):
            for resp in conversation.responses:
                prompt_text = resp.prompt.prompt if hasattr(resp.prompt, 'prompt') else str(resp.prompt)
                response_text = resp.response if resp.response else ""
                conversation_history += f"Human: {prompt_text}\nAssistant: {response_text}\n\n"

        result = self.get_orchestrator().orchestrate(
            prompt.prompt, 
            conversation_history=conversation_history, 
            consortium_id=consortium_id, 
            conversation_id=conversation_id
        )
        
        response._set_content(result.get('final_response', ''))
        yield from response


