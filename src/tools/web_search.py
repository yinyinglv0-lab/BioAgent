"""Web search tool - PubMed and general web search capabilities."""

import logging
from . import register

logger = logging.getLogger(__name__)


@register(
    name="search_pubmed",
    description="Search PubMed for scientific literature. Returns paper titles, authors, journal, year, and PMID.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for PubMed (e.g., 'SEMA3A renal cell carcinoma')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 10)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
)
def search_pubmed(query: str, max_results: int = 10) -> dict:
    """Search PubMed via E-utilities API and return formatted results."""
    import json
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET

    try:
        # ESearch - get IDs
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        })
        with urllib.request.urlopen(f"{esearch_url}?{params}", timeout=10) as resp:
            search_data = json.loads(resp.read())

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return {"query": query, "results": [], "message": "No results found"}

        # EFetch - get details
        efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
        })
        with urllib.request.urlopen(f"{efetch_url}?{fetch_params}", timeout=15) as resp:
            fetch_data = resp.read()

        root = ET.fromstring(fetch_data)
        articles = []
        for article in root.findall(".//PubmedArticle"):
            try:
                title_el = article.find(".//ArticleTitle")
                title = title_el.text if title_el is not None else "N/A"

                pmid_el = article.find(".//PMID")
                pmid = pmid_el.text if pmid_el is not None else "N/A"

                journal_el = article.find(".//Journal/Title")
                journal = journal_el.text if journal_el is not None else "N/A"

                year_el = article.find(".//PubDate/Year")
                year = year_el.text if year_el is not None else "N/A"

                # Authors
                authors = []
                for author in article.findall(".//Author"):
                    last = author.findtext("LastName", "")
                    initials = author.findtext("Initials", "")
                    if last:
                        authors.append(f"{last} {initials}")
                author_str = ", ".join(authors[:5])
                if len(authors) > 5:
                    author_str += " et al."

                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "authors": author_str,
                    "journal": journal,
                    "year": year,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })
            except Exception:
                continue

        return {"query": query, "total_found": len(articles), "results": articles}

    except Exception as e:
        logger.warning(f"PubMed search failed: {e}")
        return {
            "query": query,
            "error": f"PubMed API unavailable: {e}",
            "fallback": "Use general knowledge or provide information from training data.",
        }
