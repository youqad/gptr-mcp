"""
Minimal ExtendedDocumentLoader for GPT-Researcher MCP.

This is a safe wrapper that inherits from gpt_researcher's default DocumentLoader
and provides fallback behavior if the library isn't available.
"""
from typing import Any, Dict, List

try:
    from gpt_researcher.document.document import DocumentLoader as BaseDocumentLoader
except Exception:
    # Fallback if gpt_researcher isn't installed
    class BaseDocumentLoader:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass
        def load(self, *args, **kwargs) -> List[Dict[str, Any]]:
            return []

class ExtendedDocumentLoader(BaseDocumentLoader):  # type: ignore
    """
    Extended document loader with safe fallback behavior.
    Inherits from gpt_researcher's DocumentLoader when available.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def load(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Load documents with error handling.
        Falls back to empty list on any error to prevent crashes.
        """
        try:
            return super().load(*args, **kwargs)  # type: ignore
        except Exception:
            # Safe fallback - return empty list rather than crashing
            return []

# For backward compatibility
DocumentLoader = ExtendedDocumentLoader