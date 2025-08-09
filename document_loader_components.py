"""
Document Loader Components - Clean Architecture
Following SOLID principles for maintainable, testable code
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Set, List, Dict, Any, Optional, Protocol, Callable
# Note: We implement our own loaders to avoid langchain_community dependency
# The original GPT-Researcher might have these, but we'll use our own simple implementations

# Configure logging
logger = logging.getLogger(__name__)


class FileCategory(Enum):
    """Enumeration of file categories for organization."""
    ACADEMIC = "academic"
    PROGRAMMING = "programming"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    DATA = "data"
    STANDARD = "standard"
    UNKNOWN = "unknown"


@dataclass
class FileFormat:
    """Represents a file format with its metadata."""
    extension: str
    category: FileCategory
    description: str = ""
    mime_type: Optional[str] = None


class FileFormatRegistry:
    """
    Registry for managing file formats and their associations.
    Single Responsibility: Manage file format metadata and categorization.
    """
    
    def __init__(self):
        self._formats: Dict[str, FileFormat] = {}
        self._initialize_formats()
    
    def _initialize_formats(self):
        """Initialize the registry with all 162+ known formats."""
        # Academic formats
        academic_formats = [
            ('tex', 'LaTeX document'), ('bib', 'BibTeX bibliography'),
            ('cls', 'LaTeX class'), ('sty', 'LaTeX style'),
            ('bst', 'BibTeX style'), ('dtx', 'LaTeX documented source'),
            ('ins', 'LaTeX installer'), ('org', 'Org-mode document'),
            ('rst', 'reStructuredText'), ('adoc', 'AsciiDoc'),
            ('asciidoc', 'AsciiDoc'), ('textile', 'Textile markup'),
            ('mediawiki', 'MediaWiki markup'),
        ]
        for ext, desc in academic_formats:
            self.register(ext, FileCategory.ACADEMIC, desc)
        
        # Programming languages - ALL 96+ formats
        programming_formats = [
            # Functional languages
            ('hs', 'Haskell'), ('lhs', 'Literate Haskell'),
            ('ml', 'OCaml'), ('mli', 'OCaml interface'),
            ('sml', 'Standard ML'), ('sig', 'SML signature'),
            ('agda', 'Agda'), ('lean', 'Lean'), ('v', 'Coq'),
            ('idr', 'Idris'), ('elm', 'Elm'), ('purs', 'PureScript'),
            
            # Systems programming
            ('c', 'C'), ('h', 'C header'),
            ('cpp', 'C++'), ('cc', 'C++'), ('cxx', 'C++'),
            ('hpp', 'C++ header'), ('hxx', 'C++ header'), ('hh', 'C++ header'),
            ('rs', 'Rust'), ('go', 'Go'), ('zig', 'Zig'),
            ('nim', 'Nim'), ('d', 'D'), ('ada', 'Ada'),
            ('adb', 'Ada body'), ('ads', 'Ada spec'),
            
            # JVM languages
            ('java', 'Java'), ('scala', 'Scala'), ('sc', 'Scala script'),
            ('kt', 'Kotlin'), ('kts', 'Kotlin script'),
            ('groovy', 'Groovy'), ('clj', 'Clojure'),
            ('cljs', 'ClojureScript'), ('cljc', 'Clojure common'),
            
            # .NET languages
            ('cs', 'C#'), ('fs', 'F#'), ('fsx', 'F# script'),
            ('fsi', 'F# signature'), ('vb', 'Visual Basic'),
            
            # Dynamic languages
            ('py', 'Python'), ('pyx', 'Cython'), ('pyi', 'Python interface'),
            ('pyw', 'Python Windows'),
            ('rb', 'Ruby'), ('rake', 'Rakefile'), ('gemspec', 'Gem specification'),
            ('pl', 'Perl'), ('pm', 'Perl module'), ('pod', 'Perl documentation'),
            ('t', 'Perl test'), ('php', 'PHP'), ('php3', 'PHP3'),
            ('php4', 'PHP4'), ('php5', 'PHP5'), ('phtml', 'PHP HTML'),
            ('lua', 'Lua'),
            
            # Web languages
            ('js', 'JavaScript'), ('jsx', 'JSX'), ('ts', 'TypeScript'),
            ('tsx', 'TSX'), ('mjs', 'ES module'), ('cjs', 'CommonJS'),
            ('coffee', 'CoffeeScript'), ('dart', 'Dart'),
            ('vue', 'Vue'), ('svelte', 'Svelte'),
            
            # Mobile languages
            ('swift', 'Swift'), ('m', 'Objective-C'), ('mm', 'Objective-C++'),
            ('objc', 'Objective-C'),
            
            # Scientific languages
            ('r', 'R'), ('R', 'R'), ('Rmd', 'R Markdown'),
            ('jl', 'Julia'), ('f90', 'Fortran 90'), ('f95', 'Fortran 95'),
            ('f03', 'Fortran 2003'), ('for', 'Fortran'),
            ('matlab', 'MATLAB'), ('octave', 'Octave'),
            ('sci', 'Scilab'), ('sce', 'Scilab script'),
            
            # Lisp family
            ('ex', 'Elixir'), ('exs', 'Elixir script'),
            ('erl', 'Erlang'), ('hrl', 'Erlang header'),
            ('rkt', 'Racket'), ('scm', 'Scheme'),
            ('lisp', 'Lisp'), ('lsp', 'Lisp'), ('l', 'Lisp'),
            ('cl', 'Common Lisp'),
        ]
        for ext, desc in programming_formats:
            self.register(ext, FileCategory.PROGRAMMING, desc)
        
        # Configuration and data formats
        config_formats = [
            ('json', 'JSON'), ('jsonl', 'JSON Lines'), ('geojson', 'GeoJSON'),
            ('yaml', 'YAML'), ('yml', 'YAML'),
            ('toml', 'TOML'), ('ini', 'INI'), ('cfg', 'Configuration'),
            ('conf', 'Configuration'), ('config', 'Configuration'),
            ('xml', 'XML'), ('xsd', 'XML Schema'), ('xsl', 'XSL'),
            ('xslt', 'XSLT'), ('properties', 'Properties'),
            ('props', 'Properties'),
        ]
        for ext, desc in config_formats:
            self.register(ext, FileCategory.CONFIGURATION, desc)
        
        # Database and query languages
        data_formats = [
            ('sql', 'SQL'), ('psql', 'PostgreSQL'), ('mysql', 'MySQL'),
            ('sqlite', 'SQLite'), ('graphql', 'GraphQL'), ('gql', 'GraphQL'),
        ]
        for ext, desc in data_formats:
            self.register(ext, FileCategory.DATA, desc)
        
        # Shell and scripting
        shell_formats = [
            ('sh', 'Shell'), ('bash', 'Bash'), ('zsh', 'Zsh'),
            ('fish', 'Fish'), ('ksh', 'Korn shell'), ('csh', 'C shell'),
            ('tcsh', 'TC shell'), ('ps1', 'PowerShell'),
            ('psm1', 'PowerShell module'), ('psd1', 'PowerShell data'),
            ('bat', 'Batch'), ('cmd', 'Command'),
        ]
        for ext, desc in shell_formats:
            self.register(ext, FileCategory.PROGRAMMING, desc)
        
        # Styling languages
        style_formats = [
            ('css', 'CSS'), ('scss', 'SCSS'), ('sass', 'Sass'),
            ('less', 'Less'), ('styl', 'Stylus'),
        ]
        for ext, desc in style_formats:
            self.register(ext, FileCategory.PROGRAMMING, desc)
        
        # Build and project files
        build_formats = [
            ('makefile', 'Makefile'), ('mk', 'Make'), ('mak', 'Make'),
            ('make', 'Make'), ('cmake', 'CMake'),
            ('dockerfile', 'Dockerfile'), ('containerfile', 'Containerfile'),
            ('vagrantfile', 'Vagrantfile'), ('jenkinsfile', 'Jenkinsfile'),
            ('rakefile', 'Rakefile'), ('gemfile', 'Gemfile'),
            ('brewfile', 'Brewfile'), ('podfile', 'Podfile'),
            ('cartfile', 'Cartfile'), ('gradle', 'Gradle'),
            ('maven', 'Maven'), ('ant', 'Ant'), ('bazel', 'Bazel'),
            ('buck', 'Buck'),
        ]
        for ext, desc in build_formats:
            self.register(ext, FileCategory.CONFIGURATION, desc)
        
        # Documentation files
        doc_formats = [
            ('readme', 'README'), ('license', 'License'),
            ('changelog', 'Changelog'), ('authors', 'Authors'),
            ('contributors', 'Contributors'), ('todo', 'TODO'),
            ('fixme', 'FIXME'), ('hack', 'HACK'),
            ('log', 'Log'), ('diff', 'Diff'), ('patch', 'Patch'),
        ]
        for ext, desc in doc_formats:
            self.register(ext, FileCategory.DOCUMENTATION, desc)
        
        # Editor configs
        editor_formats = [
            ('vim', 'Vim config'), ('el', 'Emacs Lisp'), ('emacs', 'Emacs'),
        ]
        for ext, desc in editor_formats:
            self.register(ext, FileCategory.CONFIGURATION, desc)
        
        # Standard document formats
        standard_formats = [
            ('pdf', 'PDF'), ('doc', 'Word'), ('docx', 'Word'),
            ('pptx', 'PowerPoint'), ('xls', 'Excel'), ('xlsx', 'Excel'),
            ('csv', 'CSV'), ('md', 'Markdown'), ('html', 'HTML'),
            ('htm', 'HTML'),
        ]
        for ext, desc in standard_formats:
            self.register(ext, FileCategory.STANDARD, desc)
    
    def register(self, extension: str, category: FileCategory, 
                 description: str = "", mime_type: Optional[str] = None):
        """Register a new file format."""
        self._formats[extension.lower()] = FileFormat(
            extension=extension.lower(),
            category=category,
            description=description,
            mime_type=mime_type
        )
    
    def get_format(self, extension: str) -> Optional[FileFormat]:
        """Get format info for an extension."""
        return self._formats.get(extension.lower().strip('.'))
    
    def get_category(self, extension: str) -> FileCategory:
        """Get the category for a file extension."""
        fmt = self.get_format(extension)
        return fmt.category if fmt else FileCategory.UNKNOWN
    
    def is_supported(self, extension: str) -> bool:
        """Check if an extension is supported."""
        return extension.lower().strip('.') in self._formats
    
    def get_extensions_by_category(self, category: FileCategory) -> Set[str]:
        """Get all extensions for a category."""
        return {fmt.extension for fmt in self._formats.values() 
                if fmt.category == category}
    
    @property
    def total_formats(self) -> int:
        """Get total number of registered formats."""
        return len(self._formats)


class DirectoryTraverser:
    """
    Handles directory traversal and file discovery.
    Single Responsibility: Navigate file systems and filter files.
    """
    
    DEFAULT_SKIP_DIRS = {
        # Version control
        '.git', '.svn', '.hg',
        # Python
        '__pycache__', '.venv', 'venv', 'env', '.tox', '.pytest_cache',
        # Node/JS
        'node_modules', 'bower_components',
        # Build outputs
        'dist', 'build', 'target', 'out', 'bin', 'obj',
        # IDE
        '.idea', '.vscode', '.vs',
        # Dependencies
        'vendor', 'deps',
        # Cloud/Deploy
        '.terraform', '.serverless',
    }
    
    def __init__(self, skip_dirs: Optional[Set[str]] = None,
                 skip_hidden: bool = True):
        self.skip_dirs = skip_dirs or self.DEFAULT_SKIP_DIRS
        self.skip_hidden = skip_hidden
    
    def should_skip_directory(self, dirname: str) -> bool:
        """Check if a directory should be skipped."""
        if self.skip_hidden and dirname.startswith('.'):
            return True
        return dirname in self.skip_dirs
    
    def should_skip_file(self, filename: str) -> bool:
        """Check if a file should be skipped."""
        if self.skip_hidden and filename.startswith('.'):
            return True
        if filename.endswith('~'):  # Backup files
            return True
        return False
    
    def traverse(self, path: str) -> List[Path]:
        """
        Traverse directory and return list of files.
        
        Args:
            path: Directory path to traverse
            
        Returns:
            List of Path objects for discovered files
        """
        files = []
        
        for root, dirs, filenames in os.walk(path):
            # Filter directories in-place
            dirs[:] = [d for d in dirs if not self.should_skip_directory(d)]
            
            # Process files
            for filename in filenames:
                if not self.should_skip_file(filename):
                    files.append(Path(root) / filename)
        
        return files
    
    def find_files_by_extension(self, path: str, 
                                extensions: Set[str]) -> List[Path]:
        """Find files with specific extensions."""
        files = []
        for file_path in self.traverse(path):
            if file_path.suffix.lower().strip('.') in extensions:
                files.append(file_path)
        return files


class DocumentProcessor(Protocol):
    """
    Protocol defining the interface for document processors.
    Interface Segregation: Minimal interface for processing documents.
    """
    
    async def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process a file and return document data."""
        ...


