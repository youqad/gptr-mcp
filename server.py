"""
GPT Researcher MCP Server

This script implements an MCP server for GPT Researcher, allowing AI assistants
to conduct web research and generate reports via the MCP protocol.
"""

import os
import sys
import uuid
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from fastmcp import FastMCP
from gpt_researcher import GPTResearcher

# Load environment variables
load_dotenv()

from utils import (
    research_store,
    create_success_response, 
    handle_exception,
    get_researcher_by_id, 
    format_sources_for_response,
    format_context_with_sources, 
    store_research_results,
    create_research_prompt,
    validate_doc_path
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] - %(message)s',
)

logger = logging.getLogger(__name__)

# Try to replace the DocumentLoader class with our extended version if available
try:
    import gpt_researcher.document.document as gr_doc_document
    import gpt_researcher.skills.researcher as gr_skills_researcher
    import gpt_researcher.document as gr_document
    from document_loader_refactored import ExtendedDocumentLoader

    # Replace with our ExtendedDocumentLoader if import succeeded
    gr_doc_document.DocumentLoader = ExtendedDocumentLoader
    if hasattr(gr_skills_researcher, "DocumentLoader"):
        gr_skills_researcher.DocumentLoader = ExtendedDocumentLoader
    if hasattr(gr_document, "DocumentLoader"):
        gr_document.DocumentLoader = ExtendedDocumentLoader
    logger.info("ExtendedDocumentLoader successfully patched into gpt_researcher")
except Exception as e:
    logger.warning(f"ExtendedDocumentLoader not available; using default gpt_researcher loader. Reason: {e}")

# Initialize FastMCP server
mcp = FastMCP(
    name="GPT Researcher"
)

# Initialize researchers dictionary
if not hasattr(mcp, "researchers"):
    mcp.researchers = {}


@mcp.resource("research://{topic}")
async def research_resource(topic: str) -> str:
    """
    Provide research context for a given topic directly as a resource.
    
    This allows LLMs to access web-sourced or local document information without explicit function calls.
    
    Args:
        topic: The research topic or query (can include "[local]" or "[hybrid]" prefix for mode)
        
    Returns:
        String containing the research context with source information
    """
    # Parse report_source from topic if specified
    report_source = "web"
    actual_topic = topic
    
    if topic.startswith("[local]"):
        report_source = "local"
        actual_topic = topic[7:].strip()
    elif topic.startswith("[hybrid]"):
        report_source = "hybrid"
        actual_topic = topic[8:].strip()
    
    # Check if we've already researched this topic
    cache_key = f"{report_source}:{actual_topic}"
    if cache_key in research_store:
        logger.info(f"Returning cached {report_source} research for topic: {actual_topic}")
        return research_store[cache_key]["context"]
    
    # If not, conduct the research
    logger.info(f"Conducting new {report_source} research for resource on topic: {actual_topic}")
    
    # Check DOC_PATH for local/hybrid modes
    is_valid, doc_path, error = validate_doc_path(report_source)
    if not is_valid:
        return f"Error: DOC_PATH not configured properly for {report_source} research"
    
    # Initialize GPT Researcher with report_source
    researcher = GPTResearcher(query=actual_topic, report_source=report_source)
    
    try:
        # Conduct the research
        await researcher.conduct_research()
        
        # Get the context and sources
        context = researcher.get_research_context()
        sources = researcher.get_research_sources()
        source_urls = researcher.get_source_urls()
        
        # Format with sources included
        formatted_context = format_context_with_sources(actual_topic, context, sources)
        formatted_context = f"[Research Mode: {report_source.upper()}]\n\n{formatted_context}"
        
        # Store for future use with mode-specific key
        research_store[cache_key] = {
            "context": formatted_context,
            "sources": sources,
            "source_urls": source_urls
        }
        
        return formatted_context
    except Exception as e:
        return f"Error conducting {report_source} research on '{actual_topic}': {str(e)}"


