"""
Extended Document Loader for GPT-Researcher MCP
Extends the base DocumentLoader to support 96+ additional file formats
Author: Younesse Kaddar
"""

import os
from typing import List, Union, Set
from pathlib import Path

# Try to import the original - fall back to our own base if needed
try:
    from gpt_researcher.document.document import DocumentLoader as BaseDocumentLoader
except ImportError:
    # If we can't import, define a minimal base (should never happen in production)
    class BaseDocumentLoader:
        def __init__(self, path):
            self.path = path
        async def load(self):
            raise NotImplementedError("Base DocumentLoader not available")


class ExtendedDocumentLoader(BaseDocumentLoader):
    """
    Extends GPT-Researcher's DocumentLoader to support additional file formats.
    
    Adds support for:
    - Programming languages (96+ formats)
    - Academic documents (LaTeX, BibTeX, etc.)
    - Configuration files
    - Documentation formats
    """
    
    # Additional text-based extensions we support
    EXTENDED_TEXT_FORMATS: Set[str] = {
        # LaTeX/Academic
        'tex', 'bib', 'cls', 'sty', 'bst', 'dtx', 'ins',
        
        # Markup/Documentation
        'org', 'rst', 'adoc', 'asciidoc', 'textile', 'mediawiki',
        
        # Programming - Functional
        'hs', 'lhs', 'ml', 'mli', 'sml', 'sig', 
        'agda', 'lean', 'v', 'idr', 'elm', 'purs',
        
        # Programming - Systems
        'c', 'h', 'cpp', 'cc', 'cxx', 'hpp', 'hxx', 'hh',
        'rs', 'go', 'zig', 'nim', 'd', 'ada', 'adb', 'ads',
        
        # Programming - JVM
        'java', 'scala', 'sc', 'kt', 'kts', 'groovy', 'clj', 'cljs', 'cljc',
        
        # Programming - .NET
        'cs', 'fs', 'fsx', 'fsi', 'vb',
        
        # Programming - Dynamic
        'py', 'pyx', 'pyi', 'pyw',
        'rb', 'rake', 'gemspec',
        'pl', 'pm', 'pod', 't',
        'php', 'php3', 'php4', 'php5', 'phtml',
        'lua',
        
        # Programming - Web
        'js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs',
        'coffee', 'dart', 'elm',
        'vue', 'svelte',
        
        # Programming - Mobile
        'swift', 'm', 'mm', 'objc',
        
        # Programming - Scientific
        'r', 'R', 'Rmd', 'jl', 'f90', 'f95', 'f03', 'for',
        'matlab', 'octave', 'sci', 'sce',
        
        # Programming - Other
        'ex', 'exs', 'erl', 'hrl', 'rkt', 'scm', 'lisp', 'lsp', 'l', 'cl',
        
        # Data/Config
        'json', 'jsonl', 'geojson',
        'yaml', 'yml',
        'toml', 'ini', 'cfg', 'conf', 'config',
        'xml', 'xsd', 'xsl', 'xslt',
        'properties', 'props',
        
        # Database
        'sql', 'psql', 'mysql', 'sqlite',
        'graphql', 'gql',
        
        # Shell/Scripts
        'sh', 'bash', 'zsh', 'fish', 'ksh', 'csh', 'tcsh',
        'ps1', 'psm1', 'psd1', 'bat', 'cmd',
        
        # Styling
        'css', 'scss', 'sass', 'less', 'styl',
        
        # Build/Project files
        'makefile', 'mk', 'mak', 'make',
        'cmake', 'dockerfile', 'containerfile',
        'vagrantfile', 'jenkinsfile', 'rakefile',
        'gemfile', 'brewfile', 'podfile', 'cartfile',
        'gradle', 'maven', 'ant', 'bazel', 'buck',
        
        # Documentation
        'readme', 'license', 'changelog', 'authors', 'contributors',
        'todo', 'fixme', 'hack',
        
        # Logs/Diffs
        'log', 'diff', 'patch',
        
        # Editor configs
        'vim', 'el', 'emacs'
    }
    
    # Directories to skip during traversal
    SKIP_DIRS: Set[str] = {
        '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env',
        'dist', 'build', 'target', 'out', 'bin', 'obj',
        '.pytest_cache', '.mypy_cache', '.tox', '.coverage',
        '.idea', '.vscode', '.vs', '.eclipse',
        'vendor', 'deps', 'dependencies',
        '.terraform', '.serverless'
    }
    
    def __init__(self, path: Union[str, List[str]]):
        """Initialize the extended document loader."""
        super().__init__(path)
        self._text_loader_cache = {}
    
    def _is_extended_format(self, file_extension: str) -> bool:
        """Check if this is one of our extended formats."""
        return file_extension.lower() in self.EXTENDED_TEXT_FORMATS
    
    def _should_skip_directory(self, dirname: str) -> bool:
        """Check if directory should be skipped during traversal."""
        return dirname in self.SKIP_DIRS or dirname.startswith('.')
    
    async def _load_document(self, file_path: str, file_extension: str) -> list:
        """
        Load a document, handling extended formats.
        
        For extended formats, use TextLoader with encoding fallback.
        For standard formats, delegate to parent implementation.
        """
        # Normalize extension
        file_extension = file_extension.lower().strip('.')
        
        # Handle extended formats
        if self._is_extended_format(file_extension):
            return await self._load_text_file(file_path)
        
        # Handle files without extensions that might be text
        if not file_extension:
            filename = os.path.basename(file_path).lower()
            # Check if filename itself is a known text format
            if filename in self.EXTENDED_TEXT_FORMATS:
                return await self._load_text_file(file_path)
        
        # Delegate to parent for standard formats
        try:
            return await super()._load_document(file_path, file_extension)
        except (AttributeError, NotImplementedError):
            # If parent doesn't have this method, try text loader as fallback
            return await self._load_text_file(file_path)
    
    async def _load_text_file(self, file_path: str) -> list:
        """Load a text file with encoding detection and fallback."""
        # Try different encodings in order
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        path = Path(file_path)
        
        for encoding in encodings:
            try:
                content = path.read_text(encoding=encoding)
                # Return in a format similar to what TextLoader would return
                return [{
                    'page_content': content,
                    'metadata': {'source': file_path, 'encoding': encoding}
                }]
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                continue
        
        # If all encodings fail, try binary fallback
        return self._load_binary_as_text(file_path)
    
    def _load_binary_as_text(self, file_path: str) -> list:
        """Last resort: load binary file and decode with replacement chars."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
            # Create a minimal document structure
            return [{
                'page_content': content,
                'metadata': {'source': file_path}
            }]
        except Exception:
            return []
    
    async def load(self) -> list:
        """
        Load documents with extended format support.
        
        Overrides parent to:
        1. Filter out unwanted directories
        2. Handle extended formats
        3. Provide better error messages
        """
        # If parent's load works perfectly, use it
        try:
            # First, let's modify behavior for directory traversal
            if isinstance(self.path, str) and os.path.isdir(self.path):
                # We need to handle directory traversal ourselves to skip dirs
                return await self._load_directory(self.path)
            else:
                # For single files or file lists, use parent
                return await super().load()
        except (AttributeError, NotImplementedError):
            # Parent doesn't have load, implement our own
            return await self._custom_load()
    
    async def _load_directory(self, directory: str) -> list:
        """Load all documents from a directory, respecting skip rules."""
        import asyncio
        
        tasks = []
        for root, dirs, files in os.walk(directory):
            # Filter directories in-place to prevent traversal
            dirs[:] = [d for d in dirs if not self._should_skip_directory(d)]
            
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                ext = ext.strip('.').lower()
                
                # Skip certain file patterns
                if file.startswith('.') or file.endswith('~'):
                    continue
                    
                tasks.append(self._load_document(file_path, ext))
        
        # Load all documents concurrently
        docs = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    for doc in result:
                        if hasattr(doc, 'page_content') and doc.page_content:
                            docs.append({
                                "raw_content": doc.page_content,
                                "url": os.path.basename(doc.metadata.get('source', ''))
                            })
        
        if not docs:
            raise ValueError("No documents found or loaded successfully")
        
        return docs
    
    async def _custom_load(self) -> list:
        """Fallback implementation if parent's load is not available."""
        import asyncio
        
        tasks = []
        paths = self.path if isinstance(self.path, list) else [self.path]
        
        for path in paths:
            if os.path.isfile(path):
                _, ext = os.path.splitext(path)
                tasks.append(self._load_document(path, ext.strip('.')))
            elif os.path.isdir(path):
                return await self._load_directory(path)
        
        docs = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    for doc in result:
                        if hasattr(doc, 'page_content') and doc.page_content:
                            docs.append({
                                "raw_content": doc.page_content,
                                "url": os.path.basename(doc.metadata.get('source', ''))
                            })
        
        if not docs:
            raise ValueError("No documents found or loaded successfully")
            
        return docs