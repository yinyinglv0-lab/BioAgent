"""Tests for BioAgent tools."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_tool_registry():
    """Verify all tools are registered."""
    from src.tools import TOOL_REGISTRY, get_all_tools

    expected_tools = {
        "read_paper", "search_pubmed", "run_enrichment",
        "query_tcga", "query_geo", "query_uniprot",
        "query_ensembl", "query_kegg", "query_clinvar", "query_dbsnp",
    }

    registered = set(TOOL_REGISTRY.keys())
    missing = expected_tools - registered
    unexpected = registered - expected_tools

    assert not missing, f"Missing tools: {missing}"
    if unexpected:
        print(f"  Extra tools (OK): {unexpected}")
    print(f"  All {len(expected_tools)} expected tools registered")
    assert len(get_all_tools()) == len(TOOL_REGISTRY)


def test_config():
    from src.config import Config
    assert Config.PROJECT_NAME == "BioAgent"
    assert Config.VERSION == "1.0.0"
    print(f"  Config OK: {Config.PROJECT_NAME} v{Config.VERSION}")


def test_uniprot():
    from src.tools.external_dbs import query_uniprot
    r = query_uniprot('TP53')
    assert 'results' in r
    assert len(r['results']) > 0
    print(f"  UniProt: {r['results'][0]['protein_name']}")


def test_ensembl():
    from src.tools.external_dbs import query_ensembl
    r = query_ensembl('EGFR')
    assert 'ensembl_id' in r
    print(f"  Ensembl: {r['ensembl_id']}")


def test_geo():
    from src.tools.external_dbs import query_geo
    r = query_geo('cancer')
    assert 'results' in r
    print(f"  GEO: {len(r['results'])} datasets")


def test_pubmed():
    from src.tools.web_search import search_pubmed
    r = search_pubmed('TP53 cancer', 3)
    assert 'query' in r
    print(f"  PubMed: '{r['query']}' => {len(r.get('results', []))} papers")


def test_kegg():
    from src.tools.external_dbs import query_kegg
    r = query_kegg('cell cycle', 'pathway')
    assert 'pathways' in r
    print(f"  KEGG: {len(r['pathways'])} pathways")


if __name__ == "__main__":
    print("BioAgent Tool Tests\n")
    tests = [test_config, test_tool_registry, test_uniprot, test_ensembl, test_geo, test_pubmed, test_kegg]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__} - {e}")
    print(f"\n{passed}/{len(tests)} passed")
