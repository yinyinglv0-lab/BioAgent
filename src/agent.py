"""BioAgent - Core Agent implementation using Claude API with tool use."""

import json
import logging
from pathlib import Path
from typing import Any

import anthropic
from anthropic.types import TextBlock, ToolUseBlock

from .config import config
from .tools import get_all_tools, execute_tool

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are BioAgent, an AI research assistant specialized in bioinformatics and genomics.

You have access to tools covering 7 public databases (all free APIs, no keys required):
- **query_uniprot**: Protein functional annotation, domains, disease associations
- **query_ensembl**: Gene annotation, genomic location, homologs
- **query_kegg**: Metabolic/signaling pathways, gene orthologs, diseases
- **query_tcga**: Cancer genomics mutation data via cBioPortal
- **query_geo**: Public gene expression datasets from NCBI GEO
- **query_clinvar**: Clinically significant genetic variants
- **query_dbsnp**: SNP information by gene or rsID
- **search_pubmed**: Scientific literature from PubMed
- **read_paper**: Extract text and findings from PDF papers
- **run_enrichment**: Basic GO/KEGG enrichment analysis on gene lists

Guidelines:
1. When asked about a gene, query UniProt (protein), Ensembl (genomic), KEGG (pathways)
2. When asked about mutations/variants, query ClinVar and dbSNP
3. When asked about cancer, query TCGA for mutation data
4. When asking for public datasets, query GEO
5. Always back claims with PubMed citations when possible
6. Explain results in plain language for biologists
7. Format gene symbols in uppercase

Workflow for research questions:
1. Query database for relevant data
2. If insufficient, search literature
3. Synthesize findings and provide actionable insights
4. Suggest follow-up analyses where appropriate
"""


class BioAgent:
    """Core Agent that orchestrates Claude API calls with tool execution."""

    def __init__(self):
        config.check()
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.tools = get_all_tools()
        self.conversation_history: list[dict[str, Any]] = []

    def chat(self, user_message: str, max_turns: int = 8) -> str:
        """Single-turn or multi-turn conversation with tool use."""
        self.conversation_history.append(
            {"role": "user", "content": user_message}
        )

        messages = self._build_messages()

        for _ in range(max_turns):
            response = self.client.messages.create(
                model=config.AGENT_MODEL,
                max_tokens=config.AGENT_MAX_TOKENS,
                temperature=config.AGENT_TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages,
            )

            # Process response
            text_parts: list[str] = []
            tool_calls: list[ToolUseBlock] = []

            for block in response.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append(block)

            # If no tool calls, return the final text response
            if not tool_calls:
                result = "\n".join(text_parts)
                self.conversation_history.append(
                    {"role": "assistant", "content": result}
                )
                return result

            # Handle tool calls
            messages.append({
                "role": "assistant",
                "content": response.content,
            })

            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input if isinstance(tool_call.input, dict) else {}
                logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                try:
                    result = execute_tool(tool_name, tool_input)
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    logger.info(f"Tool {tool_name} completed")
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})
                    logger.error(f"Tool {tool_name} failed: {e}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": result_str,
                })

            messages.append({"role": "user", "content": tool_results})

        return "Agent reached maximum conversation turns. Please refine your question."

    def _build_messages(self) -> list[dict[str, Any]]:
        """Build messages list with conversation window management."""
        max_messages = 20
        recent = self.conversation_history[-max_messages:]
        messages: list[dict[str, Any]] = []
        for msg in recent:
            if msg["role"] == "assistant" and isinstance(msg.get("content"), str):
                messages.append(msg)
            elif msg["role"] == "user":
                messages.append(msg)
        return messages

    def reset(self):
        """Clear conversation history."""
        self.conversation_history = []

    def run_pipeline(self, user_message: str) -> str:
        """Run a complete research pipeline and return structured results."""
        return self.chat(user_message, max_turns=10)


# Global agent instance
agent = BioAgent()
