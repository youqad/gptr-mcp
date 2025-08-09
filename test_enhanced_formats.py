#!/usr/bin/env python
"""
Test script to verify enhanced document loader supports various file formats
"""

import asyncio
import tempfile
import os
from document_loader_enhanced import EnhancedDocumentLoader

async def test_formats():
    """Test loading various file formats"""
    
    # Create temporary directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Testing in {tmpdir}")
        
        # Create test files of various formats
        test_files = {
            'test.tex': r'\documentclass{article}\begin{document}LaTeX content\end{document}',
            'test.py': 'def hello():\n    print("Python code")',
            'test.hs': 'main :: IO ()\nmain = putStrLn "Haskell code"',
            'test.ml': 'let hello () = print_endline "OCaml code"',
            'test.rs': 'fn main() {\n    println!("Rust code");\n}',
            'test.go': 'package main\nimport "fmt"\nfunc main() {\n    fmt.Println("Go code")\n}',
            'test.json': '{"test": "JSON data"}',
            'test.yaml': 'test: YAML data',
            'test.md': '# Markdown\nThis is markdown content',
            'test.txt': 'Plain text content',
            'README': 'README file without extension',
        }
        
        # Write test files
        for filename, content in test_files.items():
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
        
        # Test loading
        loader = EnhancedDocumentLoader(tmpdir)
        docs = await loader.load()
        
        print(f"\nLoaded {len(docs)} documents:")
        for doc in docs:
            filename = doc['url']
            content_preview = doc['raw_content'][:50] + '...' if len(doc['raw_content']) > 50 else doc['raw_content']
            print(f"  - {filename}: {content_preview}")
        
        # Verify all expected files were loaded
        loaded_files = {doc['url'] for doc in docs}
        expected_files = set(test_files.keys())
        
        if loaded_files == expected_files:
            print("\n✅ All test files were successfully loaded!")
        else:
            missing = expected_files - loaded_files
            if missing:
                print(f"\n❌ Missing files: {missing}")
            extra = loaded_files - expected_files
            if extra:
                print(f"\n❌ Unexpected files: {extra}")
        
        return len(docs) == len(test_files)

if __name__ == "__main__":
    success = asyncio.run(test_formats())
    exit(0 if success else 1)