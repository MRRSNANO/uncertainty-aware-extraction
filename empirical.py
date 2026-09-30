"""
Stage 3-6 empirical analysis.

Takes validated extraction records plus the two gold standards and produces the
numbers behind RQ2, RQ4-RQ8. Provider-independent: it consumes records, not
model calls, so it can be written and tested before any extraction exists.

Data model
----------
Records follow `protocol/extraction_schema.json`. Everything here works on the
**flattened** form: one row per (record, variable). That is the correct unit
because extraction uncertainty is a per-value property, and flattening at record
level would destroy the pairing the whole analysis depends on.

Statistical discipline
----------------------
**Every confidence interval resamples papers, not values.** Values within a paper
share a document, a prompt set, and often a single table; their errors are
correlated. Resampling values would produce intervals that are far too narrow,
and that is the single most common way a result like this is made to look more
precise than it is. `cluster_bootstrap` exists so that the shortcut is never
taken by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


# --------------------------------------------------------------------------
# Flattening
# --------------------------------------------------------------------------

@dataclass
class ValueRow:
    record_id: str
    domain: str
    variable: str
    value: float | str | None
    uncertainty: float
    correct: int | None
    error_type: str | None
    location: str | None
    n_attempts: int | None
    n_valid_attempts: int | None
    exclusion_rate: float | None
    components: dict
    ground_truth_source: str | None


# The extraction pipeline writes the cross-model signal under
# `cross_model_agreement` (following the schema's vocabulary), while the
# normalisation pass writes it under `epistemic` (following Hamidieh et al.'s
# term). Both reach this module. Reading only one of them made
# `rq8_mode_collapse`'s cross-model catch rate silently NaN forever -- the
# single most important output of that diagnostic, disabled by a key name.
_COMPONENT_ALIASES = {
    "self_consistency": "self_consistency",
    "token_entropy": "token_entropy",
    "cross_model_agreement": "epistemic",
    "epistemic": "epistemic",
}


def _canonical_components(entry: dict) -> dict:
    """Return components under one canonical key set, preferring normalised ones.

    Normalised values are preferred because they are on a common scale; the raw
    ones are only comparable within a single signal.
    """
    raw = (entry.get("uncertainty_components_normalised")
           or entry.get("uncertainty_components") or {})
    out: dict = {}
    for key, value in raw.items():
        canonical = _COMPONENT_ALIASES.get(key)
        if canonical:
            out[canonical] = value
    return out


def flatten_records(records: Iterable[dict]) -> list[ValueRow]:
    """One row per (record, variable). Silently drops nothing that carries data.

    Values without an uncertainty are kept with NaN rather than dropped, so that
    the count of unscored values is visible in every downstream table. Dropping
    them here would make a partially-scored corpus look complete.
    """
    rows: list[ValueRow] = []
    for rec in records:
        rid = rec.get("record_id", "?")
        domain = rec.get("domain", "?")
        gts = rec.get("ground_truth_source")
        loc = (rec.get("provenance") or {}).get("location")
        for name, entry in (rec.get("variables") or {}).items():
            entry = entry or {}
            u = entry.get("uncertainty")
            rows.append(ValueRow(
                record_id=rid,
                domain=domain,
                variable=name,
                value=entry.get("value"),
                uncertainty=float(u) if u is not None else float("nan"),
                correct=(None if entry.get("extraction_correct") is None
                         else int(bool(entry["extraction_correct"]))),
                error_type=entry.get("error_type"),
                location=entry.get("value_location") or loc,
                n_attempts=entry.get("n_attempts"),
                n_valid_attempts=entry.get("n_valid_attempts"),
                exclusion_rate=entry.get("outlier_exclusion_rate"),
                components=_canonical_components(entry),
                ground_truth_source=gts,
            ))
    return rows


# --------------------------------------------------------------------------
# Ranking metrics
# --------------------------------------------------------------------------

def auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Probability a random erroneous value outranks a random correct one.

    Computed by rank (Mann-Whitney U) rather than by integrating an ROC curve,
    because ties are common in these scores -- many values have dispersion
    exactly zero -- and the rank form handles them correctly via mid-ranks.
    0.5 is chance; 1.0 is perfect ranking.
    """
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    mask = np.isfinite(s) & np.isfinite(y)
    s, y = s[mask], y[mask]
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = _midranks(s)
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _midranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size, dtype=float)
    ranks[order] = np.arange(1, x.size + 1, dtype=float)
    sx = x[order]
    i = 0
    while i < sx.size:
        j = i
        while j + 1 < sx.size and sx[j + 1] == sx[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    return ranks


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(_midranks(x), _midranks(y))[0, 1])


