import uuid
import base64
import hashlib
import logging
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TransmissionMetadata:
    filename: Optional[str]
    total_size: int
    total_parts: int
    checksum: str

@dataclass
class TransmissionChunk:
    number: int
    total: int
    content: str

class TransmissionError(Exception):
    """Base exception for transmission-related errors."""
    pass

class TransmissionProtocol:
    def __init__(self, chunk_size: int = 1024 * 1024):  # Default 1MB chunks
        self.chunk_size = chunk_size
    
    def create_transmission(self, content: Union[str, bytes], 
                          content_type: str, 
                          filename: Optional[str] = None,
                          encoding: str = "utf-8") -> str:
        """Create a new transmission with the given content."""
        try:
            transmission_id = str(uuid.uuid4())
            
            if isinstance(content, str):
                content = content.encode(encoding)
            
            # Calculate checksum and metadata
            checksum = hashlib.sha256(content).hexdigest()
            total_size = len(content)
            chunks = self._chunk_content(content)
            total_parts = len(chunks)
            
            # Create the transmission JSON
            transmission = {
                "id": transmission_id,
                "type": content_type,
                "encoding": encoding,
                "metadata": {
                    "filename": filename,
                    "total_size": total_size,
                    "total_parts": total_parts,
                    "checksum": checksum
                },
                "chunks": [
                    {
                        "number": idx,
                        "total": total_parts,
                        "content": base64.b64encode(chunk).decode('ascii')
                    } for idx, chunk in enumerate(chunks, 1)
                ]
            }
            
            return json.dumps(transmission)
            
        except Exception as e:
            raise TransmissionError(f"Failed to create transmission: {str(e)}") from e

    def process_transmission(self, transmission_json: str) -> Dict[str, Any]:
        """Process a received transmission."""
        try:
            transmission = json.loads(transmission_json)
            
            # Extract transmission details
            trans_id = transmission["id"]
            content_type = transmission["type"]
            encoding = transmission.get("encoding", "utf-8")
            
            # Parse metadata
            meta = TransmissionMetadata(
                filename=transmission["metadata"].get("filename"),
                total_size=transmission["metadata"]["total_size"],
                total_parts=transmission["metadata"]["total_parts"],
                checksum=transmission["metadata"]["checksum"]
            )
            
            # Process chunks
            chunks = [
                TransmissionChunk(
                    number=chunk["number"],
                    total=chunk["total"],
                    content=chunk["content"]
                ) for chunk in transmission["chunks"]
            ]
            
            # Validate and reassemble content
            content = self._reassemble_chunks(chunks, encoding)
            if hashlib.sha256(content).hexdigest() != meta.checksum:
                raise ValueError("Checksum verification failed")
            
            return {
                "id": trans_id,
                "type": content_type,
                "content": content,
                "metadata": meta
            }
            
        except Exception as e:
            logger.error(f"Error processing transmission: {e}")
            raise
    
    def create_continuation_request(self, transmission_id: str, 
                                 next_part: int) -> str:
        """Create a continuation request for a specific transmission part."""
        request = {
            "id": transmission_id,
            "next_part": next_part
        }
        return json.dumps(request)
    
    def _chunk_content(self, content: bytes) -> List[bytes]:
        """Split content into chunks of specified size."""
        return [content[i:i + self.chunk_size] 
                for i in range(0, len(content), self.chunk_size)]
    
    def _reassemble_chunks(self, chunks: List[TransmissionChunk], 
                         encoding: str) -> bytes:
        """Reassemble chunks into complete content."""
        # Sort chunks by number
        chunks.sort(key=lambda x: x.number)
        
        # Validate chunk sequence
        if chunks[0].number != 1 or \
           chunks[-1].number != chunks[0].total or \
           len(chunks) != chunks[0].total:
            raise ValueError("Invalid or incomplete chunk sequence")
        
        # Decode and concatenate chunks
        content = b''.join(
            base64.b64decode(chunk.content) for chunk in chunks
        )
        return content

    def validate_transmission(self, transmission_json: str) -> bool:
        """Validate a received transmission."""
        # check  response.response_json for end reason = max_tokens.

    def replace_auto_generated(self, text: str) -> str:
        """Replace {auto_generated} placeholders with actual UUIDs."""
        result = text
        while "{auto_generated}" in result:
            result = result.replace("{auto_generated}", str(uuid.uuid4()), 1)
        return result

    def format_model_response(self, response_text: str, model_id: str) -> str:
        """Format a model response into a simple plain text object."""
        try:
            formatted_response = f"Model: {model_id}\nResponse: {response_text}"
            return formatted_response
        except Exception as e:
            raise TransmissionError(f"Failed to format model response: {str(e)}") from e
