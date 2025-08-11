"""
Secure Document Loader for GPT-Researcher MCP
Incorporates security fixes for path traversal, DoS, and info disclosure
"""

import logging
import asyncio
from typing import List, Union, Dict, Any, Optional
from pathlib import Path

# Import security utilities
from security_utils import (
    validate_path,
    check_file_size,
    safe_read_file,
    RateLimiter,
    sanitize_error_message,
    validate_directory_traversal,
    get_safe_filename,
    SecurityError,
    PathTraversalError,
    FileSizeError
)

# Import clean architecture components
from document_loader_components import (
    DocumentLoaderOrchestrator as BaseOrchestrator,
    FileFormatRegistry,
    DirectoryTraverser,
    LoaderFactory,
    TextDocumentProcessor
)

# Try to import original base loader
try:
    from gpt_researcher.document.document import DocumentLoader as BaseDocumentLoader
except ImportError:
    class BaseDocumentLoader:
        def __init__(self, path):
            self.path = path
        async def load(self):
            raise NotImplementedError("Base DocumentLoader not available")


class SecureDirectoryTraverser(DirectoryTraverser):
    """Enhanced directory traverser with security checks"""
    
    def __init__(self, allowed_base: Optional[str] = None):
        super().__init__()
        self.allowed_base = allowed_base
        self.logger = logging.getLogger(__name__)
    
    def traverse(self, path: str) -> List[Path]:
        """Traverse directory with security validation"""
        try:
            # Validate path if allowed_base is set
            if self.allowed_base:
                validated_path = validate_path(path, self.allowed_base)
            else:
                validated_path = Path(path).resolve()
            
            # Validate directory is safe to traverse
            stats = validate_directory_traversal(validated_path)
            self.logger.info(
                f"Directory validated: {stats['total_files']} files, "
                f"{stats['total_size']:,} bytes total"
            )
            
            # Perform traversal with parent implementation
            return super().traverse(str(validated_path))
            
        except SecurityError as e:
            self.logger.error(f"Security violation: {sanitize_error_message(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Traversal failed: {sanitize_error_message(e)}")
            return []


class SecureTextDocumentProcessor(TextDocumentProcessor):
    """Enhanced text processor with security checks"""
    
    async def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process text file with size limits and safe reading"""
        try:
            # Check file size before processing
            check_file_size(file_path)
            
            # Try different encodings with safe read
            encodings = ['utf-8', 'utf-8-sig', 'latin-1']
            
            for encoding in encodings:
                try:
                    content = await safe_read_file(file_path, encoding)
                    return [{
                        "raw_content": content,
                        "url": get_safe_filename(str(file_path)),
                        "metadata": {
                            "encoding": encoding,
                            "source": get_safe_filename(str(file_path))
                        }
                    }]
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except Exception as e:
                    self.logger.debug(f"Failed with {encoding}: {sanitize_error_message(e)}")
                    continue
            
            # If all encodings fail, return error
            return [{
                "raw_content": "[File could not be decoded]",
                "url": get_safe_filename(str(file_path)),
                "metadata": {"error": "encoding_failure"}
            }]
            
        except SecurityError as e:
            self.logger.error(f"Security violation: {sanitize_error_message(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Processing failed: {sanitize_error_message(e)}")
            return []


class SecureDocumentLoaderOrchestrator(BaseOrchestrator):
    """Secure orchestrator with dependency injection and rate limiting"""
    
    def __init__(
        self,
        allowed_base: Optional[str] = None,
        registry: Optional[FileFormatRegistry] = None,
        traverser: Optional[DirectoryTraverser] = None,
        factory: Optional[LoaderFactory] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize with injected dependencies"""
        self.logger = logger or logging.getLogger(__name__)
        self.allowed_base = allowed_base or os.getcwd()  # Default to CWD
        
        # Use injected dependencies or create secure defaults
        self.registry = registry or FileFormatRegistry()
        self.traverser = traverser or SecureDirectoryTraverser(self.allowed_base)
        
        # Create factory with secure text processor
        if not factory:
            secure_text_processor = SecureTextDocumentProcessor(self.logger)
            self.factory = LoaderFactory(self.registry, self.logger)
            # Replace text processor in factory
            self.factory.text_processor = secure_text_processor
        else:
            self.factory = factory
        
        # Rate limiter for concurrent operations
        self.rate_limiter = RateLimiter()
        
        self.logger.info(
            f"SecureDocumentLoaderOrchestrator initialized with base: {self.allowed_base}"
        )
    
    async def load_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load single file with validation"""
        try:
            # Validate path
            if self.allowed_base:
                validated_path = validate_path(str(file_path), self.allowed_base)
            else:
                validated_path = file_path.resolve()
            
            # Load with rate limiting
            async with self.rate_limiter:
                loader = self.factory.create_loader(validated_path)
                return await loader.load(validated_path)
                
        except SecurityError as e:
            self.logger.error(f"Security violation: {sanitize_error_message(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Load failed: {sanitize_error_message(e)}")
            return []
    
    async def load_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Load directory with security validation"""
        try:
            # Validate directory path
            if self.allowed_base:
                validated_dir = validate_path(directory, self.allowed_base)
            else:
                validated_dir = Path(directory).resolve()
            
            # Get files with secure traverser
            files = self.traverser.traverse(str(validated_dir))
            
            if not files:
                self.logger.warning(f"No files found in directory: {get_safe_filename(directory)}")
                return []
            
            self.logger.info(f"Loading {len(files)} files from directory")
            
            # Load files with rate limiting
            all_docs = []
            for file_path in files:
                async with self.rate_limiter:
                    docs = await self.load_file(file_path)
                    all_docs.extend(docs)
            
            return all_docs
            
        except SecurityError as e:
            self.logger.error(f"Security violation: {sanitize_error_message(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Directory load failed: {sanitize_error_message(e)}")
            return []


