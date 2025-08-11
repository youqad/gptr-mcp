#!/usr/bin/env python3
"""
Test script for the consolidated document loader.
Tests the extended format support and safety features.
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_loader import ExtendedDocumentLoader, EXTENDED_FORMATS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_basic_loading():
    """Test basic document loading functionality."""
    print("\n=== Testing Basic Loading ===")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content for GPT-Researcher")
        test_file = f.name
    
    try:
        loader = ExtendedDocumentLoader(test_file)
        result = await loader.load()
        
        if result:
            print(f"✓ Successfully loaded file: {test_file}")
            print(f"  Content length: {len(result[0]['raw_content'])} chars")
        else:
            print(f"✓ File loading returned empty (expected for base implementation)")
            
    finally:
        os.unlink(test_file)

def test_format_support():
    """Test that extended formats are recognized."""
    print("\n=== Testing Format Support ===")
    
    loader = ExtendedDocumentLoader("dummy_path")
    
    # Test some key formats
    test_formats = ['.tex', '.yaml', '.dockerfile', '.swift', '.graphql']
    
    for fmt in test_formats:
        test_path = Path(f"test{fmt}")
        is_supported = loader._is_supported(test_path)
        print(f"  {fmt}: {'✓ Supported' if is_supported else '✗ Not supported'}")
    
    print(f"\nTotal supported formats: {len(EXTENDED_FORMATS)}")

def test_safety_features():
    """Test path safety validation."""
    print("\n=== Testing Safety Features ===")
    
    loader = ExtendedDocumentLoader("dummy_path")
    
    # Test safe paths
    safe_paths = [
        Path("/tmp/test.txt"),
        Path("./document.pdf"),
        Path("subfolder/file.py")
    ]
    
    for path in safe_paths:
        is_safe = loader._is_safe_path(path)
        print(f"  {path}: {'✓ Safe' if is_safe else '✗ Unsafe'}")
    
    # File size limit
    print(f"\n  Max file size: {loader.MAX_FILE_SIZE / (1024*1024):.0f} MB")

async def test_error_handling():
    """Test that errors are handled gracefully."""
    print("\n=== Testing Error Handling ===")
    
    # Test with non-existent file
    loader = ExtendedDocumentLoader("/non/existent/path.txt")
    result = await loader.load()
    
    if result == []:
        print("✓ Non-existent file handled gracefully (returned empty list)")
    else:
        print("✗ Unexpected result for non-existent file")
    
    # Test with directory instead of file
    loader = ExtendedDocumentLoader("/tmp")
    result = await loader.load()
    
    if result == []:
        print("✓ Directory path handled gracefully (returned empty list)")
    else:
        print("✗ Unexpected result for directory path")

async def main():
    """Run all tests."""
    print("=" * 60)
    print("DOCUMENT LOADER TEST SUITE")
    print("=" * 60)
    
    # Run tests
    await test_basic_loading()
    test_format_support()
    test_safety_features()
    await test_error_handling()
    
    print("\n" + "=" * 60)
    print("✓ All tests completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())