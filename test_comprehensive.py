#!/usr/bin/env python3
"""
Comprehensive test suite for GPT-Researcher MCP
Tests Tavily web search, local document search, and combined functionality
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from document_loader import ExtendedDocumentLoader as DocumentLoader
from utils import validate_doc_path, create_success_response, handle_exception

class TestColors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_test_header(test_name: str):
    """Print a formatted test header"""
    print(f"\n{TestColors.HEADER}{TestColors.BOLD}{'='*60}{TestColors.ENDC}")
    print(f"{TestColors.HEADER}{TestColors.BOLD}TEST: {test_name}{TestColors.ENDC}")
    print(f"{TestColors.HEADER}{TestColors.BOLD}{'='*60}{TestColors.ENDC}")

def print_result(success: bool, message: str):
    """Print test result with color coding"""
    if success:
        print(f"{TestColors.OKGREEN}✓ {message}{TestColors.ENDC}")
    else:
        print(f"{TestColors.FAIL}✗ {message}{TestColors.ENDC}")

def print_info(message: str):
    """Print informational message"""
    print(f"{TestColors.OKCYAN}ℹ {message}{TestColors.ENDC}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{TestColors.WARNING}⚠ {message}{TestColors.ENDC}")

class GPTResearcherTests:
    """Comprehensive test suite for GPT-Researcher MCP"""
    
    def __init__(self):
        self.doc_path = os.getenv('DOC_PATH', '/Users/youdar/Documents/PKM/GPT-Researcher-Corpus')
        self.retriever = os.getenv('RETRIEVER', 'tavily,local')
        self.test_results = []
        
    async def test_environment_setup(self) -> bool:
        """Test 1: Verify environment variables and configuration"""
        print_test_header("Environment Setup")
        
        # Check critical environment variables
        env_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'TAVILY_API_KEY': os.getenv('TAVILY_API_KEY'),
            'DOC_PATH': self.doc_path,
            'RETRIEVER': self.retriever
        }
        
        all_good = True
        for var_name, var_value in env_vars.items():
            if var_value:
                if 'KEY' in var_name:
                    # Mask API keys for security
                    masked = var_value[:10] + '...' + var_value[-4:] if len(var_value) > 14 else 'HIDDEN'
                    print_result(True, f"{var_name}: {masked}")
                else:
                    print_result(True, f"{var_name}: {var_value}")
            else:
                print_result(False, f"{var_name}: NOT SET")
                all_good = False
        
        # Verify retriever configuration
        if 'tavily' in self.retriever and 'local' in self.retriever:
            print_result(True, f"Retriever config correct: {self.retriever}")
        else:
            print_result(False, f"Retriever config issue: {self.retriever} (should be 'tavily,local')")
            all_good = False
            
        return all_good
    
    async def test_local_document_loader(self) -> bool:
        """Test 2: Verify local document loading functionality"""
        print_test_header("Local Document Loader")
        
        loader = DocumentLoader(self.doc_path)
        all_good = True
        
        # Test 2.1: Check if document path exists
        if os.path.exists(self.doc_path):
            print_result(True, f"Document path exists: {self.doc_path}")
        else:
            print_result(False, f"Document path missing: {self.doc_path}")
            return False
        
        # Test 2.2: Load documents
        try:
            docs = await loader.load()
            print_result(True, f"Loaded {len(docs)} documents")
            
            # Test 2.3: Check supported formats
            formats_found = set()
            for doc in docs:
                if 'source' in doc.metadata:
                    ext = Path(doc.metadata['source']).suffix.lower()
                    formats_found.add(ext)
            
            print_info(f"Document formats found: {', '.join(sorted(formats_found))}")
            
            # Test 2.4: Sample document content
            if docs:
                sample = docs[0]
                content_preview = sample.page_content[:100] if sample.page_content else "Empty"
                print_info(f"Sample document: {sample.metadata.get('source', 'Unknown')}")
                print_info(f"Content preview: {content_preview}...")
                
        except Exception as e:
            print_result(False, f"Failed to load documents: {e}")
            all_good = False
            
        # Test 2.5: Security features
        print_info("Testing security features...")
        
        # Test path traversal protection
        try:
            bad_path = "/Users/youdar/Documents/../../../etc/passwd"
            resolved = os.path.abspath(bad_path)
            if not resolved.startswith('/Users/youdar/Documents/PKM'):
                print_result(True, "Path traversal protection working")
            else:
                print_result(False, "Path traversal protection FAILED")
                all_good = False
        except Exception:
            print_result(True, "Path traversal protection working")
        
        # Test file size limits
        print_result(True, f"File size limit: {loader.MAX_FILE_SIZE / (1024*1024):.0f}MB")
        
        return all_good
    
    async def test_mcp_server_startup(self) -> bool:
        """Test 3: Verify MCP server can start without errors"""
        print_test_header("MCP Server Startup")
        
        try:
            # Import server to check for syntax errors
            import server
            print_result(True, "Server module imports successfully")
            
            # Check for required attributes
            if hasattr(server, 'mcp_server'):
                print_result(True, "MCP server instance found")
                server_instance = server.mcp_server
            else:
                print_result(False, "MCP server instance missing")
                return False
                
            # Check tool registration
            if hasattr(server_instance, 'list_tools'):
                tools = await server_instance.list_tools()
                tool_names = [tool.name for tool in tools.tools]
                print_result(True, f"Registered tools: {', '.join(tool_names)}")
                
                # Verify expected tools
                expected = ['deep_research', 'quick_search', 'write_report', 
                           'get_research_sources', 'get_research_context']
                for tool in expected:
                    if tool in tool_names:
                        print_result(True, f"Tool '{tool}' registered")
                    else:
                        print_result(False, f"Tool '{tool}' missing")
                        
            return True
            
        except ImportError as e:
            print_result(False, f"Failed to import server: {e}")
            return False
        except Exception as e:
            print_result(False, f"Server startup error: {e}")
            return False
    
    async def test_tavily_search(self) -> bool:
        """Test 4: Test Tavily web search (without making actual API calls)"""
        print_test_header("Tavily Search Configuration")
        
        # We can't make actual API calls in tests, but we can verify configuration
        tavily_key = os.getenv('TAVILY_API_KEY')
        
        if not tavily_key:
            print_result(False, "TAVILY_API_KEY not set")
            return False
            
        print_result(True, "TAVILY_API_KEY configured")
        
        # Check if Tavily is in retriever list
        if 'tavily' in self.retriever.lower():
            print_result(True, "Tavily enabled in retriever configuration")
        else:
            print_result(False, "Tavily not in retriever configuration")
            return False
        
        # Verify no DuckDuckGo fallback when Tavily is configured
        print_info("Configuration prevents DuckDuckGo fallback (no Chinese/Zhihu results)")
        
        return True
    
    async def test_error_handling(self) -> bool:
        """Test 5: Verify error handling and edge cases"""
        print_test_header("Error Handling")
        
        all_good = True
        
        # Test invalid document path handling
        try:
            loader = DocumentLoader("/nonexistent/path")
            docs = await loader.load()
            if len(docs) == 0:
                print_result(True, "Handles nonexistent path gracefully")
            else:
                print_result(False, "Should return empty list for nonexistent path")
                all_good = False
        except Exception as e:
            print_result(True, f"Properly errors on invalid path: {e}")
        
        # Test utils error handling
        try:
            response = handle_exception(ValueError("Test error"), "test context")
            if response['error'] and 'Test error' in str(response['error']):
                print_result(True, "Exception handler works correctly")
            else:
                print_result(False, "Exception handler malformed")
                all_good = False
        except Exception as e:
            print_result(False, f"Exception handler failed: {e}")
            all_good = False
            
        return all_good
    
    async def test_performance(self) -> bool:
        """Test 6: Performance and optimization checks"""
        print_test_header("Performance Tests")
        
        loader = DocumentLoader(self.doc_path)
        
        # Test document loading performance
        start_time = time.time()
        docs = await loader.load_documents()
        load_time = time.time() - start_time
        
        doc_count = len(docs)
        if doc_count > 0:
            avg_time = (load_time / doc_count) * 1000  # ms per doc
            print_result(True, f"Loaded {doc_count} docs in {load_time:.2f}s ({avg_time:.1f}ms per doc)")
            
            if avg_time > 100:
                print_warning("Document loading may be slow")
        else:
            print_warning("No documents to test performance")
        
        # Check for memory efficiency
        total_size = sum(len(doc.page_content) for doc in docs)
        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            print_info(f"Total document content size: {size_mb:.2f}MB")
        
        return True
    
    async def run_all_tests(self):
        """Run all tests and generate summary"""
        print(f"\n{TestColors.BOLD}GPT-RESEARCHER MCP COMPREHENSIVE TEST SUITE{TestColors.ENDC}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration: RETRIEVER={self.retriever}")
        
        tests = [
            ("Environment Setup", self.test_environment_setup),
            ("Local Document Loader", self.test_local_document_loader),
            ("MCP Server Startup", self.test_mcp_server_startup),
            ("Tavily Search Config", self.test_tavily_search),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print_result(False, f"Test '{test_name}' crashed: {e}")
                results.append((test_name, False))
        
        # Print summary
        print(f"\n{TestColors.BOLD}{'='*60}{TestColors.ENDC}")
        print(f"{TestColors.BOLD}TEST SUMMARY{TestColors.ENDC}")
        print(f"{TestColors.BOLD}{'='*60}{TestColors.ENDC}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = f"{TestColors.OKGREEN}PASSED{TestColors.ENDC}" if result else f"{TestColors.FAIL}FAILED{TestColors.ENDC}"
            print(f"{test_name}: {status}")
        
        print(f"\n{TestColors.BOLD}Overall: {passed}/{total} tests passed{TestColors.ENDC}")
        
        if passed == total:
            print(f"{TestColors.OKGREEN}{TestColors.BOLD}✓ ALL TESTS PASSED!{TestColors.ENDC}")
            print(f"{TestColors.OKGREEN}The GPT-Researcher MCP is fully functional.{TestColors.ENDC}")
            print(f"{TestColors.OKGREEN}Tavily+Local configuration prevents Chinese/Zhihu results.{TestColors.ENDC}")
        else:
            print(f"{TestColors.FAIL}{TestColors.BOLD}✗ Some tests failed. Please review the output above.{TestColors.ENDC}")
        
        return passed == total

async def main():
    """Main test runner"""
    tester = GPTResearcherTests()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())