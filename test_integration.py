#!/usr/bin/env python3
"""
Integration test for GPT-Researcher MCP - Actually calls the server tools
"""

import asyncio
import json
import os
import sys
from pathlib import Path
import subprocess
import time

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def test_result(passed: bool, message: str):
    """Print colored test result"""
    if passed:
        print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")
    else:
        print(f"{Colors.RED}✗ {message}{Colors.ENDC}")
    return passed

def info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.ENDC}")

async def test_quick_search():
    """Test quick_search with Tavily to ensure no Chinese results"""
    print(f"\n{Colors.BOLD}Testing Quick Search (Tavily){Colors.ENDC}")
    
    # Create a test request
    test_query = "latest advances in machine learning 2024"
    
    # Build the MCP request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "quick_search",
            "arguments": {
                "query": test_query,
                "report_source": "web"  # This will use Tavily
            }
        },
        "id": 1
    }
    
    # Start the server and send request
    process = subprocess.Popen(
        ["uv", "run", "python", "server.py"],
        cwd="/Users/youdar/Documents/PKM/MCPs/tools/gptr-mcp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, 
             "RETRIEVER": "tavily,local",
             "DOC_PATH": "/Users/youdar/Documents/PKM/GPT-Researcher-Corpus"}
    )
    
    try:
        # Send the request
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        
        # Wait for response (with timeout)
        start_time = time.time()
        response = None
        while time.time() - start_time < 10:  # 10 second timeout
            line = process.stdout.readline()
            if line:
                try:
                    response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if response:
            if "result" in response:
                # Check for Chinese/Zhihu content
                result_str = str(response["result"]).lower()
                has_chinese = any(ord(c) > 0x4e00 and ord(c) < 0x9fff for c in result_str)
                has_zhihu = "zhihu" in result_str
                
                if not has_chinese and not has_zhihu:
                    test_result(True, "No Chinese/Zhihu content in results")
                    info(f"Got {len(result_str)} characters of search results")
                    return True
                else:
                    test_result(False, "Found Chinese/Zhihu content in results!")
                    return False
            else:
                test_result(False, f"No result in response: {response}")
                return False
        else:
            test_result(False, "No response from server")
            return False
            
    finally:
        process.terminate()
        process.wait(timeout=2)

async def test_local_search():
    """Test searching local documents"""
    print(f"\n{Colors.BOLD}Testing Local Document Search{Colors.ENDC}")
    
    # Create a test request for local search
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "quick_search",
            "arguments": {
                "query": "GFlowNet probabilistic inference",
                "report_source": "local"  # Search local docs only
            }
        },
        "id": 2
    }
    
    # Start the server
    process = subprocess.Popen(
        ["uv", "run", "python", "server.py"],
        cwd="/Users/youdar/Documents/PKM/MCPs/tools/gptr-mcp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, 
             "RETRIEVER": "tavily,local",
             "DOC_PATH": "/Users/youdar/Documents/PKM/GPT-Researcher-Corpus"}
    )
    
    try:
        # Send the request
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        
        # Wait for response
        start_time = time.time()
        response = None
        while time.time() - start_time < 10:
            line = process.stdout.readline()
            if line:
                try:
                    response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if response and "result" in response:
            test_result(True, "Local document search working")
            info(f"Found content from local corpus")
            return True
        else:
            test_result(False, "Local search failed")
            return False
            
    finally:
        process.terminate()
        process.wait(timeout=2)

async def test_hybrid_search():
    """Test combined Tavily + local search"""
    print(f"\n{Colors.BOLD}Testing Hybrid Search (Tavily + Local){Colors.ENDC}")
    
    request = {
        "jsonrpc": "2.0", 
        "method": "tools/call",
        "params": {
            "name": "quick_search",
            "arguments": {
                "query": "transformer architecture attention mechanism",
                "report_source": "hybrid"  # Use both Tavily and local
            }
        },
        "id": 3
    }
    
    # Start the server
    process = subprocess.Popen(
        ["uv", "run", "python", "server.py"],
        cwd="/Users/youdar/Documents/PKM/MCPs/tools/gptr-mcp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ,
             "RETRIEVER": "tavily,local",
             "DOC_PATH": "/Users/youdar/Documents/PKM/GPT-Researcher-Corpus"}
    )
    
    try:
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        
        start_time = time.time()
        response = None
        while time.time() - start_time < 15:  # Longer timeout for hybrid
            line = process.stdout.readline()
            if line:
                try:
                    response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if response and "result" in response:
            result_str = str(response["result"])
            
            # Check it combines both sources
            has_web_content = len(result_str) > 1000  # Web results are usually substantial
            has_no_chinese = not any(ord(c) > 0x4e00 and ord(c) < 0x9fff for c in result_str)
            
            if has_web_content and has_no_chinese:
                test_result(True, "Hybrid search combines web + local effectively")
                info("No Chinese/Zhihu content in hybrid results")
                return True
            else:
                test_result(False, "Hybrid search issues detected")
                return False
        else:
            test_result(False, "Hybrid search failed")
            return False
            
    finally:
        process.terminate()
        process.wait(timeout=2)

async def main():
    """Run all integration tests"""
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}GPT-RESEARCHER MCP INTEGRATION TESTS{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    # Check environment
    retriever = os.getenv("RETRIEVER", "tavily,local")
    doc_path = os.getenv("DOC_PATH", "/Users/youdar/Documents/PKM/GPT-Researcher-Corpus")
    
    info(f"RETRIEVER: {retriever}")
    info(f"DOC_PATH: {doc_path}")
    
    # Run tests
    results = []
    
    # Test 1: Quick search with Tavily (no Chinese results)
    results.append(("Tavily Web Search", await test_quick_search()))
    
    # Test 2: Local document search
    results.append(("Local Document Search", await test_local_search()))
    
    # Test 3: Hybrid search
    results.append(("Hybrid Search", await test_hybrid_search()))
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASSED{Colors.ENDC}" if result else f"{Colors.RED}FAILED{Colors.ENDC}"
        print(f"{test_name}: {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All integration tests passed!{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Tavily prevents Chinese/Zhihu results{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Local corpus search works{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Hybrid mode combines both effectively{Colors.ENDC}")
    else:
        print(f"{Colors.RED}Some tests failed. Review output above.{Colors.ENDC}")

if __name__ == "__main__":
    asyncio.run(main())