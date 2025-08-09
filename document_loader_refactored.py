"""
Refactored Extended Document Loader for GPT-Researcher MCP
Uses clean architecture components while maintaining backward compatibility
"""

import logging
from typing import List, Union
from pathlib import Path

# Import our clean architecture components
from document_loader_components import (
    DocumentLoaderOrchestrator,
    FileFormatRegistry,
    DirectoryTraverser
)

# Try to import the original - fall back to our own base if needed
try:
    from gpt_researcher.document.document import DocumentLoader as BaseDocumentLoader
except ImportError:
    # If we can't import, define a minimal base
    class BaseDocumentLoader:
        def __init__(self, path):
            self.path = path
        async def load(self):
            raise NotImplementedError("Base DocumentLoader not available")


class ExtendedDocumentLoader(BaseDocumentLoader):
    """
    Extends GPT-Researcher's DocumentLoader using clean architecture.
    
    This is a facade that maintains backward compatibility while
    delegating to our clean architecture components.
    
    Supports 162+ file formats including:
    - Programming languages
    - Academic documents (LaTeX, BibTeX, etc.)
    - Configuration files
    - Documentation formats
    """
    
    def __init__(self, path: Union[str, List[str]]):
        """Initialize with clean architecture components."""
        super().__init__(path)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize our orchestrator
        self.orchestrator = DocumentLoaderOrchestrator(self.logger)
        self.logger.info(f"ExtendedDocumentLoader initialized with {self.orchestrator.supported_formats} supported formats")
    
    async def load(self) -> List[dict]:
        """
        Load documents using clean architecture components.
        
        Returns:
            List of document dictionaries with 'raw_content' and 'url' keys
        """
        try:
            # Handle different path types
            if isinstance(self.path, list):
                # Multiple specific files
                self.logger.info(f"Loading {len(self.path)} specific files")
                return await self.orchestrator.load_files(self.path)
            
            elif isinstance(self.path, str):
                path_obj = Path(self.path)
                
                if path_obj.is_file():
                    # Single file
                    self.logger.info(f"Loading single file: {self.path}")
                    return await self.orchestrator.load_file(path_obj)
                
                elif path_obj.is_dir():
                    # Directory
                    self.logger.info(f"Loading directory: {self.path}")
                    return await self.orchestrator.load_directory(self.path)
                
                else:
                    raise ValueError(f"Path does not exist: {self.path}")
            
            else:
                raise ValueError(f"Invalid path type: {type(self.path)}")
                
        except Exception as e:
            self.logger.error(f"Failed to load documents: {e}")
            raise
    
    @property
    def supported_formats(self) -> int:
        """Get the number of supported file formats."""
        return self.orchestrator.supported_formats
    
    def get_format_info(self, extension: str):
        """Get information about a specific file format."""
        return self.orchestrator.get_format_info(extension)
    
    def __repr__(self):
        """String representation."""
        return f"ExtendedDocumentLoader(path={self.path}, formats={self.supported_formats})"


# For backward compatibility, also export as DocumentLoader
DocumentLoader = ExtendedDocumentLoader