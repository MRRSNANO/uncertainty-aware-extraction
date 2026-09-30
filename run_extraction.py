"""
Stage 2 — extraction runner.

Drives the frozen paraphrase set against the model ensemble, computes the three
signals, and writes schema-conformant records.

This module contains **no provider-specific code**. It calls whatever
`ModelClient` it is given, so the same loop runs against a hosted API, a local
server, or a recording. That is what allows the whole chain to be validated
offline before a single model call is paid for.

Two parsing rules that matter more than they look:

**A response that cannot be parsed is not an error to discard — it is data.**
It becomes an attempt with a parse failure recorded, because "the model returned
something unreadable" is a real extraction outcome and the dispersion across
attempts must include it. Dropping such attempts would silently shrink N and make
the instrument look more stable than it is.

**A null is not a zero.** A model that reports it cannot find a value is
returning information, and conflating that with a numerical zero would corrupt
every downstream statistic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

try:
    from .adapters import Completion, ModelClient, record_completion
    from .uncertainty import (CompositeSpec, categorical_disagreement,
                              composite_uncertainty,
                              ensemble_epistemic_term, numeric_dispersion,
                              normalised_token_entropy, sequence_similarity)
except ImportError:                                    # direct script execution
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from adapters import Completion, ModelClient, record_completion
    from uncertainty import (CompositeSpec, categorical_disagreement,
                             composite_uncertainty, ensemble_epistemic_term,
                             numeric_dispersion, normalised_token_entropy,
                             sequence_similarity)


SYSTEM_PROMPT = (
    "You extract quantitative data from scientific text. You return JSON only. "
    "If a value is not stated in the supplied text, return null for that field. "
    "Never infer, interpolate, or convert between units unless the conversion is "
    "exact and the source states both values. For every value, also report the "
    "verbatim span it came from."
)


# --------------------------------------------------------------------------
# Response parsing
# --------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def robust_json_loads(text: str) -> tuple[dict | None, str | None]:
    """Parse a model response into a dict. Returns (obj, error).

    Three fallbacks, in order: the raw text, the contents of a fenced code
    block, then the first balanced brace-delimited object. The third exists
    because models routinely prepend a sentence to otherwise-valid JSON, and
    discarding such a response would lose a perfectly usable attempt.
    """
    if text is None or not text.strip():
        return None, "empty response"

    for candidate in _candidates(text):
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(obj, dict):
            return obj, None
    return None, "no parseable JSON object"


def _candidates(text: str) -> list[str]:
    out = [text.strip()]
    for m in _FENCE.finditer(text):
        out.append(m.group(1).strip())
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[start:i + 1])
                    break
    return out


def parse_number(value) -> float | None:
    """Extract a float, or None. A bare null stays None -- it is not a zero."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _NUM.search(str(value))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _field_of(payload: dict, name: str) -> tuple[object, str | None]:
    """Return (value, evidence_span) for one variable, tolerating the common
    shapes a model uses: a bare value, or an object with value/span keys."""
    if name not in payload:
        return None, None
    entry = payload[name]
    if isinstance(entry, dict):
        for key in ("value", "extracted_value", "result"):
            if key in entry:
                return entry[key], (entry.get("span") or entry.get("evidence")
                                    or entry.get("quote"))
        return None, None
    return entry, None


# --------------------------------------------------------------------------
# Attempts
# --------------------------------------------------------------------------

@dataclass
class Attempt:
    model: str
    revision: str
    paraphrase_id: str
    text: str
    parsed: dict | None
    parse_error: str | None
    token_entropy: float
    error: str | None = None
    # Carried so that the written attempt log is directly usable as a
    # `ReplayClient` recording. Without these the log lacked a `prompt_key` and
    # the token distributions, so the offline replay path was advertised but
    # could not in fact be produced by the pipeline -- a capability that existed
    # only in the documentation.
    prompt_key: str = ""
    token_logprobs: list | None = None
    top_logprobs: list | None = None
    token_count: int | None = None


@dataclass
class ExtractionTask:
    """One paper and the variables to pull from it."""
    record_id: str
    domain: str
    domain_variable_set: str
    paper_text: str
    variables: list[str]
    source: dict = field(default_factory=dict)
    provenance_location: str = "prose"
    page: int | None = None


