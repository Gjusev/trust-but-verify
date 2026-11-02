"""Model clients: OpenAI-compatible client with usage tracking, plus a deterministic mock."""
import os
import time

BASE_URL = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4")


class Usage:
    """Accumulated model call counts and token totals."""

    def __init__(self):
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def add(self, prompt_tokens, completion_tokens):
        self.calls += 1
        self.input_tokens += prompt_tokens
        self.output_tokens += completion_tokens

    def snapshot(self):
        return (self.calls, self.input_tokens, self.output_tokens)


class Client:
    """Thin wrapper over the openai client. Thinking is disabled because this
    harness only needs direct answers and reasoning tokens inflate cost."""

    def __init__(self, model, usage=None, base_url=None, api_key=None):
        from openai import OpenAI

        self.model = model
        self.usage = usage if usage is not None else Usage()
        self.cli = OpenAI(
            base_url=base_url or BASE_URL,
            api_key=api_key or os.environ["ZAI_API_KEY"],
            timeout=120,
        )

    def chat(self, messages, max_tokens=2048, retries=3):
        last = None
        for attempt in range(retries):
            try:
                r = self.cli.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0,
                    max_tokens=max_tokens,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                if r.usage:
                    self.usage.add(r.usage.prompt_tokens, r.usage.completion_tokens)
                return r.choices[0].message.content or ""
            except Exception as exc:  # network or provider hiccups, retry with backoff
                last = exc
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"model call failed after {retries} attempts: {last}")


class MockClient:
    """Deterministic fake client for --mock mode and tests. Returns canned
    responses based on the prompt it sees. Numbers it reports are fake."""

    def __init__(self):
        self.usage = Usage()

    def chat(self, messages, max_tokens=2048, retries=3):
        system = messages[0]["content"].lower()
        last_user = [m for m in messages if m["role"] == "user"][-1]["content"].lower()
        self.usage.add(100, 20)
        if "independent reviewer" in system:
            return "VERDICT: REVISE\n\nCOMMENTS: handle edge cases"
        if "failed" in last_user or "requests changes" in last_user:
            return "```python\nMOCK_REVISED\n```"
        if "review your own" in last_user:
            return "```python\nMOCK_SELFCHECK\n```"
        return "```python\nMOCK_SOLVE\n```"
