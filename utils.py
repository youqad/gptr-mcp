import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Simple in-memory store for research results and caches
# Keys are typically f"{report_source}:{topic}"
research_store: Dict[str, Dict[str, Any]] = {}

def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "data": data
    }

def handle_exception(exc: Exception, context: str) -> Dict[str, Any]:
    logger.exception(f"{context} failed: {exc}")
    return {
        "ok": False,
        "error": {
            "context": context,
            "type": exc.__class__.__name__,
            "message": str(exc)
        }
    }

def get_researcher_by_id(researchers: Dict[str, Any], research_id: str) -> Tuple[bool, Optional[Any], Dict[str, Any]]:
    if research_id in researchers:
        return True, researchers[research_id], {}
    error = {
        "ok": False,
        "error": {
            "context": "Lookup",
            "type": "NotFound",
            "message": f"Researcher with ID '{research_id}' not found"
        }
    }
    return False, None, error

def validate_doc_path(report_source: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate DOC_PATH for local/hybrid research modes.
    
    Args:
        report_source: Research mode ('web', 'local', or 'hybrid')
        
    Returns:
        Tuple of (is_valid, doc_path, error_dict)
    """
    if report_source not in ["local", "hybrid"]:
        return True, None, None
        
    doc_path = os.getenv("DOC_PATH")
    if not doc_path:
        return False, None, handle_exception(
            ValueError("DOC_PATH environment variable not set. Required for local/hybrid research."),
            "DOC_PATH Validation"
        )
    if not os.path.exists(doc_path):
        return False, None, handle_exception(
            ValueError(f"DOC_PATH directory does not exist: {doc_path}"),
            "DOC_PATH Validation"
        )
    
    logger.info(f"Using local documents from: {doc_path}")
    return True, doc_path, None

def _normalize_source_item(item: Any) -> Dict[str, Any]:
    """Normalize source items from various formats to consistent dictionary."""
    # Accept dict-like or object-like source items
    if isinstance(item, dict):
        title = item.get("title") or item.get("name") or item.get("page_title") or ""
        url = item.get("url") or item.get("link") or item.get("source_url") or ""
        snippet = item.get("snippet") or item.get("summary") or item.get("content") or ""
        score = item.get("score") or item.get("relevance") or None
    else:
        # Fallback to attribute access
        title = getattr(item, "title", "") or getattr(item, "name", "")
        url = getattr(item, "url", "") or getattr(item, "link", "")
        snippet = getattr(item, "snippet", "") or getattr(item, "summary", "") or getattr(item, "content", "")
        score = getattr(item, "score", None)

    result: Dict[str, Any] = {"title": title, "url": url}
    if snippet:
        result["snippet"] = snippet
    if score is not None:
        result["score"] = score
    return result

def format_sources_for_response(sources: Optional[List[Any]]) -> List[Dict[str, Any]]:
    if not sources:
        return []
    return [_normalize_source_item(s) for s in sources]

def format_context_with_sources(topic: str, context: str, sources: Optional[List[Any]]) -> str:
    lines = [
        f"Topic: {topic}",
        "",
        "Context:",
        context.strip() if context else "(no context)",
        ""
    ]
    formatted_sources = format_sources_for_response(sources)
    if formatted_sources:
        lines.append("Sources:")
        for i, s in enumerate(formatted_sources, start=1):
            title = s.get("title", "(untitled)") or "(untitled)"
            url = s.get("url", "")
            snippet = s.get("snippet", "")
            if url and snippet:
                lines.append(f"{i}. {title} — {url}\n   {snippet}")
            elif url:
                lines.append(f"{i}. {title} — {url}")
            else:
                lines.append(f"{i}. {title}")
    else:
        lines.append("Sources: none")
    return "\n".join(lines)

def store_research_results(query: str, context: str, sources: Optional[List[Any]], source_urls: Optional[List[str]], report_source: str = "web") -> None:
    """
    Store research results using a cache key compatible with resource endpoint.
    
    Args:
        query: The research query/topic
        context: Research context/findings
        sources: List of source documents
        source_urls: List of source URLs
        report_source: Research mode ('web', 'local', 'hybrid')
    """
    # Normalize the topic key
    topic_key = query.strip()
    cache_key = f"{report_source}:{topic_key}"
    research_store[cache_key] = {
        "context": format_context_with_sources(topic_key, context, sources),
        "sources": sources or [],
        "source_urls": source_urls or []
    }

def create_research_prompt(topic: str, goal: str, report_format: str = "research_report") -> str:
    return (
        "You are GPT-Researcher. Conduct research and produce a concise, well-structured report.\n\n"
        f"Topic: {topic}\n"
        f"Goal: {goal}\n"
        f"Report Format: {report_format}\n\n"
        "Guidelines:\n"
        "- Be factual and cite sources inline where applicable.\n"
        "- Include a brief summary and key takeaways.\n"
        "- Prefer reputable sources; avoid speculation.\n"
        "- Use bullet points where helpful.\n"
    )