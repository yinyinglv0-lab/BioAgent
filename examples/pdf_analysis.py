#!/usr/bin/env python3
"""
Example: PDF Paper Analysis

Demonstrates how to use BioAgent's paper reading capability.
Drop a PDF and get a structured summary.

Usage:
    python examples/pdf_analysis.py /path/to/paper.pdf
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.pdf_reader import read_paper


def analyze_pdf(file_path: str):
    """Extract and display paper information."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    print(f"\nAnalyzing: {path.name}")
    print("-" * 50)

    result = read_paper(file_path)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print(f"Pages: {result.get('page_count', 'N/A')}")
    print(f"Characters: {result.get('char_count', 'N/A'):,}")

    if "title" in result:
        print(f"\nTitle: {result['title']}")

    if "abstract" in result:
        print(f"\nAbstract Preview:")
        print(result["abstract"][:500])

    if "potential_gene_symbols" in result:
        genes = result["potential_gene_symbols"][:20]
        print(f"\nPotential Gene Symbols ({len(result['potential_gene_symbols'])} total):")
        print(", ".join(sorted(genes)[:20]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/pdf_analysis.py <path_to_pdf>")
        sys.exit(1)

    analyze_pdf(sys.argv[1])
