#!/usr/bin/env python
"""
GPT-Researcher MCP Setup Verification Script
Run this to verify the MCP is properly configured and ready to use.
"""

import os
import sys
import subprocess
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

def check_mark(condition):
    """Return appropriate status mark"""
    return "✅" if condition else "❌"

def info_mark():
    """Return info mark"""
    return "ℹ️ "

def main():
    print("=" * 70)
    print("GPT-RESEARCHER MCP SETUP VERIFICATION")
    print("=" * 70)
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"\n✅ Loaded environment from: {env_file}")
    
    errors = []
    warnings = []
    
    # 1. Check virtual environment
    print("\n1. PYTHON ENVIRONMENT")
    venv_path = Path(__file__).parent / ".venv"
    venv_exists = venv_path.exists()
    print(f"   {check_mark(venv_exists)} Virtual environment: {venv_path}")
    if not venv_exists:
        errors.append("Virtual environment not found. Run: uv venv && uv pip install -r requirements.txt")
    
    # 2. Check required packages
    print("\n2. DEPENDENCIES")
    try:
        import fastmcp
        print(f"   ✅ fastmcp: {getattr(fastmcp, '__version__', 'installed')}")
    except ImportError:
        print("   ❌ fastmcp: NOT INSTALLED")
        errors.append("fastmcp not installed")
    
    try:
        import gpt_researcher
        print("   ✅ gpt_researcher: installed")
    except ImportError:
        print("   ❌ gpt_researcher: NOT INSTALLED")
        errors.append("gpt_researcher not installed")
    
    try:
        import dotenv  # noqa
        print("   ✅ python-dotenv: installed")
    except ImportError:
        print("   ❌ python-dotenv: NOT INSTALLED")
        errors.append("python-dotenv not installed")

    # 2b. Check local helper modules required by server.py
    print("\n2b. LOCAL MODULES")
    base_dir = Path(__file__).parent
    utils_ok = (base_dir / "utils.py").exists()
    docloader_ok = (base_dir / "document_loader.py").exists()
    print(f"   {check_mark(utils_ok)} utils.py present")
    print(f"   {check_mark(docloader_ok)} document_loader.py present")
    if not utils_ok:
        errors.append("utils.py missing (required by server.py)")
    if not docloader_ok:
        warnings.append("document_loader.py missing; server will fallback to default loader")

    # 3. Check environment variables
    print("\n3. ENVIRONMENT VARIABLES")
    
    # Required
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"   ✅ OPENAI_API_KEY: Set ({len(openai_key)} characters)")
    else:
        print("   ❌ OPENAI_API_KEY: NOT SET (REQUIRED!)")
        errors.append("OPENAI_API_KEY environment variable not set")
    
    # Optional but recommended
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        print(f"   ✅ TAVILY_API_KEY: Set ({len(tavily_key)} characters)")
    else:
        print(f"   {info_mark()}TAVILY_API_KEY: Not set (optional for web search)")
        warnings.append("TAVILY_API_KEY not set - web search may be limited")
    
    # Local document path
    doc_path = os.getenv("DOC_PATH")
    if doc_path:
        if os.path.exists(doc_path):
            file_count = sum(len(files) for _, _, files in os.walk(doc_path))
            print(f"   ✅ DOC_PATH: {doc_path} ({file_count} files)")
        else:
            print(f"   ⚠️  DOC_PATH: Set but directory not found: {doc_path}")
            warnings.append(f"DOC_PATH directory not found: {doc_path}")
    else:
        print(f"   {info_mark()}DOC_PATH: Not set (local document search disabled)")
    
    # 4. SERVER FUNCTIONALITY
    print("\n4. SERVER FUNCTIONALITY")
    server_import_ok = False
    try:
        # Add parent to path for import
        sys.path.insert(0, str(Path(__file__).parent))
        import server  # type: ignore
        from server import mcp  # type: ignore
        server_import_ok = True
        print(f"   ✅ Server imports successfully")
        print(f"   ✅ Server name: {mcp.name}")
    except Exception as e:
        print(f"   ❌ Server import failed: {e}")
        errors.append(f"Server import error: {e}")
    
    # 4b. Check tools and resources registration by scanning server.py (static check)
    print("\n4b. TOOL AND RESOURCE REGISTRATION (static scan)")
    try:
        server_path = Path(__file__).parent / "server.py"
        src = server_path.read_text(encoding="utf-8")

        def has_tool(name: str) -> bool:
            # Look for an @mcp.tool() decorator above a function with given name
            pattern = rf"@mcp\.tool\(\)\s*\nasync\s+def\s+{re.escape(name)}\("
            return re.search(pattern, src) is not None

        def has_resource(pattern_str: str) -> bool:
            pat = re.escape(pattern_str)
            return re.search(rf"@mcp\.resource\(\"{pat}\"\)", src) is not None

        tools_expected = [
            "deep_research",
            "quick_search",
            "write_report",
            "get_research_sources",
            "get_research_context",
        ]
        tools_ok = {t: has_tool(t) for t in tools_expected}
        for t, ok in tools_ok.items():
            print(f"   {check_mark(ok)} tool: {t}")
        missing_tools = [t for t, ok in tools_ok.items() if not ok]
        if missing_tools:
            warnings.append(f"Missing tool definitions (static check): {', '.join(missing_tools)}")

        resource_ok = has_resource("research://{topic}")
        print(f"   {check_mark(resource_ok)} resource: research://{{topic}}")
        if not resource_ok:
            warnings.append("Resource research://{topic} not found (static check)")
    except Exception as e:
        print(f"   ⚠️  Could not statically analyze server.py: {e}")
        warnings.append("Static analysis of tool/resource registration failed")

    # 5. MCP INTEGRATION (project-level and user-level config)
    print("\n5. MCP INTEGRATION")
    # Project mcp.json
    project_mcp_json = Path("/Users/youdar/Documents/PKM/MCPs/mcp.json")
    if project_mcp_json.exists():
        try:
            with open(project_mcp_json, "r", encoding="utf-8") as f:
                config = json.load(f)
            srv = config.get("mcpServers", {}).get("gpt-researcher")
            if srv:
                print("   ✅ Project mcp.json: gpt-researcher entry found")
                # Validate directory and entrypoint
                args: List[str] = srv.get("args", [])
                dir_ok = False
                file_ok = False
                for i, arg in enumerate(args):
                    if arg == "--directory" and i + 1 < len(args):
                        dir_path = Path(args[i + 1])
                        dir_ok = dir_path.exists()
                if "server.py" in args:
                    file_index = args.index("server.py")
                    # Ensure server.py exists in specified directory
                    dir_path = None
                    for i, arg in enumerate(args):
                        if arg == "--directory" and i + 1 < len(args):
                            dir_path = Path(args[i + 1])
                            break
                    if dir_path:
                        file_ok = (dir_path / "server.py").exists()
                print(f"   {check_mark(dir_ok)} gpt-researcher directory exists")
                print(f"   {check_mark(file_ok)} server.py exists at configured path")
                if not dir_ok or not file_ok:
                    errors.append("Project mcp.json misconfigured: directory or server.py missing")
            else:
                print("   ❌ Project mcp.json: gpt-researcher entry NOT found")
                errors.append("Add gpt-researcher server block to project mcp.json")
        except Exception as e:
            print(f"   ❌ Could not parse project mcp.json: {e}")
            errors.append(f"Invalid project mcp.json: {e}")
    else:
        print("   ❌ Project mcp.json not found at /Users/youdar/Documents/PKM/MCPs/mcp.json")
        errors.append("Project mcp.json missing")

    # User-level configuration (best-effort)
    user_mcp_json = Path.home() / ".claude.json"
    if user_mcp_json.exists():
        try:
            with open(user_mcp_json, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "gpt-researcher" in config.get("mcpServers", {}):
                print("   ✅ Registered in Claude Code configuration (~/.claude.json)")
            else:
                print("   ⚠️  Not found in ~/.claude.json")
                warnings.append("Register gpt-researcher in your Claude config or sync it")
        except Exception as e:
            print(f"   ⚠️  Could not verify Claude Code config at ~/.claude.json: {e}")
    else:
        print(f"   {info_mark()}Claude Code config not found at ~/.claude.json (may not be installed)")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    if errors:
        print("\n❌ ERRORS FOUND:")
        for error in errors:
            print(f"   • {error}")
        print("\n⚠️  The MCP will NOT work properly until these are fixed.")
    elif warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   • {warning}")
        print("\n✅ The MCP should work but some features may be limited.")
    else:
        print("\n✅ ALL CHECKS PASSED!")
        print("The GPT-Researcher MCP is fully configured and ready to use.")
    
    print("\n" + "=" * 70)
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())