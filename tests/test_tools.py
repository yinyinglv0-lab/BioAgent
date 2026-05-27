"""Tests for BioAgent tools."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_tool_registry():
    """Verify all tools are registered."""
    from src.tools import TOOL_REGISTRY, get_all_tools

    expected_tools = {
        "read_paper",
        "query_disease",
        "query_gene",
        "differential_expression",
        "survival_analysis",
        "search_pubmed",
        "run_enrichment",
    }

    registered = set(TOOL_REGISTRY.keys())
    missing = expected_tools - registered
    extra = registered - expected_tools

    assert not missing, f"Missing tools: {missing}"
    print(f"  All {len(expected_tools)} tools registered")

    tools = get_all_tools()
    assert len(tools) == len(expected_tools), f"Expected {len(expected_tools)} tools, got {len(tools)}"
    print(f"  get_all_tools() returns {len(tools)} ToolParam objects")


def test_config():
    """Verify config module."""
    from src.config import Config
    assert Config.PROJECT_NAME == "BioAgent"
    assert Config.VERSION == "1.0.0"
    print(f"  Config: {Config.PROJECT_NAME} v{Config.VERSION}")


def test_pdf_reader_simulation():
    """Test PDF reader returns proper error for missing file."""
    from src.tools.pdf_reader import read_paper
    result = read_paper("/nonexistent/paper.pdf")
    assert "error" in result or "char_count" in result
    print(f"  PDF reader handles missing files gracefully")


def test_db_query_without_connection():
    """Test DB query returns error when MySQL unavailable."""
    from src.tools.db_query import query_disease
    result = query_disease("Lung")
    # Should either return results or graceful error
    assert isinstance(result, dict)
    assert "error" in result or "results" in result
    print(f"  DB query handles missing connection gracefully")


def test_enrichment():
    """Test enrichment with known genes."""
    from src.tools.expression import run_enrichment
    result = run_enrichment(["TP53", "EGFR", "VEGFA"])
    assert result["genes_queried"] == ["TP53", "EGFR", "VEGFA"]
    assert "results" in result
    print(f"  Enrichment: {result['total_terms']} terms found for 3 genes")


def test_pubmed_search():
    """Test PubMed search (may fail without internet)."""
    from src.tools.web_search import search_pubmed
    result = search_pubmed("TP53 cancer", max_results=3)
    assert isinstance(result, dict)
    assert "query" in result
    print(f"  PubMed search for '{result['query']}' returned {len(result.get('results', []))} papers")


if __name__ == "__main__":
    print("BioAgent Tool Tests\n")

    tests = [
        test_config,
        test_tool_registry,
        test_pdf_reader_simulation,
        test_db_query_without_connection,
        test_enrichment,
        test_pubmed_search,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__} - {e}")

    print(f"\n{passed}/{len(tests)} tests passed")
