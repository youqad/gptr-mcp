"""
Security utilities for GPT-Researcher MCP
Provides path validation, resource limits, and safe file operations
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Security configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total limit
CONCURRENT_FILE_LIMIT = 10  # Max concurrent file operations
MAX_DIRECTORY_DEPTH = 10  # Prevent deep recursion
MAX_FILES_PER_DIRECTORY = 1000  # Prevent DoS via huge directories

class SecurityError(Exception):
    """Base exception for security violations"""
    pass

class PathTraversalError(SecurityError):
    """Raised when path traversal is detected"""
    pass

class FileSizeError(SecurityError):
    """Raised when file size limits are exceeded"""
    pass

def validate_path(path: str, allowed_base: str) -> Path:
    """
    Validate and canonicalize file paths to prevent traversal attacks.
    
    Args:
        path: The path to validate
        allowed_base: The allowed base directory
        
    Returns:
        Validated Path object
        
    Raises:
        PathTraversalError: If path is outside allowed directory
    """
    try:
        # Resolve to absolute path, following symlinks
        resolved = Path(path).resolve()
        allowed = Path(allowed_base).resolve()
        
        # Check if resolved path is within allowed base
        try:
            resolved.relative_to(allowed)
        except ValueError:
            # Path is outside allowed directory
            raise PathTraversalError(
                f"Path traversal detected: {path} is outside allowed directory"
            )
        
        # Additional checks for suspicious patterns
        path_str = str(resolved)
        suspicious_patterns = ['..', '~', '$', '|', ';', '&', '>', '<', '`']
        for pattern in suspicious_patterns:
            if pattern in str(path):  # Check original path for injection attempts
                logger.warning(f"Suspicious pattern '{pattern}' in path: {path}")
        
        return resolved
        
    except Exception as e:
        if isinstance(e, PathTraversalError):
            raise
        raise PathTraversalError(f"Invalid path: {path} - {str(e)}")

def check_file_size(file_path: Path, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Check if file size is within limits.
    
    Args:
        file_path: Path to the file
        max_size: Maximum allowed size in bytes
        
    Raises:
        FileSizeError: If file exceeds size limit
    """
    if not file_path.exists():
        return
    
    size = file_path.stat().st_size
    if size > max_size:
        raise FileSizeError(
            f"File too large: {file_path.name} ({size:,} bytes > {max_size:,} bytes limit)"
        )

async def safe_read_file(file_path: Path, encoding: str = 'utf-8') -> str:
    """
    Safely read a file with size checks and error handling.
    
    Args:
        file_path: Path to the file
        encoding: File encoding
        
    Returns:
        File contents as string
        
    Raises:
        FileSizeError: If file is too large
        SecurityError: For other security issues
    """
    # Validate file exists and is a regular file
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise SecurityError(f"Not a regular file: {file_path}")
    
    # Check file size
    check_file_size(file_path)
    
    # Read file with timeout protection
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: file_path.read_text(encoding=encoding)
        )
    except Exception as e:
        # Don't expose full path in error messages
        raise SecurityError(f"Failed to read file: {file_path.name}")

class RateLimiter:
    """Simple rate limiter for concurrent operations"""
    
    def __init__(self, max_concurrent: int = CONCURRENT_FILE_LIMIT):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def acquire(self):
        """Acquire a slot for operation"""
        await self.semaphore.acquire()
    
    def release(self):
        """Release the slot after operation"""
        self.semaphore.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()

def sanitize_error_message(error: Exception, context: str = "") -> str:
    """
    Sanitize error messages to prevent information disclosure.
    
    Args:
        error: The exception to sanitize
        context: Optional context about the operation
        
    Returns:
        Safe error message without sensitive information
    """
    # Map error types to safe messages
    safe_messages = {
        FileNotFoundError: "File not found",
        PermissionError: "Permission denied",
        IsADirectoryError: "Invalid file type",
        PathTraversalError: "Invalid path",
        FileSizeError: "File size limit exceeded",
        UnicodeDecodeError: "File encoding error",
        MemoryError: "Insufficient memory",
        TimeoutError: "Operation timed out",
    }
    
    # Get safe message for known error types
    for error_type, message in safe_messages.items():
        if isinstance(error, error_type):
            if context:
                return f"{message}: {context}"
            return message
    
    # Generic message for unknown errors
    return "Operation failed" if not context else f"Operation failed: {context}"

def validate_directory_traversal(
    path: Path,
    max_depth: int = MAX_DIRECTORY_DEPTH,
    max_files: int = MAX_FILES_PER_DIRECTORY
) -> Dict[str, int]:
    """
    Validate directory for safe traversal.
    
    Args:
        path: Directory path to validate
        max_depth: Maximum allowed directory depth
        max_files: Maximum files per directory
        
    Returns:
        Dictionary with validation stats
        
    Raises:
        SecurityError: If directory is unsafe to traverse
    """
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    
    stats = {
        'total_files': 0,
        'total_dirs': 0,
        'max_depth': 0,
        'total_size': 0
    }
    
    for root, dirs, files in os.walk(path):
        current_depth = len(Path(root).relative_to(path).parts)
        
        # Check depth limit
        if current_depth > max_depth:
            raise SecurityError(f"Directory too deep: {current_depth} > {max_depth}")
        
        # Check file count limit
        if len(files) > max_files:
            raise SecurityError(f"Too many files in directory: {len(files)} > {max_files}")
        
        stats['total_files'] += len(files)
        stats['total_dirs'] += len(dirs)
        stats['max_depth'] = max(stats['max_depth'], current_depth)
        
        # Calculate total size
        for file in files:
            file_path = Path(root) / file
            if file_path.is_file():
                stats['total_size'] += file_path.stat().st_size
        
        # Check total size limit
        if stats['total_size'] > MAX_TOTAL_SIZE:
            raise SecurityError(
                f"Directory too large: {stats['total_size']:,} bytes > {MAX_TOTAL_SIZE:,} bytes"
            )
    
    return stats

def get_safe_filename(filename: str) -> str:
    """
    Sanitize filename for safe display.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for display
    """
    # Remove path components
    name = Path(filename).name
    
    # Truncate if too long
    if len(name) > 100:
        name = name[:97] + "..."
    
    # Remove special characters
    safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_')
    sanitized = ''.join(c if c in safe_chars else '_' for c in name)
    
    return sanitized if sanitized else "unnamed"