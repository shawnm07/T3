"""AI research layer: load `.claude/agents/*.md` and call them via Anthropic SDK.

The agents were designed for interactive CLI use with tools. In the autonomous
loop we invoke them statelessly — pre-computed data goes in the user message,
a structured JSON object comes back out. Tools are disabled this invocation.
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.config import Config

# Global semaphore to limit concurrent API requests (avoid 429 rate limits).
# Allow 2 concurrent requests; queue the rest.
_api_semaphore = asyncio.Semaphore(2)

log = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).resolve().parents[1] / ".claude" / "agents"

# Autonomous-mode prompt suffix appended to every agent system message.
AUTONOMOUS_SUFFIX = """
---
# AUTONOMOUS MODE (IMPORTANT)

You are being invoked programmatically by the trading bot's scheduled scanner.
Tools are NOT available this invocation. You will receive pre-computed data in
the user message — trust it, do not try to "go fetch more" in your reasoning.

Return ONLY a single valid JSON object matching the schema in your instructions
above. No markdown fences, no prose before or after, no comments. The scanner
will fail if it cannot parse your response as JSON.
""".strip()


@dataclass(frozen=True)
class AgentDef:
    name: str
    description: str
    body: str  # full system prompt body (minus frontmatter)


class AIUnavailable(Exception):
    """Raised when AI research is configured but can't run (no key, etc.)."""


@lru_cache(maxsize=16)
def load_agent(name: str) -> AgentDef:
    path = AGENTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent file not found: {path}")
    text = path.read_text(encoding="utf-8")
    # Parse YAML frontmatter between leading --- markers
    fm = {}
    body = text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.DOTALL)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
            body = m.group(2)
        except yaml.YAMLError as e:
            log.warning("Failed to parse frontmatter for %s: %s", name, e)
    return AgentDef(
        name=fm.get("name", name),
        description=fm.get("description", ""),
        body=body.strip(),
    )


def _extract_json(text: str) -> dict | None:
    """Best-effort extraction of a JSON object from model output."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first balanced {...} block
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class AIResearcher:
    """Thin async wrapper around Anthropic's Messages API for agent invocation."""

    def __init__(self, config: Config):
        self.cfg = config
        self.enabled = bool(config.get("ai", "enabled", default=False))
        self.model = config.get("ai", "model", default="claude-sonnet-4-6")
        self.haiku_model = config.get("ai", "haiku_model", default="claude-haiku-4-5-20251001")
        self.max_tokens = config.get("ai", "max_tokens_per_call", default=1500)
        self.temperature = config.get("ai", "temperature", default=0.3)
        self.timeout = config.get("ai", "timeout_seconds", default=45)
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self._client = None

    def available(self) -> bool:
        return self.enabled and bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            if not self.available():
                raise AIUnavailable("AI research not available (enabled=%s, key=%s)" % (
                    self.enabled, bool(self.api_key)))
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)
        return self._client

    async def call_agent(
        self,
        agent_name: str,
        context: dict[str, Any],
        extra_instructions: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Invoke one agent with a context dict; return parsed JSON response."""
        agent = load_agent(agent_name)

        # System prompt as cached content block — stable per agent, so cache hits
        # after the first call cut input token cost ~90% for the system prompt.
        system_blocks: list[dict] = [
            {
                "type": "text",
                "text": agent.body + "\n\n" + AUTONOMOUS_SUFFIX,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if extra_instructions:
            system_blocks.append({"type": "text", "text": extra_instructions.strip()})

        user_content = (
            "Here is the pre-computed research context. Analyze it per your instructions"
            " and return the JSON object.\n\n```json\n"
            + json.dumps(context, indent=2, default=str)
            + "\n```"
        )

        client = self._get_client()
        effective_model = model or self.model
        try:
            # Limit concurrent API requests to avoid 429 rate limits.
            # Up to 2 requests run in parallel; others queue.
            async with _api_semaphore:
                resp = await client.messages.create(
                    model=effective_model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_content}],
                )
        except Exception as e:
            log.warning("Agent %s call failed: %s", agent_name, e)
            return {"_error": str(e), "_agent": agent_name}

        # Extract text from content blocks
        text_parts = []
        for block in resp.content:
            t = getattr(block, "text", None)
            if t:
                text_parts.append(t)
        raw_text = "\n".join(text_parts)
        parsed = _extract_json(raw_text)
        if parsed is None:
            log.warning("Agent %s returned unparseable output: %r", agent_name, raw_text[:300])
            return {"_error": "json_parse_failed", "_raw": raw_text[:800], "_agent": agent_name}

        cache_read = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(resp.usage, "cache_creation_input_tokens", 0) or 0
        if cache_read or cache_write:
            log.debug(
                "Agent %s cache: read=%d write=%d (model=%s)",
                agent_name, cache_read, cache_write, effective_model,
            )

        parsed["_agent"] = agent_name
        parsed["_model"] = effective_model
        parsed["_input_tokens"] = getattr(resp.usage, "input_tokens", None)
        parsed["_output_tokens"] = getattr(resp.usage, "output_tokens", None)
        parsed["_cache_read_tokens"] = cache_read
        parsed["_cache_creation_tokens"] = cache_write
        return parsed
