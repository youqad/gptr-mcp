#!/usr/bin/env python3
"""
Test that the server starts correctly with the refactored document loader
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        # Test importing the refactored loader
        from document_loader_refactored import ExtendedDocumentLoader
        print("✓ document_loader_refactored imported successfully")
        
        # Test that it has the expected attributes
        loader = ExtendedDocumentLoader("/tmp")
        print(f"✓ ExtendedDocumentLoader instantiated (supports {loader.supported_formats} formats)")
        
        # Test importing server
        import server
        print("✓ server module imported successfully")
        
        # Check that monkey-patching worked
        import gpt_researcher.document.document
        if gpt_researcher.document.document.DocumentLoader == ExtendedDocumentLoader:
            print("✓ Monkey-patching successful")
        else:
            print("✗ Monkey-patching failed")
            return False
            
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_environment():
    """Test environment setup."""
    print("\nTesting environment...")
    
    # Check for .env file
    if os.path.exists(".env"):
        print("✓ .env file exists")
    else:
        print("⚠ .env file not found (will use environment variables)")
    
    # Check for API keys
    if os.getenv("OPENAI_API_KEY"):
        print("✓ OPENAI_API_KEY is set")
    else:
        print("⚠ OPENAI_API_KEY not set")
    
    if os.getenv("TAVILY_API_KEY"):
        print("✓ TAVILY_API_KEY is set")
    else:
        print("⚠ TAVILY_API_KEY not set (optional)")
    
    # Check DOC_PATH
    doc_path = os.getenv("DOC_PATH")
    if doc_path:
        if os.path.exists(doc_path):
            print(f"✓ DOC_PATH is set and exists: {doc_path}")
        else:
            print(f"⚠ DOC_PATH is set but doesn't exist: {doc_path}")
    else:
        print("ℹ DOC_PATH not set (local document search disabled)")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING SERVER STARTUP WITH REFACTORED LOADER")
    print("=" * 60)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test environment
    if not test_environment():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL STARTUP TESTS PASSED")
        print("The server should start correctly with the refactored loader.")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please fix the issues before starting the server.")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())