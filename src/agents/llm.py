"""Thin OpenRouter chat client for the reasoning agents (Director, critics, research)."""

import json
import os
import re

import requests

URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-sonnet-5.5"


class LLM:
    def __init__(self, model: str = DEFAULT_MODEL):
        from dotenv import load_dotenv

        load_dotenv()
        self.model = model
        self.key = os.environ.get("OPENROUTER_API_KEY")
        if not self.key:
            raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env.")
        self.cost = 0.0
        self.calls = 0

    def ask(self, system: str, user: str, temperature: float = 0.8, max_tokens: int = 6000) -> str:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {self.key}"},
            json={"model": self.model, "temperature": temperature, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=300,
        )
        if not r.ok:
            raise RuntimeError(f"OpenRouter rejected the request ({r.status_code}): {r.text[:300]}")
        data = r.json()
        self.calls += 1
        self.cost += float((data.get("usage") or {}).get("cost") or 0)
        choice = data["choices"][0]
        text = choice["message"].get("content")
        if not text:
            raise RuntimeError(f"Empty reply from {self.model} (finish_reason={choice.get('finish_reason')})")
        return text

    def ask_json(self, system: str, user: str, **kw) -> dict:
        """Ask for a JSON object; retry once if the reply cannot be parsed."""
        for attempt in range(2):
            try:
                text = self.ask(system, user + "\n\nReply with a single JSON object and nothing else.", **kw)
            except RuntimeError:
                if attempt:
                    raise
                continue
            m = re.search(r"\{.*\}", text, re.DOTALL)
            try:
                return json.loads(m.group(0)) if m else json.loads(text)
            except json.JSONDecodeError:
                if attempt:
                    raise RuntimeError(f"Model did not return valid JSON: {text[:300]}")
