"""
Stage 0 — per-record causal impact.

This module implements the paper's central metric, which is also the main
methodological change from the original proposal.

The original design measured one global Structural Hamming Distance per domain:
SHD(graph from original extractions, graph from corrected extractions). A single
number per domain cannot be correlated with anything, so the hypothesis that
extraction uncertainty predicts causal damage was untestable as written.

The fix: define impact *per record*.

    CI_i = SHD( G(D) , G(D with record i corrected) )

This yields n observations instead of one, which is what gives RQ4 statistical
power. Two scalar summaries are derived from the CI vector:

    r_impact  = corr(uncertainty_i, CI_i)              -- RQ4
    contrast  = mean(CI | high uncertainty)
                - mean(CI | low uncertainty, matched)  -- Stage 5 test 2

The second is the assumption-light test: if uncertainty is meaningful, repairing
an uncertain record must damage the graph more than repairing a certain one.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np

# Importable BOTH as a package member and as a top-level module, because every
# entry point in this repository reaches it the second way: `run_stage0.py`,
# `stage0/selftest.py`, and `analysis/causal.py` all put `stage0/` on sys.path
# and import `impact` by name. A bare `from .discovery import shd` raised
# "attempted relative import with no known parent package" on every one of those
# paths -- and because `causal.py` wraps its imports in a try/except ImportError,
# it would have reported *causal-learn is missing* while the real fault was this
# line. A misleading error is worse than a crash.
try:
    from .discovery import shd
except ImportError:                                    # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from discovery import shd


def per_record_impact(X_corrupted: np.ndarray, X_clean: np.ndarray,
                      discover: Callable,
                      rows: Sequence[int] | None = None,
                      max_records: int | None = None,
                      rng: np.random.Generator | None = None) -> dict:
    """Compute CI_i for each selected record.

    Parameters
    ----------
    X_corrupted : the dataset as extracted (errors present).
    X_clean     : the same dataset with true values, used as the correction target.
    rows        : which records to evaluate. Defaults to all.
    max_records : if set, a random subset is used. The cost is one full causal
                  discovery per record, so this bounds runtime on large n.

    Returns
    -------
    dict with the baseline graph, the per-record impact vector, and summary stats.
    """
    rng = np.random.default_rng() if rng is None else rng
    n = X_corrupted.shape[0]

    if rows is None:
        rows = np.arange(n)
    rows = np.asarray(rows, dtype=int)
    if max_records is not None and rows.size > max_records:
        rows = np.sort(rng.choice(rows, size=max_records, replace=False))

    baseline = discover(X_corrupted)

    impacts = np.zeros(rows.size, dtype=float)
    failed = 0
    for k, i in enumerate(rows):
        Xi = X_corrupted.copy()
        Xi[i, :] = X_clean[i, :]
        try:
            impacts[k] = shd(baseline, discover(Xi))
        except Exception:
            impacts[k] = np.nan
            failed += 1

    valid = ~np.isnan(impacts)
    return {
        "baseline_graph": baseline,
        "rows": rows,
        "impact": impacts,
        "n_evaluated": int(rows.size),
        "n_failed": int(failed),
        "mean_impact": float(np.nanmean(impacts)) if valid.any() else float("nan"),
        "frac_nonzero_impact": float(np.mean(impacts[valid] > 0)) if valid.any() else float("nan"),
    }


def impact_vs_uncertainty(uncertainty: np.ndarray, impact: np.ndarray,
                          rows: Sequence[int] | None = None) -> dict:
    """RQ4: correlate per-record uncertainty with per-record causal impact."""
    u = np.asarray(uncertainty, dtype=float)
    if rows is not None:
        u = u[np.asarray(rows, dtype=int)]
    c = np.asarray(impact, dtype=float)

    mask = ~(np.isnan(u) | np.isnan(c))
    u, c = u[mask], c[mask]
    if u.size < 4 or np.std(u) == 0 or np.std(c) == 0:
        return {"r_pearson": float("nan"), "r_spearman": float("nan"), "n": int(u.size)}

    pearson = float(np.corrcoef(u, c)[0, 1])
    spearman = _spearman(u, c)
    return {"r_pearson": pearson, "r_spearman": spearman, "n": int(u.size)}


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = _rank(a)
    rb = _rank(b)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def _rank(x: np.ndarray) -> np.ndarray:
    """Average ranks, ties handled."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size, dtype=float)
    ranks[order] = np.arange(x.size, dtype=float)
    # average tied ranks
    sorted_x = x[order]
    i = 0
    while i < sorted_x.size:
        j = i
        while j + 1 < sorted_x.size and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return ranks