@mcp.tool()
async def deep_research(query: str, report_source: str = "web") -> Dict[str, Any]:
    """
    Conduct deep research on a given query using GPT Researcher. 
    Can search the web, local documents, or both (hybrid mode).
    
    Args:
        query: The research query or topic
        report_source: Research source - "web" (default), "local" (uses DOC_PATH env var), or "hybrid" (both)
        
    Returns:
        Dict containing research status, ID, and the actual research context and sources
        that can be used directly by LLMs for context enrichment
    """
    # Validate report_source
    valid_sources = ["web", "local", "hybrid"]
    if report_source not in valid_sources:
        return handle_exception(
            ValueError(f"Invalid report_source: {report_source}. Must be one of {valid_sources}"),
            "Research"
        )
    
    # Check DOC_PATH for local/hybrid modes
    is_valid, doc_path, error = validate_doc_path(report_source)
    if not is_valid:
        return error
    
    logger.info(f"Conducting {report_source} research on query: {query}...")
    
    # Generate a unique ID for this research session
    research_id = str(uuid.uuid4())
    
    # Initialize GPT Researcher with report_source
    researcher = GPTResearcher(query=query, report_source=report_source)
    
    # Start research
    try:
        await researcher.conduct_research()
        mcp.researchers[research_id] = researcher
        logger.info(f"Research completed for ID: {research_id}")
        
        # Get the research context and sources
        context = researcher.get_research_context()
        sources = researcher.get_research_sources()
        source_urls = researcher.get_source_urls()
        
        # Store in the research store for the resource API with correct report_source key
        store_research_results(query, context, sources, source_urls, report_source=report_source)
        
        return create_success_response({
            "research_id": research_id,
            "query": query,
            "report_source": report_source,
            "source_count": len(sources),
            "context": context,
            "sources": format_sources_for_response(sources),
            "source_urls": source_urls
        })
    except Exception as e:
        return handle_exception(e, "Research")


@mcp.tool()
async def quick_search(query: str, report_source: str = "web") -> Dict[str, Any]:
    """
    Perform a quick search on a given query and return search results with snippets.
    This optimizes for speed over quality and is useful when an LLM doesn't need in-depth
    information on a topic.
    
    Args:
        query: The search query
        report_source: Search source - "web" (default), "local" (uses DOC_PATH env var), or "hybrid" (both)
        
    Returns:
        Dict containing search results and snippets
    """
    # Validate report_source
    valid_sources = ["web", "local", "hybrid"]
    if report_source not in valid_sources:
        return handle_exception(
            ValueError(f"Invalid report_source: {report_source}. Must be one of {valid_sources}"),
            "Quick search"
        )
    
    # Check DOC_PATH for local/hybrid modes
    is_valid, doc_path, error = validate_doc_path(report_source)
    if not is_valid:
        return error
    
    logger.info(f"Performing quick {report_source} search on query: {query}...")
    
    # Generate a unique ID for this search session
    search_id = str(uuid.uuid4())
    
    # Initialize GPT Researcher with report_source
    researcher = GPTResearcher(query=query, report_source=report_source)
    
    try:
        # Perform quick search
        search_results = await researcher.quick_search(query=query)
        mcp.researchers[search_id] = researcher
        logger.info(f"Quick {report_source} search completed for ID: {search_id}")
        
        return create_success_response({
            "search_id": search_id,
            "query": query,
            "report_source": report_source,
            "result_count": len(search_results) if search_results else 0,
            "search_results": search_results
        })
    except Exception as e:
        return handle_exception(e, "Quick search")


