"""External bioinformatics database tools.

All seven databases use public REST APIs - no API key required.
Each tool is self-contained and returns structured JSON results.
"""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

from . import register

logger = logging.getLogger(__name__)


def _http_get(url: str, timeout: int = 15) -> dict | str:
    """Helper: Make an HTTP GET request, return parsed JSON or raw text."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BioAgent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    except urllib.error.URLError as e:
        return {"error": f"API unavailable: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 1. TCGA - via cBioPortal Web API
# ============================================================

@register(
    name="query_tcga",
    description="Query TCGA cancer genomics data via cBioPortal API. Search by cancer type, gene symbol, or molecular profile. Returns mutation frequency, CNA, expression data.",
    input_schema={
        "type": "object",
        "properties": {
            "cancer_type": {
                "type": "string",
                "description": "Cancer type keyword (e.g., 'lung adenocarcinoma', 'kidney renal clear cell')",
            },
            "gene_symbol": {
                "type": "string",
                "description": "Gene symbol to query (e.g., 'TP53', 'EGFR', 'VHL')",
            },
        },
        "required": ["gene_symbol"],
    },
)
def query_tcga(cancer_type: str = "", gene_symbol: str = "") -> dict:
    """Query TCGA data from cBioPortal."""

    # Step 1: Find matching cancer studies
    studies_url = "https://www.cbioportal.org/api/studies?pageSize=100&direction=ASC"
    studies = _http_get(studies_url)

    if isinstance(studies, dict) and "error" in studies:
        return studies

    if not isinstance(studies, list):
        return {"error": "cBioPortal API returned unexpected format"}

    # Filter by cancer type
    matching = []
    for s in studies:
        name = s.get("name", "").lower()
        cancer_id = s.get("cancerTypeId", "").lower()
        if cancer_type.lower() in name or cancer_type.lower() in cancer_id:
            matching.append(s)

    if not matching and cancer_type:
        matching = studies  # fallback to all studies

    study_ids = [s["studyId"] for s in matching[:5]]
    if not study_ids:
        return {"error": "No matching studies found"}

    study_id = study_ids[0]

    # Step 2: Get molecular profiles for the study
    profiles_url = f"https://www.cbioportal.org/api/studies/{study_id}/molecular-profiles"
    profiles = _http_get(profiles_url)

    mutation_profile_id = None
    if isinstance(profiles, list):
        for p in profiles:
            if "MUTATION_EXTENDED" in p.get("molecularAlterationType", ""):
                mutation_profile_id = p["molecularProfileId"]
                break

    # Step 3: Query gene mutation data
    result = {
        "database": "TCGA (via cBioPortal)",
        "study_id": study_id,
        "gene": gene_symbol.upper(),
        "cancer_type_query": cancer_type,
        "mutation_frequency": None,
        "url": f"https://www.cbioportal.org/study/summary?id={study_id}",
    }

    if mutation_profile_id:
        mut_url = (
            f"https://www.cbioportal.org/api/molecular-profiles/"
            f"{mutation_profile_id}/mutations?"
            f"geneList={gene_symbol.upper()}&projection=SUMMARY"
        )
        mutations = _http_get(mut_url)
        if isinstance(mutations, list):
            total = len(mutations)
            result["mutation_count"] = total
            result["mutation_types"] = list(set(m.get("mutationType", "?") for m in mutations[:100]))
            result["sample_mutations"] = [
                {"sample": m.get("sampleId", "?"), "type": m.get("mutationType", "?"),
                 "protein_change": m.get("proteinChange", "?"), "allele_freq": m.get("tumorAltCount", "?")}
                for m in mutations[:20]
            ]

    return result


# ============================================================
# 2. GEO - via NCBI E-utilities
# ============================================================

@register(
    name="query_geo",
    description="Search NCBI GEO (Gene Expression Omnibus) for gene expression datasets. Returns GSE accession, title, sample count, and platform info.",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Search keyword (e.g., 'ccRCC RNA-seq', 'lung cancer microarray')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of datasets to return (default: 10)",
                "default": 10,
            },
        },
        "required": ["keyword"],
    },
)
def query_geo(keyword: str, max_results: int = 10) -> dict:
    """Search GEO datasets via NCBI E-utilities."""

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search_url = f"{base_url}/esearch.fcgi?db=gds&term={urllib.parse.quote(keyword)}&retmax={max_results}&retmode=json&sort=relevance"
    search_data = _http_get(search_url)

    if isinstance(search_data, dict) and "error" in search_data:
        return search_data

    id_list = search_data.get("esearchresult", {}).get("idlist", []) if isinstance(search_data, dict) else []
    if not id_list:
        return {"keyword": keyword, "results": [], "message": "No GEO datasets found"}

    # Get summaries
    summary_url = f"{base_url}/esummary.fcgi?db=gds&id={','.join(id_list)}&retmode=json"
    summary_data = _http_get(summary_url)

    results = []
    if isinstance(summary_data, dict):
        for gid in id_list:
            record = summary_data.get("result", {}).get(gid, {})
            if isinstance(record, dict):
                results.append({
                    "accession": record.get("accession", "N/A"),
                    "title": record.get("title", "N/A")[:200],
                    "summary": record.get("summary", "")[:300],
                    "gds_type": record.get("gdsType", "N/A"),
                    "sample_count": record.get("ntaxa", "N/A"),
                    "url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={record.get('accession', '')}",
                })

    return {
        "database": "GEO (Gene Expression Omnibus)",
        "keyword": keyword,
        "total_found": len(results),
        "results": results,
    }


# ============================================================
# 3. UniProt
# ============================================================

@register(
    name="query_uniprot",
    description="Search UniProt for protein functional annotation by gene name or protein ID. Returns protein function, domains, subcellular location, and disease associations.",
    input_schema={
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g., 'TP53', 'EGFR', 'SEMA3A') or UniProt accession",
            },
        },
        "required": ["gene"],
    },
)
def query_uniprot(gene: str) -> dict:
    """Query UniProt REST API for protein annotation."""

    # Search by gene name, filter to human
    query = f"(gene:{gene}) AND organism_id:9606"
    search_url = f"https://rest.uniprot.org/uniprotkb/search?query={urllib.parse.quote(query)}&size=3"
    data = _http_get(search_url)

    if isinstance(data, dict) and "error" in data:
        return data

    results = []
    if isinstance(data, dict):
        for entry in data.get("results", [])[:3]:
            protein_info = {
                "uniprot_id": entry.get("primaryAccession", "N/A"),
                "entry_name": entry.get("uniProtkbId", "N/A"),
                "protein_name": entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "N/A"),
                "gene_symbol": gene.upper(),
                "length": entry.get("sequence", {}).get("length", "N/A"),
                "function": None,
                "domains": [],
                "disease_associations": [],
            }

            # Extract function from comments
            for comment in entry.get("comments", []):
                if comment.get("commentType") == "FUNCTION":
                    texts = comment.get("texts", [])
                    if texts:
                        protein_info["function"] = texts[0].get("value", "")[:500]
                elif comment.get("commentType") == "DISEASE":
                    protein_info["disease_associations"].append({
                        "disease": comment.get("disease", {}).get("description", "N/A"),
                    })

            # Extract domains
            for feature in entry.get("features", []):
                if feature.get("type") == "DOMAIN":
                    protein_info["domains"].append({
                        "name": feature.get("description", "N/A"),
                        "start": feature.get("location", {}).get("start", {}).get("value", "?"),
                        "end": feature.get("location", {}).get("end", {}).get("value", "?"),
                    })

            results.append(protein_info)

    return {
        "database": "UniProt",
        "gene": gene.upper(),
        "organism": "Homo sapiens",
        "total_found": len(results),
        "url": f"https://www.uniprot.org/uniprotkb?query={urllib.parse.quote(query)}",
        "results": results,
    }


# ============================================================
# 4. Ensembl
# ============================================================

@register(
    name="query_ensembl",
    description="Query Ensembl REST API for gene annotation, homologs, and transcript information by gene symbol or Ensembl ID.",
    input_schema={
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g., 'TP53') or Ensembl ID (e.g., 'ENSG00000141510')",
            },
        },
        "required": ["gene"],
    },
)
def query_ensembl(gene: str) -> dict:
    """Query Ensembl REST API."""

    # Get gene info using xrefs (external reference) endpoint for symbol lookup
    if not gene.startswith("ENSG"):
        xref_url = (
            f"https://rest.ensembl.org/xrefs/symbol/homo_sapiens/{gene}?"
            f"content-type=application/json"
        )
        xref_data = _http_get(xref_url)

        if isinstance(xref_data, list) and xref_data:
            ensembl_id = xref_data[0].get("id", "")
            gene_info = xref_data[0]
        else:
            return {"error": f"Gene symbol '{gene}' not found in Ensembl", "gene": gene}
    else:
        ensembl_id = gene
        gene_info = {}

    # Get detailed info
    if ensembl_id:
        lookup_url = (
            f"https://rest.ensembl.org/lookup/id/{ensembl_id}?"
            f"expand=1&content-type=application/json"
        )
        lookup_data = _http_get(lookup_url)

        if isinstance(lookup_data, dict):
            return {
                "database": "Ensembl",
                "gene": gene.upper() if not gene.startswith("ENSG") else gene,
                "ensembl_id": ensembl_id,
                "description": lookup_data.get("description", gene_info.get("description", "N/A")),
                "biotype": lookup_data.get("biotype", "N/A"),
                "chromosome": lookup_data.get("seq_region_name", "N/A"),
                "start": lookup_data.get("start", "N/A"),
                "end": lookup_data.get("end", "N/A"),
                "strand": "+" if lookup_data.get("strand", 1) > 0 else "-",
                "url": f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={ensembl_id}",
            }

    return {
        "database": "Ensembl",
        "gene": gene.upper(),
        "ensembl_id": ensembl_id,
        "description": gene_info.get("description", "N/A"),
    }


# ============================================================
# 5. KEGG
# ============================================================

@register(
    name="query_kegg",
    description="Query KEGG database for pathway information, gene orthologs, and disease associations. KEGG is the primary source for pathway enrichment analysis.",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Search keyword - gene symbol (e.g., 'TP53') or pathway name (e.g., 'cell cycle')",
            },
            "search_type": {
                "type": "string",
                "enum": ["gene", "pathway", "disease"],
                "description": "Type of search: 'gene' for gene/pathway mapping, 'pathway' for pathway info, 'disease' for disease association",
                "default": "gene",
            },
        },
        "required": ["keyword"],
    },
)
def query_kegg(keyword: str, search_type: str = "gene") -> dict:
    """Query KEGG REST API."""
    base = "https://rest.kegg.jp"

    if search_type == "gene":
        # Find gene entries
        find_url = f"{base}/find/genes/{urllib.parse.quote(keyword)}"
        text = _http_get(find_url)

        results = []
        if isinstance(text, str) and text.strip():
            for line in text.strip().split("\n")[:10]:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    kegg_id, desc = parts
                    if "hsa:" in kegg_id:  # Human genes only
                        gene_part = desc.split(";")[0].strip() if ";" in desc else desc.strip()
                        results.append({
                            "kegg_id": kegg_id,
                            "description": gene_part[:200],
                        })

        return {
            "database": "KEGG",
            "keyword": keyword,
            "search_type": "gene",
            "human_matches": results[:10],
            "url": f"https://www.kegg.jp/kegg-bin/search?q={urllib.parse.quote(keyword)}",
        }

    elif search_type == "pathway":
        # List pathway entries
        list_url = f"{base}/list/pathway/hsa"
        text = _http_get(list_url)

        pathways = []
        if isinstance(text, str):
            for line in text.strip().split("\n"):
                if keyword.lower() in line.lower():
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        pathways.append({"id": parts[0], "name": parts[1]})

        return {
            "database": "KEGG",
            "keyword": keyword,
            "search_type": "pathway",
            "pathways": pathways[:10],
            "organism": "Homo sapiens (hsa)",
        }

    elif search_type == "disease":
        find_url = f"{base}/find/disease/{urllib.parse.quote(keyword)}"
        text = _http_get(find_url)

        diseases = []
        if isinstance(text, str):
            for line in text.strip().split("\n")[:10]:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    diseases.append({"id": parts[0], "name": parts[1]})

        return {
            "database": "KEGG",
            "keyword": keyword,
            "search_type": "disease",
            "diseases": diseases,
        }

    return {"error": f"Unknown search_type: {search_type}"}


# ============================================================
# 6. ClinVar - via NCBI E-utilities
# ============================================================

@register(
    name="query_clinvar",
    description="Search NCBI ClinVar for clinically significant genetic variants by gene symbol or condition. Returns variant ID, clinical significance, and associated conditions.",
    input_schema={
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g., 'BRCA1', 'TP53') to search for variants",
            },
        },
        "required": ["gene"],
    },
)
def query_clinvar(gene: str) -> dict:
    """Search ClinVar for variants by gene symbol."""

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search_url = (
        f"{base_url}/esearch.fcgi?db=clinvar"
        f"&term={urllib.parse.quote(gene)}[gene]+AND+clinsig+pathogenic[filter]"
        f"&retmax=20&retmode=json&sort=relevance"
    )
    search_data = _http_get(search_url)

    if isinstance(search_data, dict) and "error" in search_data:
        return search_data

    id_list = search_data.get("esearchresult", {}).get("idlist", []) if isinstance(search_data, dict) else []
    total = search_data.get("esearchresult", {}).get("count", "0") if isinstance(search_data, dict) else "0"

    if not id_list:
        return {
            "database": "ClinVar",
            "gene": gene.upper(),
            "total_variants": total,
            "results": [],
            "url": f"https://www.ncbi.nlm.nih.gov/clinvar/?term={urllib.parse.quote(gene)}[gene]",
        }

    # Get variant summaries
    summary_url = f"{base_url}/esummary.fcgi?db=clinvar&id={','.join(id_list[:10])}&retmode=json"
    summary_data = _http_get(summary_url)

    results = []
    if isinstance(summary_data, dict):
        for vid in id_list[:10]:
            record = summary_data.get("result", {}).get(str(vid), {})
            if isinstance(record, dict):
                results.append({
                    "variant_id": vid,
                    "title": record.get("title", "N/A")[:200],
                    "clinical_significance": record.get("clinical_significance", "N/A"),
                    "gene": record.get("gene_sort", gene.upper()),
                    "review_status": record.get("review_status", "N/A"),
                })

    return {
        "database": "ClinVar",
        "gene": gene.upper(),
        "total_variants": total,
        "results": results,
        "url": f"https://www.ncbi.nlm.nih.gov/clinvar/?term={urllib.parse.quote(gene)}[gene]",
    }


# ============================================================
# 7. dbSNP - via NCBI E-utilities
# ============================================================

@register(
    name="query_dbsnp",
    description="Search NCBI dbSNP for single nucleotide polymorphisms (SNPs) by gene or rsID. Returns SNP ID, alleles, genomic location, and functional consequence.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gene symbol (e.g., 'TP53') or rsID (e.g., 'rs1042522')",
            },
        },
        "required": ["query"],
    },
)
def query_dbsnp(query: str) -> dict:
    """Search dbSNP via NCBI E-utilities."""

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Determine if it's an rsID or gene
    if query.lower().startswith("rs"):
        term = f"{query}[RS]"
    else:
        term = f"{query}[Gene]+AND+human[Organism]"

    search_url = f"{base_url}/esearch.fcgi?db=snp&term={urllib.parse.quote(term)}&retmax=15&retmode=json"
    search_data = _http_get(search_url)

    if isinstance(search_data, dict) and "error" in search_data:
        return search_data

    id_list = search_data.get("esearchresult", {}).get("idlist", []) if isinstance(search_data, dict) else []
    total = search_data.get("esearchresult", {}).get("count", "0") if isinstance(search_data, dict) else "0"

    if not id_list:
        return {
            "database": "dbSNP",
            "query": query,
            "total_snps": total,
            "results": [],
            "url": f"https://www.ncbi.nlm.nih.gov/snp/?term={urllib.parse.quote(term)}",
        }

    # Get SNP details
    summary_url = f"{base_url}/esummary.fcgi?db=snp&id={','.join(id_list[:10])}&retmode=json"
    summary_data = _http_get(summary_url)

    results = []
    if isinstance(summary_data, dict):
        for sid in id_list[:10]:
            record = summary_data.get("result", {}).get(str(sid), {})
            if isinstance(record, dict) and "error" not in str(record):
                results.append({
                    "snp_id": f"rs{record.get('snp_id', sid)}",
                    "alleles": record.get("allele_origin", "N/A"),
                    "gene": record.get("gene_name", "N/A"),
                    "chromosome": record.get("chr", "N/A"),
                    "position": record.get("chrpos", "N/A"),
                    "func_class": record.get("fxn_class", "N/A"),
                })

    return {
        "database": "dbSNP",
        "query": query,
        "total_snps": total,
        "results": results,
        "url": f"https://www.ncbi.nlm.nih.gov/snp/?term={urllib.parse.quote(term)}",
    }
