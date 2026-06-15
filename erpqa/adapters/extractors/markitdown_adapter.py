from __future__ import annotations

from pathlib import Path

from .base import RawExtraction


name = "markitdown"
supported_extensions = frozenset({".pdf", ".docx", ".pptx", ".html"})
tier = "OPTIONAL"


def available() -> bool:
    try:
        import markitdown  # noqa: F401
    except Exception:
        return False
    return True


def extract(path: Path) -> RawExtraction:
    if not available():
        return RawExtraction(path.as_posix(), "optional_unavailable", [], "low", ["optional dependency markitdown is not installed"], name)
    from markitdown import MarkItDown

    result = MarkItDown().convert(str(path))
    text = getattr(result, "text_content", "") or ""
    records = [{"type": "paragraph", "text": line.strip(), "line": index} for index, line in enumerate(text.splitlines(), 1) if line.strip()]
    return RawExtraction(path.as_posix(), "text", records, "medium", [], name)

