from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any


class StrictAIUnavailableError(RuntimeError):
    pass


class AIProviderError(StrictAIUnavailableError):
    pass


@dataclass
class AIResponse:
    content: dict[str, Any]
    provider: str


class AIProvider:
    def __init__(self, strict_mode: bool):
        self.strict_mode = strict_mode
        self.model = os.getenv("MATE_CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.provider_mode = os.getenv("MATE_AI_PROVIDER", "copilot").strip().lower()

    def generate_json(self, task: str, context: dict[str, Any], schema_hint: dict[str, Any]) -> AIResponse:
        if self.provider_mode == "copilot":
            command = os.getenv("MATE_COPILOT_CLAUDE_COMMAND", "").strip()
            if not command:
                if self.strict_mode:
                    raise StrictAIUnavailableError(
                        "strictAIGeneration=true and provider mode is copilot, but MATE_COPILOT_CLAUDE_COMMAND is not configured."
                    )
                fallback = {
                    "note": "non-strict deterministic fallback",
                    "task": task,
                    "summary": "Generated without Copilot Claude command.",
                }
                return AIResponse(content=fallback, provider="deterministic-fallback")

            prompt = (
                "Generate JSON only for this task. "
                + "Task: "
                + task
                + "\nContext: "
                + json.dumps(context)[:15000]
                + "\nSchema hint: "
                + json.dumps(schema_hint)
            )
            try:
                proc = subprocess.run(
                    [*shlex.split(command), prompt],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if proc.returncode != 0:
                    raise RuntimeError((proc.stderr or "").strip() or "Copilot command failed")
                text = (proc.stdout or "").strip() or "{}"
                return AIResponse(content=json.loads(text), provider="copilot-claude")
            except Exception as ex:
                if self.strict_mode:
                    raise StrictAIUnavailableError(
                        f"strictAIGeneration=true and Copilot Claude command failed: {ex}"
                    ) from ex

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if self.strict_mode and not api_key:
            raise StrictAIUnavailableError(
                "strictAIGeneration=true but ANTHROPIC_API_KEY is not set; refusing fallback."
            )

        # Provider call path (best effort). If unavailable and non-strict, return deterministic structure.
        if api_key:
            try:
                import anthropic  # type: ignore

                client = anthropic.Anthropic(api_key=api_key)
                prompt = (
                    "You are generating JSON only. Task: "
                    + task
                    + "\nContext: "
                    + json.dumps(context)[:15000]
                    + "\nSchema hint: "
                    + json.dumps(schema_hint)
                    + "\nReturn valid JSON object only."
                )
                message = client.messages.create(
                    model=self.model,
                    max_tokens=2500,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = message.content[0].text if message.content else "{}"
                return AIResponse(content=json.loads(text), provider="claude")
            except Exception:
                if self.strict_mode:
                    raise StrictAIUnavailableError(
                        "strictAIGeneration=true and Claude call failed; refusing fallback."
                    )

        fallback = {
            "note": "non-strict deterministic fallback",
            "task": task,
            "summary": "Generated without Claude due to unavailable provider.",
        }
        return AIResponse(content=fallback, provider="deterministic-fallback")


def call_ai(prompt: dict[str, Any], strict: bool) -> dict[str, Any]:
    """Compatibility wrapper used by skill scripts.

    Returns a dict with:
    - text: string content (JSON string when possible)
    - providerUsed: bool indicating Claude was used
    - provider: provider identifier
    """
    provider = AIProvider(strict_mode=strict)
    task = str(prompt.get("task") or "Generate structured output")
    context = dict(prompt)
    schema_hint = {"type": "array-or-object"}

    try:
        response = provider.generate_json(task=task, context=context, schema_hint=schema_hint)
    except StrictAIUnavailableError as ex:
        raise AIProviderError(str(ex)) from ex
    except Exception as ex:
        raise AIProviderError(f"AI provider call failed: {ex}") from ex

    content = response.content
    text = json.dumps(content)
    return {
        "text": text,
        "providerUsed": response.provider == "claude",
        "provider": response.provider,
    }