def build_user_prompt(task: ExtractionTask, paraphrase: str) -> str:
    """Assemble the user turn: paper text, field list, paraphrase instruction.

    The field list is generated from the task rather than hand-written, so the
    prompt and `domain_variable_set` cannot drift apart.
    """
    fields = "\n".join(f"  - {v}" for v in task.variables)
    return (
        f"Source text:\n---\n{task.paper_text}\n---\n\n"
        f"Extract the following {len(task.variables)} variables:\n{fields}\n\n"
        f"Return a JSON object with exactly these keys. For each value also report "
        f"the verbatim span it came from, as an object with `value` and `span`.\n\n"
        f"{paraphrase}"
    )


def run_attempts(task: ExtractionTask, clients: Sequence[ModelClient],
                 paraphrases: Sequence[dict], *, temperature: float = 0.7,
                 top_p: float = 1.0, max_tokens: int = 2024,
                 attempts_per_paraphrase: int = 1,
                 seed_base: int | None = None) -> list[Attempt]:
    """Run every (model, paraphrase, repeat) combination for one task."""
    attempts: list[Attempt] = []
    for client in clients:
        for p in paraphrases:
            user = build_user_prompt(task, p["instruction"])
            for rep in range(attempts_per_paraphrase):
                seed = None if seed_base is None else seed_base + rep
                c: Completion = client.complete(
                    SYSTEM_PROMPT, user, temperature=temperature, top_p=top_p,
                    max_tokens=max_tokens, seed=seed)
                parsed, err = (None, c.error) if c.error else robust_json_loads(c.text)
                attempts.append(Attempt(
                    model=client.name, revision=client.revision,
                    paraphrase_id=p["id"], text=c.text, parsed=parsed,
                    parse_error=err, token_entropy=c.mean_token_entropy,
                    error=c.error,
                    prompt_key=prompt_key(SYSTEM_PROMPT, user, client.name),
                    token_logprobs=c.token_logprobs,
                    top_logprobs=c.top_logprobs,
                    token_count=c.token_count))
    return attempts


# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------

def signals_for_variable(attempts: Sequence[Attempt], variable: str,
                         *, is_numeric: bool, n_levels: int | None = None,
                         spec: CompositeSpec | None = None) -> dict:
    """Compute Signals A, B and C for one variable from its attempts."""
    values, spans, per_model = [], [], {}
    for a in attempts:
        if a.parsed is None:
            # An unparseable attempt is a failed extraction, not a missing data
            # point. It is counted so that N reflects the true denominator.
            per_model.setdefault(a.model, []).append(None)
            continue
        raw, span = _field_of(a.parsed, variable)
        val = parse_number(raw) if is_numeric else (None if raw is None else str(raw))
        values.append(val)
        spans.append(span)
        per_model.setdefault(a.model, []).append(val)

    n_total = len(attempts)
    n_parsed = sum(1 for v in values if v is not None)

    if is_numeric:
        numeric_vals = [v for v in values if isinstance(v, (int, float))]
        signal_a, exclusion_rate, n_valid = numeric_dispersion(numeric_vals)
    else:
        labels = [v for v in values if v is not None]
        signal_a, _raw, n_valid = categorical_disagreement(labels, n_levels=n_levels)
        exclusion_rate = None

    # Signal B: pooled per-token entropy over the attempts that returned text.
    entropies = [a.token_entropy for a in attempts if np.isfinite(a.token_entropy)]
    signal_b = float(np.mean(entropies)) if entropies else float("nan")

    # Signal C: intra-model agreement minus inter-model agreement, on the same
    # similarity scale for both so the gap is meaningful.
    def _sim_series(vals):
        strs = ["" if v is None else str(v) for v in vals]
        pairs = [(strs[i], strs[j]) for i in range(len(strs))
                 for j in range(i + 1, len(strs))]
        return float(np.mean([sequence_similarity(x, y) for x, y in pairs])) \
            if pairs else float("nan")

    intra = [_sim_series(v) for v in per_model.values() if len(v) > 1]
    intra_mean = float(np.nanmean(intra)) if intra else float("nan")

    inter_pairs = []
    models = [m for m, v in per_model.items() if v]
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            a_vals = [v for v in per_model[models[i]] if v is not None]
            b_vals = [v for v in per_model[models[j]] if v is not None]
            if a_vals and b_vals:
                inter_pairs.append(sequence_similarity(str(a_vals[0]), str(b_vals[0])))
    inter_mean = float(np.mean(inter_pairs)) if inter_pairs else float("nan")

    signal_c = (ensemble_epistemic_term(intra_mean, inter_mean)
                if np.isfinite(intra_mean) and np.isfinite(inter_mean)
                else float("nan"))

    # PROVISIONAL composite, computed on RAW signal scales. This is deliberately
    # not the value the analysis should use: CV is unbounded, entropy is in nats,
    # and the epistemic term is bounded in [-1, 1], so averaging them raw lets
    # whichever has the widest range dominate -- and which one that is varies by
    # domain and variable type rather than being a modelling choice.
    #
    # `normalise_corpus` must be run over the finished corpus to percentile-
    # normalise the signals and rewrite `uncertainty`. `uncertainty_normalised`
    # is written False here and set True there, so a corpus that skipped the
    # second pass is detectable rather than silently wrong.
    comp = composite_uncertainty_detail(
        {"self_consistency": signal_a, "token_entropy": signal_b,
         "epistemic": signal_c}, spec)

    return {
        "signal_a_self_consistency": signal_a,
        "signal_b_token_entropy": signal_b,
        "signal_c_epistemic": signal_c,
        "uncertainty": comp["value"],
        "uncertainty_normalised": False,
        "n_signals_used": comp["n_signals"],
        "n_attempts": n_total,
        "n_parsed": n_parsed,
        "n_valid_attempts": n_valid,
        "outlier_exclusion_rate": exclusion_rate,
        "n_models_reporting": len(models),
        "values": values,
        "spans": spans,
        "parse_failure_rate": (n_total - n_parsed) / n_total if n_total else float("nan"),
    }


