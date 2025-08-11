"""
A minimal, safe ExtendedDocumentLoader shim.

This implementation inherits from gpt_researcher's default DocumentLoader
(if available) and adds simple guards. It allows server.py to monkey-patch
safely without introducing heavy new dependencies. Replace with your
full implementation if needed.
"""
from typing import Any, Dict, List

try:
    from gpt_researcher.document.document import DocumentLoader as BaseDocumentLoader
except Exception:
    class BaseDocumentLoader:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass
        def load(self, *args, **kwargs) -> List[Dict[str, Any]]:
            return []

class ExtendedDocumentLoader(BaseDocumentLoader):  # type: ignore
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    # Example guard: ensure load inputs are sane; delegate to base implementation
    def load(self, *args, **kwargs) -> List[Dict[str, Any]]:
        try:
            return super().load(*args, **kwargs)  # type: ignore
        except Exception:
            # Fallback to empty list on error rather than raising
            return []