class TextDocumentProcessor:
    """
    Processes text-based documents.
    Single Responsibility: Handle text file loading with encoding detection.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    async def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process a text file with encoding fallback."""
        # Try different encodings in order
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                return [{
                    "raw_content": content,
                    "url": file_path.name,
                    "metadata": {"encoding": encoding, "source": str(file_path)}
                }]
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                self.logger.debug(f"Failed with {encoding}: {e}")
                continue
        
        # If all encodings fail, try binary fallback
        return self._load_binary_fallback(file_path)
    
    def _load_binary_fallback(self, file_path: Path) -> List[Dict[str, Any]]:
        """Last resort: load as binary and decode with replacements."""
        try:
            content = file_path.read_bytes().decode('utf-8', errors='replace')
            return [{
                "raw_content": content,
                "url": file_path.name,
                "metadata": {"encoding": "binary_fallback", "source": str(file_path)}
            }]
        except Exception as e:
            self.logger.error(f"Binary fallback failed for {file_path}: {e}")
            return []


class StandardDocumentProcessor:
    """
    Processes standard document formats.
    Single Responsibility: Handle standard document formats.
    
    Note: This is a simplified implementation. In production with GPT-Researcher,
    the actual loaders from langchain_community would be used.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        # Map of extensions that would normally use specialized loaders
        self.standard_formats = {
            'pdf', 'doc', 'docx', 'pptx', 'xls', 'xlsx', 
            'csv', 'md', 'html', 'htm'
        }
    
    async def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process a standard document format."""
        ext = file_path.suffix.lower().strip('.')
        
        if ext not in self.standard_formats:
            self.logger.warning(f"Not a standard format: {ext}")
            return []
        
        # For testing/demo purposes, we'll treat these as text files
        # In production, GPT-Researcher would use proper loaders
        if ext in ['md', 'csv', 'html', 'htm']:
            # These are text-based, can read directly
            try:
                content = file_path.read_text(encoding='utf-8')
                return [{
                    "raw_content": content,
                    "url": file_path.name,
                    "metadata": {"format": ext, "source": str(file_path)}
                }]
            except Exception as e:
                self.logger.error(f"Failed to read {file_path}: {e}")
                return []
        else:
            # Binary formats like PDF, DOC would need special handling
            # For now, just return a placeholder indicating they would be processed
            self.logger.info(f"Would process {ext} file with specialized loader: {file_path.name}")
            return [{
                "raw_content": f"[{ext.upper()} content would be extracted here]",
                "url": file_path.name,
                "metadata": {"format": ext, "source": str(file_path), "placeholder": True}
            }]