# --------------------------------------------------------------------------
# Record assembly
# --------------------------------------------------------------------------

def build_record(task: ExtractionTask, attempts: Sequence[Attempt],
                 numeric_variables: set[str], *, spec: CompositeSpec | None = None,
                 n_levels: int | None = None) -> dict:
    """Assemble one schema-conformant record from a task's attempts.

    `ground_truth_source` is set to `none` here and overwritten during Stage 3
    annotation or database matching. It is never guessed.
    """
    variables: dict = {}
    for name in task.variables:
        is_numeric = name in numeric_variables
        s = signals_for_variable(attempts, name, is_numeric=is_numeric,
                                 n_levels=n_levels, spec=spec)
        value = None
        for v in s["values"]:
            if v is not None:
                value = v
                break
        span = next((sp for sp in s["spans"] if sp), None)

        variables[name] = {
            "value": value,
            "as_reported": span or (str(value) if value is not None else "not reported"),
            "unit_reported": None,
            "unit_normalised": None,
            "value_type": "numeric" if is_numeric else "categorical",
            "uncertainty": (None if not np.isfinite(s["uncertainty"])
                            else float(s["uncertainty"])),
            "uncertainty_components": {
                "self_consistency": _finite(s["signal_a_self_consistency"]),
                "token_entropy": _finite(s["signal_b_token_entropy"]),
                "cross_model_agreement": _finite(s["signal_c_epistemic"]),
            },
            "n_attempts": s["n_attempts"],
            "n_valid_attempts": s["n_valid_attempts"],
            "outlier_exclusion_rate": _finite(s["outlier_exclusion_rate"]),
            "gold_value": None,
            "extraction_correct": None,
            "error_type": None,
        }

    return {
        "record_id": task.record_id,
        "domain": task.domain,
        "domain_variable_set": task.domain_variable_set,
        "ground_truth_source": "none",
        "uncertainty_normalised": False,
        "source": task.source,
        "provenance": {
            "location": task.provenance_location,
            "page": task.page,
            "evidence_span": next((sp for name in task.variables
                                   for sp in [variables[name]["as_reported"]]
                                   if sp and sp != "not reported"), "see variables"),
            "extraction_scope": "single_value",
        },
        "variables": variables,
    }


def _finite(x) -> float | None:
    return None if x is None or not np.isfinite(x) else float(x)


