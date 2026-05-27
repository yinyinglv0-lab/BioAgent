# BioAgent 🧬

**AI-Powered Bioinformatics Research Assistant**  
Built with Claude API · Python · MySQL · Docker

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

BioAgent is an intelligent research assistant that combines Claude's natural language understanding with bioinformatics-specific tools. It can query disease databases, analyze differential gene expression, generate survival statistics, extract information from scientific papers, and search biomedical literature — all through natural conversation.

---

## Architecture

```
                    User
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    CLI Mode     Web UI       Programmatic
    (rich)      (FastAPI)      (Python API)
                     │
                     ▼
              ┌──────────────┐
              │   BioAgent   │  ← Orchestrates Claude API + tool execution
              │    Core      │
              └──────┬───────┘
                     │
        ┌────────────┼────────────────────┐
        ▼            ▼            ▼       ▼
   ┌─────────┐ ┌──────────┐ ┌──────┐ ┌──────────┐
   │PDF      │ │Database  │ │Expr  │ │PubMed    │
   │Reader   │ │Queries   │ │&Surv │ │Search    │
   │(PyMuPDF)│ │(PyMySQL) │ │Tools │ │(E-utils) │
   └─────────┘ └──────────┘ └──────┘ └──────────┘
                     │
                     ▼
              ┌──────────────┐
              │    MySQL     │
              │ Disease DB   │
              └──────────────┘
```

## Features

### Agent Tools

| Tool | Description |
|------|-------------|
| `read_paper` | Extract text, abstract, and gene symbols from scientific PDFs |
| `query_disease` | Search diseases by name/ICD code; get associated genes and sample counts |
| `query_gene` | Search genes by symbol/Ensembl ID; get disease associations and expression |
| `differential_expression` | Query DEGs with customizable padj and log2FC thresholds |
| `survival_analysis` | Query survival data; get median survival, stage/treatment breakdown |
| `search_pubmed` | Search PubMed via NCBI E-utilities API; returns formatted references |
| `run_enrichment` | GO/KEGG enrichment analysis on gene lists |

### Interfaces

- **CLI** — Rich terminal interface with Markdown rendering
- **Web UI** — FastAPI + vanilla JavaScript, dark theme
- **Python API** — Import `BioAgent` and use it programmatically

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/BioAgent.git
cd BioAgent
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY
```

### 3. (Optional) Setup Disease Database

```bash
# Import the schema into MySQL
mysql -u root -p < ../sql/schema.sql
# Or use Docker Compose
docker-compose up -d mysql
mysql -h 127.0.0.1 -P 3307 -u root -proot123 disease_db < ../sql/schema.sql
```

### 4. Run

```bash
# CLI mode
python -m src.cli

# Single query
python -m src.cli -q "Analyze TP53 expression in lung adenocarcinoma"

# Web UI
python -m src.cli --web --port 8000
# then open http://localhost:8000

# Batch pipeline
python -m src.cli -p examples/questions.txt -o report.md

# Run examples
python examples/workflow.py
```

### 5. Docker

```bash
docker-compose up -d
```

## Usage Examples

### CLI Conversation

```
You > What genes are differentially expressed in lung adenocarcinoma?

BioAgent:
## Differential Expression: Lung Adenocarcinoma
- Total DEGs: 11 (↓7 up, ↓4 down)
- Thresholds: padj < 0.05, |log2FC| > 1.0

**Top Up-regulated:**
- MYC (log2FC: 2.88, padj: 0.0008)
- EGFR (log2FC: 3.12, padj: 0.001)
- VEGFA (log2FC: 2.48, padj: 0.0016)

**Top Down-regulated:**
- PTEN (log2FC: -1.85, padj: 0.006)
- CDKN2A (log2FC: -1.55, padj: 0.017)
```

### Programmatic API

```python
from src.agent import BioAgent
from src.tools.expression import differential_expression

# Direct tool call
degs = differential_expression("Lung Adenocarcinoma", padj_threshold=0.01)
print(f"Found {degs['total_degs']} DEGs")

# LLM-powered conversation
agent = BioAgent()
response = agent.chat(
    "Compare the roles of TP53 and EGFR mutations in ccRCC prognosis"
)
print(response)

agent.reset()
```

## Project Structure

```
BioAgent/
├── src/
│   ├── agent.py              # Core agent with Claude API + tool orchestration
│   ├── config.py             # Configuration management
│   ├── cli.py                # CLI interface (interactive, single-query, pipeline)
│   ├── web.py                # FastAPI web server and UI
│   └── tools/
│       ├── __init__.py       # Tool registry with decorator-based registration
│       ├── pdf_reader.py     # PDF paper extraction (PyMuPDF)
│       ├── db_query.py       # Disease/gene database queries (PyMySQL)
│       ├── expression.py     # Differential expression + enrichment analysis
│       ├── survival.py       # Survival data and statistics
│       └── web_search.py     # PubMed literature search (NCBI E-utilities)
├── examples/
│   ├── workflow.py           # Direct tool demo + agent conversation demo
│   └── pdf_analysis.py       # PDF paper analysis example
├── tests/
│   └── test_tools.py         # Unit tests for all tools
├── static/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Engine | Claude API (Anthropic), claude-sonnet-4-6 |
| Language | Python 3.11+ |
| Web Framework | FastAPI + Uvicorn |
| CLI | Rich (Markdown rendering, panels, spinners) |
| Database | MySQL 8.0 + PyMySQL |
| PDF Processing | PyMuPDF (fitz) |
| Data Analysis | Pandas, NumPy, Matplotlib, Seaborn |
| Containerization | Docker + Docker Compose |
| API Integration | NCBI E-utilities (PubMed) |

## Design Decisions

### Why Claude API over LangChain?
LangChain adds abstraction overhead for simple tool-calling patterns. BioAgent uses Anthropic's native `tools` parameter directly, giving full control over the tool schema, conversation flow, and error handling. This results in ~200 lines for the core agent vs ~500+ with LangChain.

### Tool Registry Pattern
Each tool is a standalone Python function decorated with `@register(...)`. This means:
- Tools can be tested independently without the LLM
- New tools are added by writing one function + one decorator
- The agent automatically discovers all registered tools

```python
@register(
    name="my_tool",
    description="What this tool does",
    input_schema={"type": "object", "properties": {...}}
)
def my_tool(param: str) -> dict:
    return {"result": param}
```

### Graceful Degradation
All tools handle missing dependencies gracefully. If MySQL isn't running, database tools return structured error messages instead of crashing. The Agent can then suggest alternatives or answer from training knowledge.

## Skills Demonstrated

- LLM Agent architecture with tool use
- Anthropic Claude API integration
- Python package design and project structure
- MySQL database integration
- Docker containerization
- FastAPI web application development
- CLI design with rich terminal UI
- Scientific data processing pipelines
- API integration (NCBI E-utilities)
- PDF document parsing and analysis

## License

MIT

---

Built with Claude Code — an AI-powered development tool that assisted throughout the entire development lifecycle, from architecture design to implementation and testing.