class LoaderStrategy(ABC):
    """
    Abstract base for loader strategies.
    Strategy Pattern: Different loading strategies for different file types.
    """
    
    @abstractmethod
    async def load(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load a file and return documents."""
        pass


class TextLoaderStrategy(LoaderStrategy):
    """Strategy for loading text files."""
    
    def __init__(self, processor: TextDocumentProcessor):
        self.processor = processor
    
    async def load(self, file_path: Path) -> List[Dict[str, Any]]:
        return await self.processor.process(file_path)


class StandardLoaderStrategy(LoaderStrategy):
    """Strategy for loading standard document formats."""
    
    def __init__(self, processor: StandardDocumentProcessor):
        self.processor = processor
    
    async def load(self, file_path: Path) -> List[Dict[str, Any]]:
        return await self.processor.process(file_path)


class LoaderFactory:
    """
    Factory for creating appropriate loaders based on file type.
    Factory Pattern: Create loaders without specifying exact classes.
    """
    
    def __init__(self, registry: FileFormatRegistry,
                 logger: Optional[logging.Logger] = None):
        self.registry = registry
        self.logger = logger or logging.getLogger(__name__)
        self.text_processor = TextDocumentProcessor(self.logger)
        self.standard_processor = StandardDocumentProcessor(self.logger)
    
    def create_loader(self, file_path: Path) -> LoaderStrategy:
        """Create appropriate loader for a file."""
        ext = file_path.suffix.lower().strip('.')
        category = self.registry.get_category(ext)
        
        # Standard formats use specialized loaders
        if category == FileCategory.STANDARD:
            return StandardLoaderStrategy(self.standard_processor)
        
        # Everything else uses text loader
        if self.registry.is_supported(ext):
            return TextLoaderStrategy(self.text_processor)
        
        # Unknown formats also try text loader
        self.logger.info(f"Unknown format {ext}, attempting text loader")
        return TextLoaderStrategy(self.text_processor)


class DocumentLoaderOrchestrator:
    """
    Orchestrates the document loading process using all components.
    Facade Pattern: Simplified interface to complex subsystem.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.registry = FileFormatRegistry()
        self.traverser = DirectoryTraverser()
        self.factory = LoaderFactory(self.registry, self.logger)
    
    async def load_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load a single file."""
        loader = self.factory.create_loader(file_path)
        return await loader.load(file_path)
    
    async def load_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Load all files from a directory."""
        import asyncio
        
        files = self.traverser.traverse(directory)
        tasks = [self.load_file(f) for f in files]
        
        all_docs = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_docs.extend(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Error loading file: {result}")
        
        return all_docs
    
    async def load_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Load multiple specific files."""
        import asyncio
        
        tasks = [self.load_file(Path(f)) for f in file_paths]
        
        all_docs = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_docs.extend(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Error loading file: {result}")
        
        return all_docs
    
    @property
    def supported_formats(self) -> int:
        """Get number of supported formats."""
        return self.registry.total_formats
    
    def get_format_info(self, extension: str) -> Optional[FileFormat]:
        """Get information about a file format."""
        return self.registry.get_format(extension)