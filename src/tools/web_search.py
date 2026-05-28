"""Web search tool - PubMed and general web search capabilities."""

import logging
from . import register

logger = logging.getLogger(__name__)


PUBMED_FIELD_QUALIFIERS = {
    "all": "",
    "title": "[Title]",
    "title_abstract": "[Title/Abstract]",
    "author": "[Author]",
    "journal": "[Journal]",
    "mesh": "[MeSH Terms]",
    "pmid": "[PMID]",
}


@register(
    name="search_pubmed",
    description=(
        "Search PubMed for scientific literature. "
        "Returns total match count, paper titles, authors, journal, year, and PMID. "
        "Use search_field='title' to search titles only, 'title_abstract' for title+abstract, "
        "'author' for author name, 'mesh' for MeSH terms."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'BRCA1 breast cancer', 'Smith J[Author] AND TP53')",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of paper details to return (default: 10). Does NOT affect total count.",
                "default": 10,
            },
            "search_field": {
                "type": "string",
                "enum": ["all", "title", "title_abstract", "author", "journal", "mesh"],
                "description": "PubMed field to search in. 'title' for titles only, 'title_abstract' for title+abstract, 'all' for everywhere.",
                "default": "all",
            },
        },
        "required": ["query"],
    },
)
def search_pubmed(query: str, max_results: int = 10, search_field: str = "all") -> dict:
    """Search PubMed via E-utilities API and return formatted results.

    Uses esearch.count for the real total number of PubMed matches,
    not just the count of returned article details.
    """
    import json
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET

    # Append field qualifier if user chose a specific field
    qualifier = PUBMED_FIELD_QUALIFIERS.get(search_field, "")
    if qualifier and qualifier not in query:
        pubmed_query = f"{query}{qualifier}"
    else:
        pubmed_query = query

    try:
        # ESearch - get IDs
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": pubmed_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        })
        with urllib.request.urlopen(f"{esearch_url}?{params}", timeout=10) as resp:
            search_data = json.loads(resp.read())

        esearch_result = search_data.get("esearchresult", {})
        id_list = esearch_result.get("idlist", [])
        # Real total from PubMed — this is the number the user cares about
        total_count = int(esearch_result.get("count", 0))

        if not id_list:
            return {
                "query": pubmed_query,
                "search_field": search_field,
                "total_count": total_count,
                "results": [],
                "message": "No results found",
            }

        # EFetch - get details for the returned IDs
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

        return {
            "query": pubmed_query,
            "search_field": search_field,
            "total_count": total_count,
            "returned": len(articles),
            "results": articles,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(pubmed_query)}",
        }

    except Exception as e:
        logger.warning(f"PubMed search failed: {e}")
        return {
            "query": pubmed_query,
            "error": f"PubMed API unavailable: {e}",
            "fallback": "Use general knowledge or provide information from training data.",
        }
