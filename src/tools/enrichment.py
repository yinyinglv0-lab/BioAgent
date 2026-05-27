"""Gene enrichment analysis tool - GO/KEGG annotations."""

from . import register


@register(
    name="run_enrichment",
    description="Run GO/KEGG enrichment analysis on a gene list. Returns enriched biological process terms with p-values.",
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
    """Perform enrichment using pre-computed GO annotations."""

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
            "message": "No pre-computed annotations for these genes. For real enrichment, use g:Profiler or clusterProfiler.",
            "results": [],
        }

    return {"genes_queried": genes, "results": results, "total_terms": len(results)}
