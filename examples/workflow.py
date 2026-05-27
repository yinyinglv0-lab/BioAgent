#!/usr/bin/env python3
"""
BioAgent Research Workflow Demo.

Demonstrates all 7 external database tools (100% free APIs, no keys needed).

Usage:
    python examples/workflow.py
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.external_dbs import *
from src.tools.web_search import search_pubmed


def demo():
    print("=" * 60)
    print("BioAgent - 7 Public Database Demos (All Free)")
    print("=" * 60)

    # 1. UniProt
    print("\n[1/7] UniProt - TP53 Protein")
    r = query_uniprot('TP53')
    if r['results']:
        p = r['results'][0]
        print(f"  Name: {p['protein_name']}")
        print(f"  ID: {p['uniprot_id']} | Length: {p['length']} aa")
        if p.get('function'):
            print(f"  Function: {p['function'][:150]}...")

    # 2. Ensembl
    print("\n[2/7] Ensembl - EGFR Gene")
    r = query_ensembl('EGFR')
    print(f"  ID: {r.get('ensembl_id')} | chr{r.get('chromosome')} | {r.get('biotype')}")

    # 3. KEGG
    print("\n[3/7] KEGG - TP53 Pathways")
    r = query_kegg('TP53', 'gene')
    for g in r.get('human_matches', [])[:3]:
        print(f"  {g['kegg_id']}: {g['description'][:80]}")

    # 4. TCGA
    print("\n[4/7] TCGA - VHL in Kidney Cancer")
    r = query_tcga(gene_symbol='VHL', cancer_type='kidney')
    print(f"  Study: {r.get('study_id', '?')}")
    print(f"  Mutations: {r.get('mutation_count', '?')}")
    if r.get('mutation_types'):
        print(f"  Types: {r['mutation_types'][:5]}")

    # 5. GEO
    print("\n[5/7] GEO - ccRCC Datasets")
    r = query_geo('renal cell carcinoma RNA-seq', 3)
    for d in r.get('results', [])[:2]:
        print(f"  {d['accession']}: {d['title'][:100]}")

    # 6. PubMed
    print("\n[6/7] PubMed - SEMA3A ccRCC")
    r = search_pubmed('SEMA3A renal cell carcinoma', 2)
    for p in r.get('results', [])[:2]:
        print(f"  [{p['year']}] {p['title'][:100]}")

    # 7. ClinVar + dbSNP
    print("\n[7/7] ClinVar/dbSNP - BRCA1")
    r = query_clinvar('BRCA1')
    print(f"  ClinVar pathogenic variants: {r.get('total_variants', '?')}")
    r = query_dbsnp('TP53')
    print(f"  dbSNP TP53 SNPs: {r.get('total_snps', '?')}")

    print("\n" + "=" * 60)
    print("7 databases, 0 cost, 100% real data.")
    print("Add ANTHROPIC_API_KEY to .env for chat mode.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