class SecureExtendedDocumentLoader(BaseDocumentLoader):
    """
    Secure extended document loader with all security fixes applied.
    
    This loader:
    - Prevents path traversal attacks
    - Enforces file size limits
    - Sanitizes error messages
    - Uses rate limiting for DoS protection
    - Validates directories before traversal
    """
    
    def __init__(self, path: Union[str, List[str]], allowed_base: Optional[str] = None):
        """
        Initialize with path validation.
        
        Args:
            path: File or directory path(s) to load
            allowed_base: Optional base directory for path validation
        """
        super().__init__(path)
        
        # Set up secure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Determine allowed base
        if allowed_base:
            self.allowed_base = Path(allowed_base).resolve()
        else:
            # Use DOC_PATH from environment or current directory
            import os
            doc_path = os.getenv("DOC_PATH")
            if doc_path and os.path.exists(doc_path):
                self.allowed_base = Path(doc_path).resolve()
            else:
                self.allowed_base = Path.cwd()
        
        # Initialize secure orchestrator
        self.orchestrator = SecureDocumentLoaderOrchestrator(
            allowed_base=str(self.allowed_base),
            logger=self.logger
        )
        
        self.logger.info(
            f"SecureExtendedDocumentLoader initialized with base: {self.allowed_base}"
        )
    
    async def load(self) -> List[dict]:
        """
        Load documents with comprehensive security checks.
        
        Returns:
            List of document dictionaries with 'raw_content' and 'url' keys
        """
        try:
            # Handle different path types
            if isinstance(self.path, list):
                # Multiple specific files
                self.logger.info(f"Loading {len(self.path)} specific files")
                
                # Validate all paths first
                validated_paths = []
                for path in self.path:
                    try:
                        validated = validate_path(path, str(self.allowed_base))
                        validated_paths.append(validated)
                    except PathTraversalError as e:
                        self.logger.error(f"Invalid path skipped: {sanitize_error_message(e)}")
                        continue
                
                # Load validated files
                return await self.orchestrator.load_files(validated_paths)
            
            elif isinstance(self.path, str):
                # Validate single path
                try:
                    validated = validate_path(self.path, str(self.allowed_base))
                except PathTraversalError as e:
                    self.logger.error(f"Invalid path: {sanitize_error_message(e)}")
                    return []
                
                if validated.is_file():
                    # Single file
                    self.logger.info(f"Loading single file: {get_safe_filename(str(validated))}")
                    return await self.orchestrator.load_file(validated)
                
                elif validated.is_dir():
                    # Directory
                    self.logger.info(f"Loading directory: {get_safe_filename(str(validated))}")
                    return await self.orchestrator.load_directory(str(validated))
                
                else:
                    self.logger.error(f"Path does not exist: {get_safe_filename(self.path)}")
                    return []
            
            else:
                self.logger.error(f"Invalid path type: {type(self.path)}")
                return []
                
        except SecurityError as e:
            self.logger.error(f"Security violation: {sanitize_error_message(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Load failed: {sanitize_error_message(e)}")
            return []
    
    @property
    def supported_formats(self) -> int:
        """Get the number of supported file formats."""
        return self.orchestrator.supported_formats
    
    def __repr__(self):
        """String representation without exposing paths."""
        return f"SecureExtendedDocumentLoader(formats={self.supported_formats})"


# Export secure loader as default
DocumentLoader = SecureExtendedDocumentLoader