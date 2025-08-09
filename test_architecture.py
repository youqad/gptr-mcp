#!/usr/bin/env python3
"""
Test script for the refactored document loader architecture
Tests both the clean components and the backward-compatible wrapper
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our components
from document_loader_components import (
    FileFormatRegistry,
    FileCategory,
    DirectoryTraverser,
    TextDocumentProcessor,
    StandardDocumentProcessor,
    LoaderFactory,
    DocumentLoaderOrchestrator
)
from document_loader_refactored import ExtendedDocumentLoader

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_file_format_registry():
    """Test the FileFormatRegistry component."""
    print("\n=== Testing FileFormatRegistry ===")
    
    registry = FileFormatRegistry()
    
    # Test format counts
    print(f"Total formats: {registry.total_formats}")
    assert registry.total_formats > 160, f"Expected 160+ formats, got {registry.total_formats}"
    
    # Test specific formats
    test_formats = {
        'tex': FileCategory.ACADEMIC,
        'py': FileCategory.PROGRAMMING,
        'json': FileCategory.CONFIGURATION,
        'pdf': FileCategory.STANDARD,
        'hs': FileCategory.PROGRAMMING,
        'rs': FileCategory.PROGRAMMING
    }
    
    for ext, expected_category in test_formats.items():
        fmt = registry.get_format(ext)
        assert fmt is not None, f"Format {ext} not found"
        assert fmt.category == expected_category, f"Format {ext} has wrong category: {fmt.category}"
        print(f"✓ {ext}: {fmt.category.value} - {fmt.description}")
    
    # Test category retrieval
    academic_formats = registry.get_extensions_by_category(FileCategory.ACADEMIC)
    print(f"\nAcademic formats ({len(academic_formats)}): {', '.join(sorted(academic_formats)[:10])}...")
    
    prog_formats = registry.get_extensions_by_category(FileCategory.PROGRAMMING)
    print(f"Programming formats ({len(prog_formats)}): {', '.join(sorted(prog_formats)[:10])}...")
    
    print("✅ FileFormatRegistry tests passed!")


def test_directory_traverser():
    """Test the DirectoryTraverser component."""
    print("\n=== Testing DirectoryTraverser ===")
    
    traverser = DirectoryTraverser()
    
    # Test skip rules
    assert traverser.should_skip_directory('.git'), ".git should be skipped"
    assert traverser.should_skip_directory('node_modules'), "node_modules should be skipped"
    assert not traverser.should_skip_directory('src'), "src should not be skipped"
    
    assert traverser.should_skip_file('.hidden'), "Hidden files should be skipped"
    assert traverser.should_skip_file('backup~'), "Backup files should be skipped"
    assert not traverser.should_skip_file('main.py'), "Normal files should not be skipped"
    
    print("✅ DirectoryTraverser tests passed!")


async def test_text_processor():
    """Test the TextDocumentProcessor component."""
    print("\n=== Testing TextDocumentProcessor ===")
    
    processor = TextDocumentProcessor(logger)
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test Python file\nprint('Hello, World!')")
        test_file = f.name
    
    try:
        # Process the file
        docs = await processor.process(Path(test_file))
        assert len(docs) > 0, "Should have loaded document"
        assert "Hello, World!" in docs[0]['raw_content'], "Content not found"
        print(f"✓ Loaded text file: {len(docs[0]['raw_content'])} chars")
    finally:
        os.unlink(test_file)
    
    print("✅ TextDocumentProcessor tests passed!")


async def test_loader_factory():
    """Test the LoaderFactory component."""
    print("\n=== Testing LoaderFactory ===")
    
    registry = FileFormatRegistry()
    factory = LoaderFactory(registry, logger)
    
    # Test strategy selection
    test_cases = [
        ('test.pdf', 'StandardLoaderStrategy'),
        ('test.py', 'TextLoaderStrategy'),
        ('test.tex', 'TextLoaderStrategy'),
        ('test.unknown', 'TextLoaderStrategy'),  # Unknown should default to text
    ]
    
    for filename, expected_strategy in test_cases:
        loader = factory.create_loader(Path(filename))
        strategy_name = loader.__class__.__name__
        assert strategy_name == expected_strategy, f"{filename} got {strategy_name}, expected {expected_strategy}"
        print(f"✓ {filename} → {strategy_name}")
    
    print("✅ LoaderFactory tests passed!")


async def test_orchestrator():
    """Test the DocumentLoaderOrchestrator component."""
    print("\n=== Testing DocumentLoaderOrchestrator ===")
    
    orchestrator = DocumentLoaderOrchestrator(logger)
    
    # Test format count
    print(f"Supported formats: {orchestrator.supported_formats}")
    assert orchestrator.supported_formats > 160
    
    # Create test files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various test files
        test_files = {
            'test.py': "# Python test\nprint('test')",
            'test.tex': "\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}",
            'test.hs': "-- Haskell test\nmain = putStrLn \"test\"",
            'test.json': '{"test": "data"}',
            'README.md': "# Test README\nThis is a test.",
        }
        
        for filename, content in test_files.items():
            path = Path(tmpdir) / filename
            path.write_text(content)
        
        # Test loading directory
        docs = await orchestrator.load_directory(tmpdir)
        print(f"✓ Loaded {len(docs)} documents from directory")
        assert len(docs) == len(test_files), f"Expected {len(test_files)} docs, got {len(docs)}"
        
        # Test loading specific files
        file_paths = [str(Path(tmpdir) / name) for name in ['test.py', 'test.tex']]
        docs = await orchestrator.load_files(file_paths)
        print(f"✓ Loaded {len(docs)} specific files")
        assert len(docs) == 2
    
    print("✅ DocumentLoaderOrchestrator tests passed!")


async def test_extended_loader():
    """Test the refactored ExtendedDocumentLoader."""
    print("\n=== Testing ExtendedDocumentLoader (Refactored) ===")
    
    # Create test files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure
        test_files = {
            'main.py': "def main():\n    print('Main function')",
            'lib.hs': "module Lib where\nimport Data.List",
            'paper.tex': "\\section{Introduction}\nThis is a test paper.",
            'config.yaml': "database:\n  host: localhost",
            'data.json': '{"users": ["alice", "bob"]}',
            '.hidden': "This should be skipped",
            'subdir/module.rs': "fn main() {\n    println!(\"Rust code\");\n}",
        }
        
        # Create files
        for filepath, content in test_files.items():
            path = Path(tmpdir) / filepath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        
        # Test loading directory
        loader = ExtendedDocumentLoader(tmpdir)
        print(f"Loader initialized with {loader.supported_formats} formats")
        
        docs = await loader.load()
        print(f"✓ Loaded {len(docs)} documents")
        
        # Check that hidden file was skipped
        urls = [doc['url'] for doc in docs]
        assert '.hidden' not in urls, "Hidden file should be skipped"
        
        # Check that all visible files were loaded
        expected_files = ['main.py', 'lib.hs', 'paper.tex', 'config.yaml', 'data.json', 'module.rs']
        for expected in expected_files:
            found = any(expected in url for url in urls)
            assert found, f"Expected file {expected} not found in results"
            print(f"  ✓ Found {expected}")
        
        # Test loading single file
        single_file = str(Path(tmpdir) / 'main.py')
        loader = ExtendedDocumentLoader(single_file)
        docs = await loader.load()
        assert len(docs) == 1
        assert "Main function" in docs[0]['raw_content']
        print("✓ Single file loading works")
        
        # Test loading multiple specific files
        files = [str(Path(tmpdir) / 'main.py'), str(Path(tmpdir) / 'lib.hs')]
        loader = ExtendedDocumentLoader(files)
        docs = await loader.load()
        assert len(docs) == 2
        print("✓ Multiple file loading works")
    
    print("✅ ExtendedDocumentLoader tests passed!")


async def test_integration():
    """Integration test with realistic file structure."""
    print("\n=== Integration Test ===")
    
    # Create a realistic project structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create project structure
        structure = {
            'src/main.py': 'import utils\n\ndef main():\n    pass',
            'src/utils.py': 'def helper():\n    return True',
            'tests/test_main.py': 'import pytest\n\ndef test_main():\n    pass',
            'docs/README.md': '# Project Documentation',
            'docs/paper.tex': '\\documentclass{article}\n\\title{Research}',
            'config/settings.yaml': 'debug: true\nport: 8080',
            '.git/config': 'Should be skipped',
            'node_modules/lib.js': 'Should be skipped',
            '__pycache__/cache.pyc': 'Should be skipped',
        }
        
        for filepath, content in structure.items():
            path = Path(tmpdir) / filepath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        
        # Test with orchestrator
        orchestrator = DocumentLoaderOrchestrator(logger)
        docs = await orchestrator.load_directory(tmpdir)
        
        # Should load only non-skipped files
        expected_count = 6  # All files except .git, node_modules, __pycache__
        assert len(docs) == expected_count, f"Expected {expected_count} docs, got {len(docs)}"
        
        # Verify content
        contents = ' '.join(doc['raw_content'] for doc in docs)
        assert 'import utils' in contents
        assert 'Research' in contents
        assert 'debug: true' in contents
        assert 'Should be skipped' not in contents
        
        print(f"✓ Integration test: loaded {len(docs)} documents correctly")
        print("  Files loaded:")
        for doc in docs:
            print(f"    - {doc['url']}")
    
    print("✅ Integration test passed!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING REFACTORED DOCUMENT LOADER ARCHITECTURE")
    print("=" * 60)
    
    # Test individual components
    test_file_format_registry()
    test_directory_traverser()
    await test_text_processor()
    await test_loader_factory()
    await test_orchestrator()
    
    # Test the refactored loader
    await test_extended_loader()
    
    # Integration test
    await test_integration()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())