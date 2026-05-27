"""PDF reader tool - extract text and analyze scientific papers."""

import logging
from . import register

logger = logging.getLogger(__name__)


@register(
    name="read_paper",
    description="Read and extract key information from a scientific PDF paper. Returns title, abstract, methods, results, and key findings.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the PDF file",
            },
            "sections": {
                "type": "string",
                "enum": ["all", "abstract", "methods", "results", "conclusion"],
                "description": "Which sections to extract",
                "default": "all",
            },
        },
        "required": ["file_path"],
    },
)
def read_paper(file_path: str, sections: str = "all") -> dict:
    """Extract text from a PDF paper with section detection."""
    import os
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        import fitz  # PyMuPDF
    except ImportError:
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            full_text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except ImportError:
            return {
                "error": "No PDF library available. Install PyMuPDF or pypdf.",
                "file_path": file_path,
            }
    else:
        doc = fitz.open(file_path)
        full_text = "\n".join(page.get_text() for page in doc)
        doc.close()

    if not full_text.strip():
        return {"error": "Could not extract text from PDF", "file_path": file_path}

    # Basic section detection
    result = {
        "file_path": file_path,
        "char_count": len(full_text),
        "page_count": len(full_text.split("\x0c")) if "\x0c" in full_text else 1,
    }

    # Identify key sections using regex patterns
    import re

    title_match = re.search(r"^(.+?)(?:\n|$)", full_text.strip())
    if title_match:
        result["title"] = title_match.group(1).strip()[:300]

    abstract_match = re.search(
        r"(?:Abstract|ABSTRACT|摘要)\s*\n(.*?)(?:\n(?:Introduction|INTRODUCTION|Background|BACKGROUND)|$)",
        full_text, re.DOTALL | re.IGNORECASE
    )
    if abstract_match:
        result["abstract"] = abstract_match.group(1).strip()[:2000]

    # Count genes mentioned
    gene_pattern = re.findall(r"\b([A-Z]{2,}[0-9]*[A-Z]*)\b", full_text)
    result["potential_gene_symbols"] = list(set(gene_pattern))[:50]

    result["text_preview"] = full_text[:3000]
    return result
