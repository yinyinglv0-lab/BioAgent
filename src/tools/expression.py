"""Differential expression analysis tool."""

import logging
import os
import subprocess
import tempfile

import pymysql

from ..config import config as cfg
from . import register
from .db_query import _get_connection, _safe_query

logger = logging.getLogger(__name__)


@register(
    name="differential_expression",
    description="Query differentially expressed genes for a specific disease. Set padj and log2FC thresholds to filter results. Returns up/down regulated genes with statistics.",
    input_schema={
        "type": "object",
        "properties": {
            "disease_name": {
                "type": "string",
                "description": "Name of the disease to analyze (partial match supported)",
            },
            "padj_threshold": {
                "type": "number",
                "description": "Adjusted p-value cutoff (default: 0.05)",
                "default": 0.05,
            },
            "log2fc_threshold": {
                "type": "number",
                "description": "Absolute log2 fold change cutoff (default: 1.0)",
                "default": 1.0,
            },
        },
        "required": ["disease_name"],
    },
)
def differential_expression(
    disease_name: str,
    padj_threshold: float = 0.05,
    log2fc_threshold: float = 1.0,
) -> dict:
    """Query differentially expressed genes for a disease."""
    sql = """
        SELECT g.gene_symbol, g.gene_id,
               ROUND(AVG(e.log2fc), 3) AS log2fc,
               ROUND(MIN(e.padj), 6) AS padj,
               ROUND(AVG(e.fpkm_value), 2) AS avg_fpkm,
               CASE WHEN AVG(e.log2fc) > 0 THEN 'Up' ELSE 'Down' END AS direction
        FROM expression e
        JOIN sample s ON e.sample_id = s.sample_id
        JOIN gene g ON e.gene_id = g.gene_id
        JOIN disease d ON s.disease_id = d.disease_id
        WHERE d.name LIKE %s AND s.group_type = 'case'
          AND e.padj IS NOT NULL
        GROUP BY g.gene_id, g.gene_symbol
        HAVING padj < %s AND ABS(log2fc) > %s
        ORDER BY padj ASC
        LIMIT 50
    """
    result = _safe_query(sql, (f"%{disease_name}%", padj_threshold, log2fc_threshold))
    if "error" in result:
        return result

    rows = result.get("results", [])
    up_count = sum(1 for r in rows if r["direction"] == "Up")
    down_count = len(rows) - up_count
    return {
        "disease_query": disease_name,
        "padj_threshold": padj_threshold,
        "log2fc_threshold": log2fc_threshold,
        "total_degs": len(rows),
        "up_regulated": up_count,
        "down_regulated": down_count,
        "top_up": [r for r in rows if r["direction"] == "Up"][:5],
        "top_down": [r for r in rows if r["direction"] == "Down"][:5],
        "all_degs": rows[:30],
    }


@register(
    name="run_enrichment",
    description="Run basic GO/KEGG enrichment analysis on a list of gene symbols. Returns enriched terms with p-values.",
    input_schema={
        "type": "object",
        "properties": {
            "genes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of gene symbols to analyze",
            },
        },
        "required": ["genes"],
    },
)
def run_enrichment(genes: list[str]) -> dict:
    """Perform enrichment analysis on a gene list using pre-computed annotation data."""

    # Simulated GO/KEGG annotations for demo purposes
    # In production, this would use clusterProfiler R package or g:Profiler API
    go_annotations = {
        "TP53": [
            ("GO:0006915", "apoptotic process", 1e-8),
            ("GO:0007049", "cell cycle", 1e-6),
            ("GO:0006281", "DNA repair", 1e-5),
        ],
        "EGFR": [
            ("GO:0007169", "transmembrane receptor protein tyrosine kinase signaling", 1e-10),
            ("GO:0043066", "negative regulation of apoptotic process", 1e-7),
        ],
        "KRAS": [
            ("GO:0007265", "Ras protein signal transduction", 1e-8),
            ("GO:0008283", "cell population proliferation", 1e-6),
        ],
        "VEGFA": [
            ("GO:0001525", "angiogenesis", 1e-12),
            ("GO:0001666", "response to hypoxia", 1e-8),
        ],
        "MYC": [
            ("GO:0006355", "regulation of transcription", 1e-8),
            ("GO:0008283", "cell population proliferation", 1e-7),
        ],
        "BRCA1": [
            ("GO:0006281", "DNA repair", 1e-10),
            ("GO:0006974", "cellular response to DNA damage stimulus", 1e-8),
        ],
        "PTEN": [
            ("GO:0008285", "negative regulation of cell population proliferation", 1e-8),
            ("GO:0016310", "phosphorylation", 1e-6),
        ],
    }

    results = []
    for gene in genes:
        if gene.upper() in go_annotations:
            for go_id, term, pval in go_annotations[gene.upper()]:
                results.append({
                    "gene": gene.upper(),
                    "go_id": go_id,
                    "term": term,
                    "p_value": pval,
                })

    if not results:
        return {
            "genes_queried": genes,
            "message": "No pre-computed annotations available for these genes. In production, this would call g:Profiler or clusterProfiler.",
            "results": [],
        }

    return {"genes_queried": genes, "results": results, "total_terms": len(results)}
