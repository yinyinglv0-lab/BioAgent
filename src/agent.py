"""BioAgent - Core Agent supporting Claude API and OpenAI-compatible APIs (DeepSeek, etc.)."""

import json
import logging
from typing import Any

from .config import config
from .tools import get_tools_anthropic, get_tools_openai, execute_tool

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are BioAgent, an AI research assistant specialized in bioinformatics and genomics.

You have access to tools covering 7 public databases (all free APIs, no keys required):
- query_uniprot: Protein functional annotation, domains, disease associations
- query_ensembl: Gene annotation, genomic location, homologs
- query_kegg: Metabolic/signaling pathways, gene orthologs, diseases
- query_tcga: Cancer genomics mutation data via cBioPortal
- query_geo: Public gene expression datasets from NCBI GEO
- query_clinvar: Clinically significant genetic variants
- query_dbsnp: SNP information by gene or rsID
- search_pubmed: Scientific literature from PubMed
- read_paper: Extract text and findings from PDF papers
- run_enrichment: GO/KEGG enrichment analysis on gene lists

Guidelines:
1. When asked about a gene, query UniProt (protein), Ensembl (genomic), KEGG (pathways)
2. When asked about mutations/variants, query ClinVar and dbSNP
3. When asked about cancer, query TCGA for mutation data
4. When asking for public datasets, query GEO
5. Always back claims with PubMed citations when possible
6. Explain results in plain language for biologists
7. Format gene symbols in uppercase
"""


class BioAgent:
    """Agent that works with Claude API or any OpenAI-compatible API."""

    def __init__(self):
        config.check()
        self.provider = config.AGENT_PROVIDER  # "anthropic" or "openai"
        self.model = config.AGENT_MODEL
        self.conversation_history: list[dict[str, Any]] = []

        if self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self._tools = get_tools_anthropic()
        else:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )
            self._tools = get_tools_openai()

    def chat(self, user_message: str, max_turns: int = 8) -> str:
        """Multi-turn conversation with automatic tool execution."""
        self.conversation_history.append({"role": "user", "content": user_message})

        if self.provider == "anthropic":
            return self._chat_anthropic(max_turns)
        else:
            return self._chat_openai(max_turns)

    # ================================================================
    # Anthropic (Claude) implementation
    # ================================================================

    def _chat_anthropic(self, max_turns: int) -> str:
        from anthropic.types import TextBlock, ToolUseBlock

        messages = self._build_messages_anthropic()

        for _ in range(max_turns):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=config.AGENT_MAX_TOKENS,
                temperature=config.AGENT_TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=self._tools,
                messages=messages,
            )

            text_parts, tool_calls = [], []
            for block in response.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append(block)

            if not tool_calls:
                result = "\n".join(text_parts)
                self.conversation_history.append({"role": "assistant", "content": result})
                return result

            messages.append({"role": "assistant", "content": response.content})
            tool_results = self._execute_tools_anthropic(tool_calls)
            messages.append({"role": "user", "content": tool_results})

        return "Agent reached maximum turns. Please refine your question."

    def _execute_tools_anthropic(self, tool_calls) -> list[dict]:
        results = []
        for tc in tool_calls:
            name = tc.name
            inputs = tc.input if isinstance(tc.input, dict) else {}
            logger.info(f"Tool: {name}({inputs})")
            try:
                result = execute_tool(name, inputs)
            except Exception as e:
                result = {"error": str(e)}
            results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })
        return results

    def _build_messages_anthropic(self) -> list:
        recent = self.conversation_history[-20:]
        msgs = []
        for m in recent:
            if m["role"] == "user":
                msgs.append(m)
            elif m["role"] == "assistant" and isinstance(m.get("content"), str):
                msgs.append(m)
        return msgs

    # ================================================================
    # OpenAI-compatible implementation (DeepSeek, GLM, Qwen, GPT, etc.)
    # ================================================================

    def _chat_openai(self, max_turns: int) -> str:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(self.conversation_history[-20:])

        for _ in range(max_turns):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=msgs,
                tools=self._tools,
                temperature=config.AGENT_TEMPERATURE,
                max_tokens=config.AGENT_MAX_TOKENS,
            )

            choice = response.choices[0]
            msg = choice.message

            # No tool calls -> return text
            if not msg.tool_calls:
                text = msg.content or ""
                self.conversation_history.append({"role": "assistant", "content": text})
                return text

            # Execute tools
            msgs.append(msg.model_dump())
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    inputs = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    inputs = {}
                logger.info(f"Tool: {name}({inputs})")
                try:
                    result = execute_tool(name, inputs)
                except Exception as e:
                    result = {"error": str(e)}

                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

            self.conversation_history.append({"role": "assistant", "content": "[used tools]"})

        return "Agent reached maximum turns."

    def reset(self):
        self.conversation_history = []

    def run_pipeline(self, user_message: str) -> str:
        return self.chat(user_message, max_turns=10)


agent = BioAgent()
