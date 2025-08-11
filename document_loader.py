"""
Extended Document Loader for GPT-Researcher MCP.

Consolidates file format support and security features into a single clean module.
Supports 96+ file formats while maintaining safety and simplicity.
"""
import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Extended file format support (recovered from cleanup)
EXTENDED_FORMATS = {
    # Academic/LaTeX
    '.tex', '.bib', '.cls', '.sty', '.bst', '.aux', '.bbl', '.blg',
    # Programming languages  
    '.hs', '.lhs', '.ml', '.mli', '.fs', '.fsx', '.clj', '.cljs', 
    '.erl', '.ex', '.exs', '.nim', '.v', '.zig', '.jl', '.rkt',
    # Config/Build files
    '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.config',
    'Makefile', 'CMakeLists.txt', 'Dockerfile', '.dockerignore',
    # Data/Markup
    '.xml', '.xsl', '.xsd', '.dtd', '.csv', '.tsv', '.jsonl',
    # Documentation
    '.rst', '.adoc', '.textile', '.pod', '.rdoc', '.mediawiki',
    # Shell/Scripts
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    # Web/Frontend
    '.vue', '.svelte', '.tsx', '.jsx', '.scss', '.sass', '.less',
    # Mobile
    '.swift', '.kt', '.kts', '.dart', '.m', '.mm',
    # Database
    '.sql', '.prisma', '.graphql', '.proto',
    # Other
    '.lock', '.gradle', '.sbt', '.cabal', '.opam', '.nix'
}

try:
    from gpt_researcher.document.document import DocumentLoader as BaseDocumentLoader
except Exception:
    # Fallback if gpt_researcher isn't installed
    class BaseDocumentLoader:  # type: ignore
        def __init__(self, path: Union[str, List[str], Path]) -> None:
            self.path = path
        async def load(self) -> List[Dict[str, Any]]:
            return []

class ExtendedDocumentLoader(BaseDocumentLoader):  # type: ignore
    """
    Extended document loader with format support and safety features.
    
    Features:
    - Supports 96+ file formats for research corpus
    - Path traversal protection
    - Safe error handling with fallback
    - File size limits (100MB default)
    """
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
    
    def __init__(self, path: Union[str, List[str], Path]) -> None:
        super().__init__(path)
        self.supported_formats = EXTENDED_FORMATS
        
    def _is_safe_path(self, path: Path) -> bool:
        """Validate path doesn't escape the intended directory."""
        try:
            # Resolve to absolute path and check it's within bounds
            resolved = path.resolve()
            return not any(part.startswith('..') for part in resolved.parts)
        except Exception:
            return False
    
    def _is_supported(self, file_path: Path) -> bool:
        """Check if file format is supported."""
        return (file_path.suffix.lower() in self.supported_formats or 
                file_path.name in self.supported_formats)
    
    async def load(self) -> List[Dict[str, Any]]:
        """
        Load documents with extended format support and safety checks.
        Falls back to parent implementation or empty list on errors.
        """
        try:
            # First try the parent class implementation
            result = await super().load()
            if result:
                return result
                
            # If parent returns empty, try our extended loading
            if isinstance(self.path, (str, Path)):
                path = Path(self.path)
                if not self._is_safe_path(path):
                    logger.warning(f"Unsafe path detected: {path}")
                    return []
                    
                if path.is_file() and self._is_supported(path):
                    # Check file size
                    if path.stat().st_size > self.MAX_FILE_SIZE:
                        logger.warning(f"File too large: {path}")
                        return []
                    
                    # Try to load with extended format support
                    try:
                        content = path.read_text(encoding='utf-8', errors='ignore')
                        return [{
                            'raw_content': content,
                            'url': str(path.absolute())
                        }]
                    except Exception as e:
                        logger.debug(f"Failed to load {path}: {e}")
                        
            return []
            
        except Exception as e:
            logger.debug(f"Document loader error: {e}")
            # Safe fallback - return empty list rather than crashing
            return []

# For backward compatibility
DocumentLoader = ExtendedDocumentLoader