# --------------------------------------------------------------------------
# Stage 5 test 2 — the high/low correction contrast
# --------------------------------------------------------------------------

def high_low_contrast(uncertainty: np.ndarray, impact: np.ndarray,
                      rows: Sequence[int] | None = None,
                      n_boot: int = 5000,
                      rng: np.random.Generator | None = None) -> dict:
    """Compare mean causal impact of repairing uncertain vs certain records.

    If the uncertainty metric carries information, this difference must be
    positive. The bootstrap CI makes the claim falsifiable: a CI spanning zero
    is evidence that the metric does not rank records by downstream importance.

    Note this specific test previously appeared in proposal v1 as a hypothesis
    but was never operationalised; it is the strongest single piece of evidence
    the study can produce, because it does not depend on any model of how
    uncertainty is generated.
    """
    rng = np.random.default_rng() if rng is None else rng
    u = np.asarray(uncertainty, dtype=float)
    if rows is not None:
        u = u[np.asarray(rows, dtype=int)]
    c = np.asarray(impact, dtype=float)

    mask = ~(np.isnan(u) | np.isnan(c))
    u, c = u[mask], c[mask]
    if u.size < 10:
        return {"difference": float("nan"), "n": int(u.size), "note": "too few records"}

    median = float(np.median(u))
    hi = c[u > median]
    lo = c[u <= median]
    if hi.size < 3 or lo.size < 3:
        return {"difference": float("nan"), "n": int(u.size), "note": "degenerate split"}

    diff = float(hi.mean() - lo.mean())
    pooled = np.concatenate([hi, lo])
    boot = np.empty(n_boot)
    for b in range(n_boot):
        s = rng.choice(pooled, size=pooled.size, replace=True)
        boot[b] = s[:hi.size].mean() - s[hi.size:].mean()
    lo_ci, hi_ci = np.percentile(boot, [2.5, 97.5])

    return {
        "difference": diff,
        "ci95": [float(lo_ci), float(hi_ci)],
        "excludes_zero": bool(lo_ci > 0 or hi_ci < 0),
        "mean_impact_high_uncertainty": float(hi.mean()),
        "mean_impact_low_uncertainty": float(lo.mean()),
        "n_high": int(hi.size),
        "n_low": int(lo.size),
        "n": int(u.size),
    }


# --------------------------------------------------------------------------
# Stage 5 test 1 — placebo / label shuffling
# --------------------------------------------------------------------------

def placebo_test(uncertainty: np.ndarray, impact: np.ndarray,
                 rows: Sequence[int] | None = None,
                 n_perm: int = 2000,
                 rng: np.random.Generator | None = None) -> dict:
    """Permute uncertainty across records and recompute the correlation.

    Returns the observed statistic and its position in the permutation null. A
    p-value near 1 here means the apparent effect is an artefact of the pipeline
    and not a property of extraction uncertainty.
    """
    rng = np.random.default_rng() if rng is None else rng
    observed = impact_vs_uncertainty(uncertainty, impact, rows=rows)
    r_obs = observed["r_spearman"]
    if not np.isfinite(r_obs):
        return {"observed_r": float("nan"), "p_permutation": float("nan")}

    u = np.asarray(uncertainty, dtype=float)
    if rows is not None:
        u = u[np.asarray(rows, dtype=int)]
    c = np.asarray(impact, dtype=float)
    mask = ~(np.isnan(u) | np.isnan(c))
    u, c = u[mask], c[mask]

    null = np.empty(n_perm)
    for k in range(n_perm):
        null[k] = _spearman(rng.permutation(u), c)

    p = float((np.abs(null) >= abs(r_obs)).mean())
    return {
        "observed_r": float(r_obs),
        "p_permutation": p,
        "null_mean": float(np.nanmean(null)),
        "null_sd": float(np.nanstd(null)),
        "n_perm": n_perm,
    }
