#!/usr/bin/env python3
"""
Example: BioAgent Research Workflow

This script demonstrates how to use BioAgent programmatically
for a complete bioinformatics research query.

Usage:
    python examples/workflow.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import BioAgent
from src.tools.db_query import query_disease, query_gene
from src.tools.expression import differential_expression
from src.tools.survival import survival_analysis
from src.tools.web_search import search_pubmed


def demo_direct_tools():
    """Demonstrate direct tool usage without the LLM (for testing/scripting)."""
    print("=" * 60)
    print("BioAgent - Direct Tool Demo")
    print("=" * 60)

    # 1. Query a disease
    print("\n[1] Querying disease: Lung")
    result = query_disease("Lung")
    if "results" in result:
        for d in result["results"]:
            print(f"  - {d['name']} | Genes: {d.get('gene_count',0)} | Samples: {d.get('sample_count',0)}")
    else:
        print(f"  {result.get('error', 'No results')}")

    # 2. Query a gene
    print("\n[2] Querying gene: TP53")
    result = query_gene("TP53")
    if "results" in result:
        for g in result["results"]:
            print(f"  - {g['gene_symbol']} ({g['chromosome']}) | FPKM case: {g.get('avg_fpkm_case')} | ctrl: {g.get('avg_fpkm_ctrl')}")
            print(f"    Diseases: {g.get('diseases', 'N/A')}")

    # 3. Differential expression
    print("\n[3] Differential expression for Lung Adenocarcinoma")
    result = differential_expression("Lung Adenocarcinoma", padj_threshold=0.05, log2fc_threshold=1.0)
    if "total_degs" in result:
        print(f"  DEGs: {result['total_degs']} (Up: {result['up_regulated']}, Down: {result['down_regulated']})")
        print(f"  Top up: {[g['gene_symbol'] for g in result.get('top_up', [])]}")
        print(f"  Top down: {[g['gene_symbol'] for g in result.get('top_down', [])]}")

    # 4. Survival analysis
    print("\n[4] Survival analysis for Lung Adenocarcinoma")
    result = survival_analysis("Lung Adenocarcinoma")
    if "total_patients" in result:
        print(f"  Patients: {result['total_patients']} | Events: {result['events']} | Censored: {result['censored']}")
        print(f"  Median survival: {result.get('median_survival_days', 'N/A')}")

    # 5. PubMed search
    print("\n[5] PubMed search: SEMA3A ccRCC immunotherapy")
    result = search_pubmed("SEMA3A renal cell carcinoma immunotherapy")
    if "results" in result:
        for paper in result["results"][:3]:
            print(f"  [{paper['year']}] {paper['title'][:100]}...")
            print(f"    {paper['authors']} | {paper['journal']} | PMID:{paper['pmid']}")


def demo_agent_conversation():
    """Demonstrate multi-turn Agent conversation."""
    print("\n\n" + "=" * 60)
    print("BioAgent - LLM Agent Demo")
    print("=" * 60)

    agent = BioAgent()

    queries = [
        "What can you tell me about TP53's role in lung cancer? Check the database.",
        "Are there any differentially expressed genes in lung adenocarcinoma?",
        "What does the survival data look like for lung cancer patients?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n[Q{i}] {query}")
        print("-" * 40)
        response = agent.chat(query)
        print(response[:500])
        print("..." if len(response) > 500 else "")

    agent.reset()


if __name__ == "__main__":
    print("BioAgent Workflow Demo\n")

    try:
        demo_direct_tools()
    except Exception as e:
        print(f"Direct tool demo skipped (database may not be available): {e}")

    print("\n\nTo use the LLM agent, set ANTHROPIC_API_KEY in .env file.")
    print("Then run: python -m src.cli")
