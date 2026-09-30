"""
Model adapters for extraction.

The provider is a configuration value, not a rewrite. Anything that speaks the
OpenAI chat-completions shape — OpenAI, DeepSeek, Together, Fireworks, vLLM,
Ollama, LM Studio, llama.cpp server — is reachable through one client, which
covers both hosted and local inference. The choice between them is therefore
deferred rather than guessed.

Three clients are provided:

    OpenAICompatibleClient   any OpenAI-shaped HTTP endpoint
    ReplayClient             deterministic replay from a recording
    ScriptedClient           canned responses for tests

**ReplayClient is the important one.** It lets the entire extraction pipeline —
prompt assembly, attempt storage, all three signals, calibration, and the record
writer — be executed and validated with no model access at all. Given that the
compute environment here cannot run anything, being able to validate the
pipeline offline is the difference between code that has been exercised and code
that has only been read.

Token entropy
-------------
Entropy is computed from the returned top-k log-probabilities. That is a
**lower bound** on the token's true entropy, because mass outside the top k is
invisible. The value of k is recorded with every completion so the bound's
tightness is auditable. Where a backend returns no log-probabilities, the field
is None and Signal B is unavailable for that value — it is never silently
substituted with zero, which would read as certainty.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np


# --------------------------------------------------------------------------

@dataclass
class Completion:
    text: str
    model: str
    revision: str
    token_count: int | None = None
    token_logprobs: list[float] | None = None
    top_logprobs: list[dict] | None = None
    latency_s: float | None = None
    raw: dict | None = None
    error: str | None = None

    @property
    def mean_token_entropy(self) -> float:
        """Mean per-token entropy over the generated span, or NaN.

        NaN rather than 0.0 when log-probabilities are unavailable: a zero would
        be read downstream as 'certain', which is the opposite of 'unknown'.
        """
        if not self.top_logprobs:
            return float("nan")
        entropies = []
        for dist in self.top_logprobs:
            if not dist:
                continue
            p = np.array([np.exp(v) for v in dist.values()], dtype=float)
            total = p.sum()
            if total <= 0:
                continue
            p = p / total
            p = p[p > 0]
            entropies.append(float(-(p * np.log(p)).sum()))
        if not entropies:
            return float("nan")
        return float(np.mean(entropies))


class ModelClient(Protocol):
    """Minimal interface the extraction runner needs."""

    name: str
    revision: str
    family: str

    def complete(self, system: str, user: str, *, temperature: float,
                 top_p: float, max_tokens: int, seed: int | None) -> Completion:
        ...


def prompt_key(system: str, user: str, model: str) -> str:
    """Stable key for record/replay. Includes the model so that a recording made
    with one model cannot be silently replayed against another."""
    h = hashlib.sha256()
    for part in (model, system, user):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:32]


# --------------------------------------------------------------------------
# OpenAI-compatible HTTP client
# --------------------------------------------------------------------------

class OpenAICompatibleClient:
    """POSTs to `<base_url>/chat/completions` using only the standard library.

    Deliberately dependency-free: adding an SDK would pin the project to one
    vendor's release cycle, which is exactly what the frozen-revision policy is
    trying to avoid.
    """

    def __init__(self, base_url: str, model: str, revision: str, family: str,
                 api_key: str | None = None, timeout_s: float = 120.0,
                 request_logprobs: bool = True, top_logprobs: int = 5):
        self.base_url = base_url.rstrip("/")
        self.name = model
        self.revision = revision
        self.family = family
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.request_logprobs = request_logprobs
        self.top_logprobs = top_logprobs

    def complete(self, system: str, user: str, *, temperature: float = 0.7,
                 top_p: float = 1.0, max_tokens: int = 512,
                 seed: int | None = None) -> Completion:
        payload: dict = {
            "model": self.name,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if seed is not None:
            payload["seed"] = seed
        if self.request_logprobs:
            payload["logprobs"] = True
            payload["top_logprobs"] = self.top_logprobs

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})},
            method="POST")

        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            # Transport failures are returned, not raised: one failed attempt out
            # of N must not abort a value, and the failure count is itself data
            # about instrument stability.
            return Completion(text="", model=self.name, revision=self.revision,
                              latency_s=time.time() - start,
                              error=f"{type(exc).__name__}: {exc}")

        return self._parse(body, time.time() - start)

    def _parse(self, body: dict, latency: float) -> Completion:
        try:
            choice = body["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            return Completion(text="", model=self.name, revision=self.revision,
                              latency_s=latency, raw=body,
                              error=f"unexpected response shape: {exc}")

        lp = choice.get("logprobs") or {}
        content_lp = lp.get("content") or []
        token_logprobs = [t.get("logprob") for t in content_lp if t.get("logprob") is not None]
        top = [t.get("top_logprobs") for t in content_lp
               if isinstance(t.get("top_logprobs"), dict)]

        return Completion(
            text=text,
            model=body.get("model", self.name),
            revision=self.revision,
            token_count=len(content_lp) if content_lp else None,
            token_logprobs=token_logprobs or None,
            top_logprobs=top or None,
            latency_s=latency,
            raw=body,
        )


# --------------------------------------------------------------------------
# Replay client — the offline validation path
# --------------------------------------------------------------------------

class ReplayClient:
    """Deterministic replay from a recording, for offline pipeline validation.

    Looks each request up by `prompt_key`. An unseen prompt **raises** rather
    than returning something plausible: a replay that silently invents a response
    would validate the pipeline against data it never saw, which is worse than
    not validating it at all.

    Repeated identical requests cycle through the recorded attempts in order, so
    N attempts at one prompt replay N distinct recorded answers — which is what
    makes Signal A non-degenerate offline.
    """

    def __init__(self, recording: str | Path | Sequence[dict], name: str,
                 revision: str, family: str):
        self.name = name
        self.revision = revision
        self.family = family
        self._by_key: dict[str, list[dict]] = {}
        self._cursor: dict[str, int] = {}

        items = recording
        if isinstance(recording, (str, Path)):
            items = []
            with Path(recording).open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))
        for item in items:
            key = item.get("prompt_key")
            if not key:
                raise ValueError("every recorded item needs a prompt_key")
            self._by_key.setdefault(key, []).append(item)

    def complete(self, system: str, user: str, *, temperature: float = 0.7,
                 top_p: float = 1.0, max_tokens: int = 512,
                 seed: int | None = None) -> Completion:
        key = prompt_key(system, user, self.name)
        if key not in self._by_key:
            raise KeyError(
                f"ReplayClient has no recording for model {self.name!r} and prompt "
                f"key {key}. A replay must never invent a response.")
        options = self._by_key[key]
        idx = self._cursor.get(key, 0)
        item = options[idx % len(options)]
        self._cursor[key] = idx + 1
        return Completion(
            text=item.get("text", ""), model=self.name, revision=self.revision,
            token_count=item.get("token_count"),
            token_logprobs=item.get("token_logprobs"),
            top_logprobs=item.get("top_logprobs"),
            latency_s=item.get("latency_s"),
            raw=item.get("raw"),
            error=item.get("error"),
        )


class ScriptedClient:
    """Canned responses keyed by a substring of the prompt. For unit tests."""

    def __init__(self, responses: dict[str, Sequence[str]], name: str = "scripted",
                 revision: str = "test", family: str = "scripted"):
        self.name = name
        self.revision = revision
        self.family = family
        self.responses = {k: list(v) for k, v in responses.items()}
        self._cursor: dict[str, int] = {}

    def complete(self, system: str, user: str, *, temperature: float = 0.7,
                 top_p: float = 1.0, max_tokens: int = 512,
                 seed: int | None = None) -> Completion:
        for needle, options in self.responses.items():
            if needle in user:
                idx = self._cursor.get(needle, 0)
                self._cursor[needle] = idx + 1
                return Completion(text=options[idx % len(options)], model=self.name,
                                  revision=self.revision, token_count=10,
                                  top_logprobs=[{"a": -0.7, "b": -1.2}] * 3)
        raise KeyError(f"ScriptedClient has no response for this prompt: {user[:80]!r}")


# --------------------------------------------------------------------------
# Recording
# --------------------------------------------------------------------------

def record_completion(system: str, user: str, completion: Completion) -> dict:
    """Serialise one attempt for the replay recording.

    `raw` is deliberately dropped: it holds the full provider response, which is
    large and provider-specific, and everything downstream needs is already in
    the named fields. The full raw response is stored separately by the runner
    when an audit trail is wanted.
    """
    return {
        "prompt_key": prompt_key(system, user, completion.model),
        "model": completion.model,
        "revision": completion.revision,
        "text": completion.text,
        "token_count": completion.token_count,
        "token_logprobs": completion.token_logprobs,
        "top_logprobs": completion.top_logprobs,
        "latency_s": completion.latency_s,
        "error": completion.error,
    }


def build_client(provider: dict) -> ModelClient:
    """Construct a client from a configuration block.

    Two kinds are recognised. `openai_compatible` covers hosted and local
    inference alike; `replay` covers offline validation. Anything else is an
    error rather than a silent fallback, because a mis-specified provider that
    quietly produced no data would be found only at analysis time.
    """
    kind = provider.get("kind")
    if kind == "openai_compatible":
        return OpenAICompatibleClient(
            base_url=provider["base_url"],
            model=provider["model"],
            revision=provider.get("revision", "unpinned"),
            family=provider["family"],
            api_key=provider.get("api_key"),
            timeout_s=float(provider.get("timeout_s", 120.0)),
            request_logprobs=bool(provider.get("request_logprobs", True)),
            top_logprobs=int(provider.get("top_logprobs", 5)),
        )
    if kind == "replay":
        return ReplayClient(provider["recording"], name=provider["model"],
                            revision=provider.get("revision", "replay"),
                            family=provider.get("family", "replay"))
    if kind == "scripted":
        return ScriptedClient(provider["responses"], name=provider.get("model", "scripted"))
    raise ValueError(f"unknown provider kind: {kind!r}")