# --------------------------------------------------------------------------
# Cluster bootstrap
# --------------------------------------------------------------------------

def cluster_bootstrap(rows: Sequence[ValueRow],
                      statistic,
                      B: int = 2000,
                      rng: np.random.Generator | None = None,
                      alpha: float = 0.05) -> dict:
    """Percentile CI for `statistic(sample_rows)` resampling **papers**.

    `statistic` receives a list of ValueRows and returns a float.
    """
    rng = np.random.default_rng() if rng is None else rng
    groups: dict[str, list[ValueRow]] = {}
    for r in rows:
        groups.setdefault(r.record_id, []).append(r)
    keys = list(groups)
    if len(keys) < 3:
        return {"estimate": float("nan"), "ci": [float("nan"), float("nan")],
                "n_papers": len(keys), "note": "fewer than 3 papers; CI not estimable"}

    point = statistic(list(rows))
    draws = np.empty(B, dtype=float)
    for b in range(B):
        idx = rng.integers(0, len(keys), size=len(keys))
        sample: list[ValueRow] = []
        for i in idx:
            sample.extend(groups[keys[i]])
        draws[b] = statistic(sample)

    finite = draws[np.isfinite(draws)]
    if finite.size == 0:
        return {"estimate": point, "ci": [float("nan"), float("nan")],
                "n_papers": len(keys), "note": "no finite bootstrap draws"}
    lo, hi = np.percentile(finite, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {
        "estimate": float(point),
        "ci": [float(lo), float(hi)],
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "n_papers": len(keys),
        "n_values": len(rows),
        "n_bootstrap": int(finite.size),
    }


# --------------------------------------------------------------------------
# RQ2 — does uncertainty track error?
# --------------------------------------------------------------------------

def rq2_uncertainty_vs_error(rows: Sequence[ValueRow], B: int = 2000,
                             rng: np.random.Generator | None = None) -> dict:
    """The validity check for the uncertainty metric itself.

    Three complementary summaries, because each fails differently:

      * Spearman correlation with the error indicator -- monotone association.
      * AUC -- ranking quality, which is what a threshold rule actually uses.
      * Separation of the *ambiguity* and *epistemic* error classes, which is
        where the substantive finding lives. A metric that catches source
        ambiguity but not hallucination is a different instrument from one that
        catches both, and collapsing the taxonomy would hide that.
    """
    labelled = [r for r in rows if r.correct is not None and np.isfinite(r.uncertainty)]
    if not labelled:
        return {"note": "no labelled values with uncertainty"}

    scores = [r.uncertainty for r in labelled]
    labels = [1 - r.correct for r in labelled]          # 1 == erroneous

    out: dict = {
        "n_values": len(labelled),
        "n_papers": len({r.record_id for r in labelled}),
        "error_rate": float(np.mean(labels)),
        "auc": auc(scores, labels),
        # One implementation of Spearman, not two. The inline mid-rank version
        # that stood here duplicated `spearman` exactly, which is how two
        # copies of a statistic drift apart.
        "spearman_uncertainty_vs_error": (
            spearman(scores, labels) if len(set(labels)) > 1 else float("nan")),
        "auc_ci": cluster_bootstrap(labelled, lambda rs: auc(
            [r.uncertainty for r in rs], [1 - r.correct for r in rs]), B=B, rng=rng),
    }

    # Separation by error class. `ambiguous_source` is aleatoric; the rest are
    # epistemic. This split is the reason the codebook keeps the taxonomy.
    aleatoric = [r for r in labelled if r.error_type == "ambiguous_source"]
    epistemic = [r for r in labelled if r.error_type in
                 ("hallucinated", "wrong_value", "wrong_unit", "wrong_scale",
                  "collapsed_range", "wrong_variable")]
    out["mean_uncertainty"] = {
        "ambiguous_source": float(np.mean([r.uncertainty for r in aleatoric]))
        if aleatoric else float("nan"),
        "epistemic": float(np.mean([r.uncertainty for r in epistemic]))
        if epistemic else float("nan"),
        "correct": float(np.mean([r.uncertainty for r in labelled if r.correct == 1])),
        "n_ambiguous_source": len(aleatoric),
        "n_epistemic": len(epistemic),
    }
    # If uncertainty flags ambiguity but not hallucination, these two means
    # diverge sharply, and that is the paper's most interesting single result.
    out["flags_aleatoric_not_epistemic"] = bool(
        np.isfinite(out["mean_uncertainty"]["ambiguous_source"])
        and np.isfinite(out["mean_uncertainty"]["epistemic"])
        and out["mean_uncertainty"]["ambiguous_source"]
        > out["mean_uncertainty"]["epistemic"] + 0.15)
    return out


# --------------------------------------------------------------------------
# RQ8 — mode collapse
# --------------------------------------------------------------------------

def rq8_mode_collapse(rows: Sequence[ValueRow], collapsed_threshold: float = 0.05
                      ) -> dict:
    """Share of errors produced with dispersion at or near zero.

    The threshold is on the composite uncertainty, and it is stated here rather
    than tuned. The pre-registered bands are in the protocol: above 30 % means
    dispersion alone is not a sufficient instrument for extraction; below 10 %
    with the cross-model signal catching most of them supports the multi-signal
    design.
    """
    labelled = [r for r in rows if r.correct is not None and np.isfinite(r.uncertainty)]
    errors = [r for r in labelled if r.correct == 0]
    if not errors:
        return {"note": "no erroneous values in the corpus"}

    collapsed = [r for r in errors if r.uncertainty <= collapsed_threshold]
    diffuse = [r for r in errors if r.uncertainty > collapsed_threshold]
    share = len(collapsed) / len(errors)

    # Restricted to the epistemic classes, which is what the diagnostic targets:
    # a source-ambiguous value that scores low is a different (and milder)
    # failure from a confidently hallucinated one.
    epistemic = [r for r in errors if r.error_type in
                 ("hallucinated", "wrong_value", "wrong_scale", "wrong_unit",
                  "collapsed_range", "wrong_variable")]
    ep_collapsed = [r for r in epistemic if r.uncertainty <= collapsed_threshold]

    # Does the cross-model term flag what dispersion misses? This is the
    # diagnostic's whole point: if the cross-model signal catches the collapsed
    # cases, the multi-signal design is justified; if it does not, dispersion
    # alone is insufficient AND the mitigation is insufficient, which is a
    # materially worse finding.
    failures = collapsed                      # `collapsed` is already all errors
    caught = []
    for r in failures:
        eu = (r.components or {}).get("epistemic")
        if eu is not None and np.isfinite(eu):
            caught.append(eu > collapsed_threshold)
    caught_rate = float(np.mean(caught)) if caught else float("nan")

    if share > 0.30:
        verdict = ("dispersion alone is not a sufficient uncertainty instrument for "
                   "extraction; report as the primary finding about the metric")
    elif share < 0.10:
        verdict = ("dispersion holds; the multi-signal design is supported provided "
                   "the cross-model term catches most collapsed cases")
    else:
        verdict = "intermediate; report the share and the cross-model catch rate together"

    return {
        "n_errors": len(errors),
        "collapsed_share": share,
        "collapsed_threshold": collapsed_threshold,
        "n_collapsed": len(collapsed),
        "n_diffuse": len(diffuse),
        "epistemic_collapsed_share": (len(ep_collapsed) / len(epistemic)
                                      if epistemic else float("nan")),
        "cross_model_catch_rate": caught_rate,
        "n_with_epistemic_component": len(caught),
        "verdict": verdict,
    }


# --------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------

def reliability_bins(rows: Sequence[ValueRow], n_bins: int = 8) -> list[dict]:
    """Predicted uncertainty against observed error rate, in equal-count bins.

    Equal-count rather than equal-width, because uncertainty scores are strongly
    skewed toward zero and equal-width bins would leave most bins empty.
    """
    labelled = [r for r in rows if r.correct is not None and np.isfinite(r.uncertainty)]
    if len(labelled) < n_bins * 2:
        return []
    labelled = sorted(labelled, key=lambda r: r.uncertainty)
    out = []
    for b in range(n_bins):
        lo = b * len(labelled) // n_bins
        hi = (b + 1) * len(labelled) // n_bins
        chunk = labelled[lo:hi]
        if not chunk:
            continue
        out.append({
            "bin": b,
            "n": len(chunk),
            "mean_uncertainty": float(np.mean([r.uncertainty for r in chunk])),
            "observed_error_rate": float(np.mean([1 - r.correct for r in chunk])),
        })
    return out


def exclusion_rate_report(rows: Sequence[ValueRow]) -> dict:
    """Outlier exclusions, reported rather than hidden.

    A high exclusion rate is the study's own best evidence that some source
    values are genuinely not pinned down, so it is a result and not a nuisance
    statistic.
    """
    rates = [r.exclusion_rate for r in rows if r.exclusion_rate is not None]
    if not rates:
        return {"note": "no exclusion rates recorded"}
    arr = np.asarray(rates, dtype=float)
    by_location: dict[str, list[float]] = {}
    for r in rows:
        if r.exclusion_rate is None:
            continue
        by_location.setdefault(r.location or "unknown", []).append(r.exclusion_rate)
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "frac_any_exclusion": float((arr > 0).mean()),
        "by_location": {k: {"n": len(v), "mean": float(np.mean(v))}
                        for k, v in sorted(by_location.items())},
    }


