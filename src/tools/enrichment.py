"""Gene enrichment analysis tool - GO/KEGG/Reactome via g:Profiler REST API.

g:Profiler (https://biit.cs.ut.ee/gprofiler/) is a public functional
profiling service - free, no API key required. It returns enriched terms
with hypergeometric p-values corrected for multiple testing.
"""

import json
import logging
import ssl
import urllib.parse
import urllib.request

from . import register

logger = logging.getLogger(__name__)

# Use certifi's CA bundle: some hosts (e.g. g:Profiler) fail verification
# against the default CA list on Windows.
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None  # fall back to system default context

GPROFILER_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"

# Source presets: GO biological process / molecular function / cellular
# component, KEGG pathways, Reactome pathways.
GPROFILER_SOURCES = ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]


def _gprofiler_call(query: list[str], organism: str, threshold: float) -> dict:
    """POST a query to g:Profiler and return the parsed JSON result."""
    payload = json.dumps({
        "organism": organism,
        "query": query,
        "sources": GPROFILER_SOURCES,
        "user_threshold": threshold,
    }).encode("utf-8")
    req = urllib.request.Request(
        GPROFILER_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"g:Profiler call failed: {e}")
        return {"error": str(e)}


@register(
    name="run_enrichment",
    description=(
        "Run functional enrichment analysis on a gene list via g:Profiler. "
        "Returns enriched GO terms, KEGG pathways and Reactome pathways with "
        "p-values, FDR, and the specific input genes matching each term."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "genes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of gene symbols to analyze (e.g., ['TP53','EGFR','KRAS'])",
            },
            "organism": {
                "type": "string",
                "enum": ["hsapiens", "mmusculus", "rnorvegicus"],
                "description": "Organism for enrichment (default: hsapiens = human)",
                "default": "hsapiens",
            },
        },
        "required": ["genes"],
    },
)
def run_enrichment(genes: list[str], organism: str = "hsapiens") -> dict:
    """Run functional enrichment via g:Profiler REST API."""
    if not genes:
        return {"error": "Empty gene list"}

    data = _gprofiler_call(genes, organism, threshold=0.05)

    if "error" in data:
        return {
            "genes_queried": genes,
            "error": data["error"],
            "fallback": "Try query_string_enrichment (STRING) instead.",
        }

    results = []
    for term in data.get("result", []):
        results.append({
            "source": term.get("source", "N/A"),
            "term_id": term.get("native", "N/A"),
            "term": term.get("name", "N/A"),
            "p_value": term.get("p_value"),
            "intersection_size": term.get("intersection_size", 0),
            "query_size": term.get("query_size", 0),
            "evidence_codes": term.get("intersections", []),
        })

    # Sort by p-value, keep the most significant terms per source
    results.sort(key=lambda x: (x["p_value"] is None, x["p_value"] or 1.0))
    top_by_source: dict[str, list] = {}
    for r in results:
        top_by_source.setdefault(r["source"], [])
        if len(top_by_source[r["source"]]) < 5:
            top_by_source[r["source"]].append(r)

    return {
        "database": "g:Profiler",
        "organism": organism,
        "genes_queried": genes,
        "total_terms": len(results),
        "top_terms": top_by_source,
        "url": "https://biit.cs.ut.ee/gplink/l/"
        + urllib.parse.quote(",".join(genes)),
    }