def normalise_corpus(records: Sequence[dict], *, spec: CompositeSpec | None = None
                     ) -> tuple[list[dict], dict]:
    """Second pass: percentile-normalise the signals and rewrite the composite.

    **Required between extraction and analysis.** The composite written during
    extraction is provisional because the three signals have incomparable
    ranges; this pass puts them on a common [0, 1] scale before combining.

    The normaliser is fitted on the whole corpus, which is the right scope for a
    *scale* transform: a percentile is a statement about where a value sits among
    its peers, and the peers are the corpus. The **conformal** calibration in
    Stage 3 is a different thing entirely and is fitted on the gold subset only.
    The two must not be confused, and conflating them would leak test data into
    the uncertainty score.

    Returns (records, report). Original records are not mutated.
    """
    import copy

    normaliser = SignalNormaliser()
    raw: dict[str, list] = {k: [] for k in SignalNormaliser.KEYS}
    for rec in records:
        for entry in (rec.get("variables") or {}).values():
            comps = (entry or {}).get("uncertainty_components") or {}
            raw["self_consistency"].append(comps.get("self_consistency"))
            raw["token_entropy"].append(comps.get("token_entropy"))
            raw["epistemic"].append(comps.get("cross_model_agreement"))
    normaliser.fit(raw)

    n_values = 0
    out: list[dict] = []
    for rec in records:
        new = copy.deepcopy(rec)
        for entry in (new.get("variables") or {}).values():
            comps = (entry or {}).get("uncertainty_components") or {}
            normed = normaliser.transform({
                "self_consistency": comps.get("self_consistency"),
                "token_entropy": comps.get("token_entropy"),
                "epistemic": comps.get("cross_model_agreement"),
            })
            detail = composite_uncertainty_detail(normed, spec)
            entry["uncertainty"] = _finite(detail["value"])
            entry["uncertainty_components_normalised"] = {
                k: _finite(v) for k, v in normed.items()}
            n_values += 1
        new["uncertainty_normalised"] = True
        out.append(new)

    return out, {
        "n_records": len(out),
        "n_values_rewritten": n_values,
        "signals_fitted": normaliser.fitted_signals,
        "note": ("signals that could not be fitted are left NaN and dropped from "
                 "the composite rather than replaced, so a value resting on one "
                 "signal stays identifiable"),
    }


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def load_paraphrases(path: str | Path) -> list[dict]:
    """Load the frozen paraphrase set. Refuses an empty or malformed set rather
    than running with a single prompt, which would make Signal A identically
    zero and look like perfect confidence."""
    with Path(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("paraphrases") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise ValueError(f"{path}: no paraphrases found")
    for i, item in enumerate(items):
        if not isinstance(item, dict) or "instruction" not in item:
            raise ValueError(f"{path}: paraphrase {i} has no 'instruction'")
        item.setdefault("id", f"p{i:02d}")
    if len(items) < 2:
        raise ValueError(
            f"{path}: only {len(items)} paraphrase; a single prompt makes Signal A "
            f"identically zero and would read as perfect confidence")
    return items


def run_corpus(tasks: Iterable[ExtractionTask], clients: Sequence[ModelClient],
               paraphrases: Sequence[dict], numeric_variables: set[str],
               *, record_path: str | Path, attempt_path: str | Path,
               temperature: float = 0.7, max_tokens: int = 2024,
               spec: CompositeSpec | None = None) -> dict:
    """Run every task, append records and raw attempts to disk, return a summary.

    Both files are appended and flushed per task, so an interrupted run leaves a
    usable partial corpus and can be resumed by record_id.
    """
    record_path = Path(record_path)
    attempt_path = Path(attempt_path)
    record_path.parent.mkdir(parents=True, exist_ok=True)

    done: set[str] = set()
    if record_path.exists():
        with record_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["record_id"])
                except (json.JSONDecodeError, KeyError):
                    continue

    n_written = 0
    with record_path.open("a", encoding="utf-8") as rf, \
            attempt_path.open("a", encoding="utf-8") as af:
        for task in tasks:
            if task.record_id in done:
                continue
            attempts = run_attempts(task, clients, paraphrases,
                                    temperature=temperature, max_tokens=max_tokens)
            record = build_record(task, attempts, numeric_variables, spec=spec)
            rf.write(json.dumps(record, default=str) + "\n")
            rf.flush()

            # Raw attempts are required, not optional: without them the
            # dispersion cannot be recomputed by a reader.
            # Written in the `ReplayClient` schema ON PURPOSE. A log that cannot
            # be replayed is an audit trail; a log that can be replayed is a
            # test fixture. The extra audit fields (`record_id`,
            # `paraphrase_id`, `parse_error`) are ignored by the replayer.
            for a in attempts:
                af.write(json.dumps({
                    "prompt_key": a.prompt_key,
                    "model": a.model,
                    "revision": a.revision,
                    "text": a.text,
                    "token_count": a.token_count,
                    "token_logprobs": a.token_logprobs,
                    "top_logprobs": a.top_logprobs,
                    "error": a.error,
                    "record_id": task.record_id,
                    "paraphrase_id": a.paraphrase_id,
                    "parse_error": a.parse_error,
                    "token_entropy": _finite(a.token_entropy),
                }, default=str) + "\n")
            af.flush()
            n_written += 1

    return {"records_written": n_written, "records_skipped": len(done),
            "record_path": str(record_path), "attempt_path": str(attempt_path)}