# --------------------------------------------------------------------------
# RQ6 — cross-domain
# --------------------------------------------------------------------------

def cross_domain_comparison(rows: Sequence[ValueRow], B: int = 2000,
                            rng: np.random.Generator | None = None) -> dict:
    """Compare the uncertainty-error relationship across domains.

    The two domains are never pooled into a single accuracy figure: BDD is
    validated against hand annotation and perovskite against an external
    database, so pooling would average two different measurement procedures.
    This function keeps them apart and reports the difference.
    """
    out: dict = {}
    for domain in sorted({r.domain for r in rows}):
        sub = [r for r in rows if r.domain == domain]
        out[domain] = {
            "n_values": len(sub),
            "n_papers": len({r.record_id for r in sub}),
            "ground_truth_source": sorted({r.ground_truth_source for r in sub
                                           if r.ground_truth_source}),
            "rq2": rq2_uncertainty_vs_error(sub, B=B, rng=rng),
            "exclusions": exclusion_rate_report(sub),
        }
    # Same-domain contrast on the study's actual independent variable.
    by_location: dict[str, list[ValueRow]] = {}
    for r in rows:
        by_location.setdefault(r.location or "unknown", []).append(r)
    out["by_value_location"] = {
        k: {"n": len(v), "auc": auc([r.uncertainty for r in v if r.correct is not None],
                                    [1 - r.correct for r in v if r.correct is not None])}
        for k, v in sorted(by_location.items())
    }
    return out
