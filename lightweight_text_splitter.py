"""
Lightweight Text Splitter
Replaces LangChain text splitter with minimal dependencies
"""

import re
from typing import List

class LightweightTextSplitter:
    """Lightweight text splitter without LangChain dependencies"""
    
    def __init__(self, separator: str = "\n", chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize text splitter
        
        Args:
            separator: Character to split on
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
        """
        self.separator = separator
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Split text by separator
        splits = text.split(self.separator)
        chunks = []
        current_chunk = ""
        
        for split in splits:
            # If adding this split would exceed chunk size
            if len(current_chunk) + len(split) + len(self.separator) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap
                    if self.chunk_overlap > 0:
                        # Take last part of previous chunk for overlap
                        overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                        current_chunk = overlap_text + self.separator + split
                    else:
                        current_chunk = split
                else:
                    # If single split is too long, split it further
                    if len(split) > self.chunk_size:
                        # Split long text into smaller pieces
                        for i in range(0, len(split), self.chunk_size):
                            chunk = split[i:i + self.chunk_size]
                            if chunk.strip():
                                chunks.append(chunk.strip())
                    else:
                        current_chunk = split
            else:
                current_chunk += (self.separator if current_chunk else "") + split
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class CharacterTextSplitter(LightweightTextSplitter):
    """Character-based text splitter for compatibility"""
    
    def __init__(self, separator: str = "\n", chunk_size: int = 1000, chunk_overlap: int = 200, length_function=None):
        """
        Initialize character text splitter
        
        Args:
            separator: Character to split on
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            length_function: Function to calculate length (ignored for compatibility)
        """
        super().__init__(separator, chunk_size, chunk_overlap)


class RecursiveCharacterTextSplitter(LightweightTextSplitter):
    """Recursive character text splitter for compatibility"""
    
    def __init__(self, separators: List[str] = None, chunk_size: int = 1000, chunk_overlap: int = 200, length_function=None):
        """
        Initialize recursive character text splitter
        
        Args:
            separators: List of separators to try in order
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            length_function: Function to calculate length (ignored for compatibility)
        """
        if separators is None:
            separators = ["\n\n", "\n", " ", ""]
        
        # Use the first separator for simplicity
        super().__init__(separators[0], chunk_size, chunk_overlap) 