@mcp.tool()
async def write_report(research_id: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a report based on previously conducted research.
    
    Args:
        research_id: The ID of the research session from deep_research
        custom_prompt: Optional custom prompt for report generation
        
    Returns:
        Dict containing the report content and metadata
    """
    success, researcher, error = get_researcher_by_id(mcp.researchers, research_id)
    if not success:
        return error
    
    logger.info(f"Generating report for research ID: {research_id}")
    
    try:
        # Generate report
        report = await researcher.write_report(custom_prompt=custom_prompt)
        
        # Get additional information
        sources = researcher.get_research_sources()
        costs = researcher.get_costs()
        
        return create_success_response({
            "report": report,
            "source_count": len(sources),
            "costs": costs
        })
    except Exception as e:
        return handle_exception(e, "Report generation")


@mcp.tool()
async def get_research_sources(research_id: str) -> Dict[str, Any]:
    """
    Get the sources used in the research.
    
    Args:
        research_id: The ID of the research session
        
    Returns:
        Dict containing the research sources
    """
    success, researcher, error = get_researcher_by_id(mcp.researchers, research_id)
    if not success:
        return error
    
    sources = researcher.get_research_sources()
    source_urls = researcher.get_source_urls()
    
    return create_success_response({
        "sources": format_sources_for_response(sources),
        "source_urls": source_urls
    })


@mcp.tool()
async def get_research_context(research_id: str) -> Dict[str, Any]:
    """
    Get the full context of the research.
    
    Args:
        research_id: The ID of the research session
        
    Returns:
        Dict containing the research context
    """
    success, researcher, error = get_researcher_by_id(mcp.researchers, research_id)
    if not success:
        return error
    
    context = researcher.get_research_context()
    
    return create_success_response({
        "context": context
    })


@mcp.prompt()
def research_query(topic: str, goal: str, report_format: str = "research_report") -> str:
    """
    Create a research query prompt for GPT Researcher.
    
    Args:
        topic: The topic to research
        goal: The goal or specific question to answer
        report_format: The format of the report to generate
        
    Returns:
        A formatted prompt for research
    """
    return create_research_prompt(topic, goal, report_format)


def run_server():
    """Run the MCP server using FastMCP's built-in event loop handling."""
    # Check if API keys are set
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found. Please set it in your .env file.")
        return

    # Check and log DOC_PATH for local document research
    doc_path = os.getenv("DOC_PATH")
    if doc_path:
        if os.path.exists(doc_path):
            logger.info(f"Local document path configured: {doc_path}")
            print(f"📚 Local documents available at: {doc_path}")
            # List document count
            try:
                file_count = sum(len(files) for _, _, files in os.walk(doc_path))
                print(f"   Found {file_count} files in corpus")
            except (OSError, ValueError) as e:
                logger.debug(f"Unable to count DOC_PATH files: {e}")
        else:
            logger.warning(f"DOC_PATH set but directory doesn't exist: {doc_path}")
            print(f"⚠️  Warning: DOC_PATH directory not found: {doc_path}")
    else:
        logger.info("DOC_PATH not set - local document research disabled")
        print("ℹ️  Local document research disabled (set DOC_PATH to enable)")

    # Determine transport based on environment
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    # Auto-detect Docker environment
    if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
        transport = "sse"
        logger.info("Docker environment detected, using SSE transport")
    
    # Add startup message
    logger.info(f"Starting GPT Researcher MCP Server with {transport} transport...")
    print(f"🚀 GPT Researcher MCP Server starting with {transport} transport...")
    print("   Check researcher_mcp_server.log for details")

    # Let FastMCP handle the event loop
    try:
        if transport == "stdio":
            logger.info("Using STDIO transport (Claude Desktop compatible)")
            mcp.run(transport="stdio")
        elif transport == "sse":
            mcp.run(transport="sse", host="0.0.0.0", port=8000)
        elif transport == "streamable-http":
            mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        print(f"❌ MCP Server error: {str(e)}")
        return
        
    logger.info("MCP Server stopped")
    print("✅ MCP Server stopped")


if __name__ == "__main__":
    # Use the non-async approach to avoid asyncio nesting issues
    run_server()
