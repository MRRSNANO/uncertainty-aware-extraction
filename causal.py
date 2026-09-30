"""
Stage 4-6 — causal driver.

Joins extracted records to the simulation-tested machinery in `stage0/` and
produces RQ4 (per-record causal impact), RQ5 (edge stability, weighted versus
uniform) and the null tests.

Structural Hamming Distance is **not** reimplemented here. `stage0/discovery.py`
owns the single implementation in this project, and this module imports it, so
there is one place for the endpoint convention to be wrong rather than two.

This module therefore requires `causal-learn`. Everything else in `analysis/`
runs on NumPy alone; this file does not, and it says so at import time rather
than failing later with an obscure error.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

# `stage0/` is a sibling package, not an installed one.
_STAGE0 = Path(__file__).resolve().parent.parent / "stage0"
if str(_STAGE0) not in sys.path:
    sys.path.insert(0, str(_STAGE0))

try:
    from discovery import edge_stability, make_discoverer, shd, skeleton_edges
    from impact import (high_low_contrast, impact_vs_uncertainty,
                        per_record_impact, placebo_test)
    _HAVE_CAUSAL = True
    _CAUSAL_IMPORT_ERROR: str | None = None
except ImportError as exc:                             # pragma: no cover
    _HAVE_CAUSAL = False
    _CAUSAL_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def require_causal() -> None:
    if not _HAVE_CAUSAL:
        raise RuntimeError(
            "causal-learn is not installed, so Stage 4-6 cannot run. "
            f"Import failed with {_CAUSAL_IMPORT_ERROR}. "
            "Install with: python -m pip install causal-learn")


# --------------------------------------------------------------------------
# Dataset construction
# --------------------------------------------------------------------------

@dataclass
class Dataset:
    """A rectangular dataset for structure learning.

    One row per record (a device or experiment), one column per variable.
    `X` holds extracted values; `X_gold` holds gold-standard values where they
    exist and falls back to the extracted value elsewhere; `gold_mask` records
    which cells were actually verified, so a row's evaluability is never assumed.
    """
    record_ids: list[str]
    variables: list[str]
    X: np.ndarray
    U: np.ndarray                       # per-record uncertainty
    X_gold: np.ndarray
    gold_mask: np.ndarray
    domain: str = "?"

    @property
    def n(self) -> int:
        return self.X.shape[0]

    @property
    def d(self) -> int:
        return self.X.shape[1]

    def evaluable_rows(self, min_gold_fraction: float = 0.5) -> np.ndarray:
        """Rows with enough verified cells for a correction to mean anything.

        Correcting a row whose cells are mostly unverified would compare the
        graph against itself, producing an impact of zero that looks like
        robustness rather than missing data.
        """
        frac = self.gold_mask.mean(axis=1)
        return np.where(frac >= min_gold_fraction)[0]


def _to_float(v) -> float:
    if v is None:
        return np.nan
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v))
    except (TypeError, ValueError):
        return np.nan


def build_dataset(records: Sequence[dict], variables: Sequence[str],
                  *, aggregate: str = "mean") -> Dataset:
    """Turn schema records into a Dataset over an explicit variable list.

    `variables` is passed in rather than inferred, because variable selection is
    a domain-knowledge decision the protocol fixes at 5-8 per domain. Inferring
    it from the data would let an incidental coverage pattern decide the graph.

    Categorical variables must be encoded to integers before this point; a
    string column would become NaN and silently drop the variable.
    """
    variables = list(variables)
    d = len(variables)
    if d < 2:
        raise ValueError("need at least 2 variables")

    rows_x, rows_gold, rows_mask, rows_u, ids = [], [], [], [], []
    for rec in records:
        vars_ = rec.get("variables") or {}
        x = np.full(d, np.nan)
        g = np.full(d, np.nan)
        m = np.zeros(d, dtype=bool)
        us = []
        for j, name in enumerate(variables):
            entry = vars_.get(name)
            if not entry:
                continue
            x[j] = _to_float(entry.get("value"))
            gold = entry.get("gold_value")
            if gold is not None and entry.get("extraction_correct") is not None:
                g[j] = _to_float(gold)
                m[j] = True
                us.append(_to_float(entry.get("uncertainty")))
            elif entry.get("uncertainty") is not None:
                us.append(_to_float(entry.get("uncertainty")))
        if not us:
            continue
        rows_x.append(x)
        rows_gold.append(np.where(m, g, x))
        rows_mask.append(m)
        rows_u.append(float(np.nanmean(us)) if aggregate == "mean"
                      else float(np.nanmax(us)))
        ids.append(rec.get("record_id", f"R{len(ids)}"))

    if not rows_x:
        raise ValueError("no usable records: every record lacked uncertainty values")

    ds = Dataset(
        record_ids=ids, variables=variables,
        X=np.vstack(rows_x), U=np.asarray(rows_u, dtype=float),
        X_gold=np.vstack(rows_gold), gold_mask=np.vstack(rows_mask),
        domain=str(records[0].get("domain", "?")),
    )
    _require_complete(ds)
    return ds


def _require_complete(ds: Dataset, max_missing_fraction: float = 0.2) -> None:
    """Refuse a dataset with too many missing cells.

    PC cannot use rows with NaN, and every implementation drops them silently.
    Dropping at 30 % missingness would leave a graph learned from a different
    sample than the one the uncertainty weights describe -- a mismatch that no
    downstream diagnostic would reveal.
    """
    missing = float(np.isnan(ds.X).mean())
    if missing > max_missing_fraction:
        raise ValueError(
            f"{missing:.0%} of cells are missing, above the {max_missing_fraction:.0%} "
            f"limit. Structure learning would silently drop those rows and the graph "
            f"would be learned from a different sample than the weights describe. "
            f"Restrict the variable set or impute explicitly, and record the choice.")


# --------------------------------------------------------------------------
# RQ4 — uncertainty against per-record causal impact
# --------------------------------------------------------------------------

def rq4_impact(ds: Dataset, *, algorithm: str = "pc", alpha: float = 0.05,
               max_records: int | None = None, B: int = 500,
               rng: np.random.Generator | None = None) -> dict:
    """Correlate per-record extraction uncertainty with per-record causal impact.

    The impact of a record is the SHD induced by correcting that record to its
    gold values. Rows without enough verified cells are excluded, and the
    exclusion count is reported -- it is the difference between "no effect" and
    "no data", and the two must never be confused.
    """
    require_causal()
    rng = np.random.default_rng() if rng is None else rng

    evaluable = ds.evaluable_rows()
    excluded = ds.n - evaluable.size
    if evaluable.size < 5:
        return {"note": f"only {evaluable.size} evaluable records; RQ4 not estimable",
                "n_evaluable": int(evaluable.size), "n_excluded": int(excluded)}

    discover = make_discoverer(algorithm, alpha=alpha, discrete=False)
    imp = per_record_impact(ds.X, ds.X_gold, discover, rows=evaluable,
                            max_records=max_records, rng=rng)

    rq4 = impact_vs_uncertainty(ds.U, imp["impact"], rows=imp["rows"])
    contrast = high_low_contrast(ds.U, imp["impact"], rows=imp["rows"],
                                 n_boot=1000, rng=rng)
    placebo = placebo_test(ds.U, imp["impact"], rows=imp["rows"],
                           n_perm=B, rng=rng)

    return {
        "n_evaluable": int(evaluable.size),
        "n_excluded": int(excluded),
        "mean_impact": imp["mean_impact"],
        "frac_nonzero_impact": imp["frac_nonzero_impact"],
        "n_failed_discoveries": imp["n_failed"],
        "r_impact": rq4,
        "high_low_contrast": contrast,
        "placebo": placebo,
        "verdict": _rq4_verdict(contrast, placebo),
    }


def _rq4_verdict(contrast: dict, placebo: dict) -> str:
    """Apply the pre-registered reading rather than narrating the numbers."""
    excl = bool(contrast.get("excludes_zero"))
    p = placebo.get("p_permutation", float("nan"))
    if not np.isfinite(p):
        return "placebo test not estimable; report as inconclusive"
    if excl and p < 0.05:
        return ("H1 supported: high-uncertainty records carry more causal impact than "
                "low-uncertainty ones, and the effect survives permutation")
    if not excl and p >= 0.05:
        return ("H2: no detectable association. Check that the confidence interval "
                "excludes the substantial-effect threshold before calling this a "
                "reassurance result rather than an underpowered one")
    return ("mixed: contrast and permutation disagree. Report both and treat the "
            "result as inconclusive rather than choosing the favourable one")


# --------------------------------------------------------------------------
# RQ5 — weighted versus uniform resampling
# --------------------------------------------------------------------------

def weighting_from_uncertainty(U: np.ndarray, scheme: str = "linear") -> np.ndarray:
    """Map uncertainty to sampling weights.

    All schemes are monotone decreasing in uncertainty, so they agree on the
    ordering and differ only in how sharply they discount. The primary
    specification is `linear` (w = 1/(1+U)); the others exist so that the
    sensitivity analysis the protocol promises is a table rather than a claim.
    """
    U = np.asarray(U, dtype=float)
    U = np.where(np.isfinite(U), U, float(np.nanmax(U)) if np.isfinite(U).any() else 0.0)
    if scheme == "linear":
        w = 1.0 / (1.0 + U)
    elif scheme == "exponential":
        w = np.exp(-U)
    elif scheme == "rank":
        order = np.argsort(np.argsort(U))          # 0 = most certain
        w = 1.0 / (1.0 + order / max(len(U) - 1, 1))
    elif scheme == "inverse_square":
        w = 1.0 / (1.0 + U) ** 2
    else:
        raise ValueError(f"unknown weighting scheme: {scheme!r}")
    return w


def rq5_weighting(ds: Dataset, *, algorithm: str = "pc", alpha: float = 0.05,
                  B: int = 200, schemes: Sequence[str] = ("linear", "exponential",
                                                          "rank", "inverse_square"),
                  rng: np.random.Generator | None = None) -> dict:
    """Does weighting by uncertainty change the recovered structure?

    The decisive comparison is against **uniform weights**, which is baseline B3.
    If weighted and uniform resampling produce indistinguishable structures, the
    practical recommendation inverts and that is a publishable outcome under H2,
    not a failure of the study.
    """
    require_causal()
    rng = np.random.default_rng() if rng is None else rng
    discover = make_discoverer(algorithm, alpha=alpha, discrete=False)

    stable_uniform = edge_stability(ds.X, discover, B=B, weights=None, rng=rng)
    all_edges = sorted(set(stable_uniform))
    ref = np.array([stable_uniform.get(e, 0.0) for e in all_edges], dtype=float)

    out: dict = {
        "n_edges_uniform": len(all_edges),
        "mean_stability_uniform": float(ref.mean()) if ref.size else float("nan"),
        "schemes": {},
    }
    for scheme in schemes:
        w = weighting_from_uncertainty(ds.U, scheme)
        stable_w = edge_stability(ds.X, discover, B=B, weights=w, rng=rng)
        vec = np.array([stable_w.get(e, 0.0) for e in all_edges], dtype=float)
        delta = vec - ref
        out["schemes"][scheme] = {
            "mean_stability": float(vec.mean()) if vec.size else float("nan"),
            "mean_abs_change_vs_uniform": float(np.abs(delta).mean()) if vec.size else float("nan"),
            "max_abs_change_vs_uniform": float(np.abs(delta).max()) if vec.size else float("nan"),
            "edges_gained": int((delta > 0).sum()),
            "edges_lost": int((delta < 0).sum()),
        }
    changes = [v["mean_abs_change_vs_uniform"] for v in out["schemes"].values()
               if np.isfinite(v["mean_abs_change_vs_uniform"])]
    out["verdict"] = (
        "uniform weighting is adequate: no scheme moves edge stability materially"
        if changes and max(changes) < 0.05 else
        "weighting matters: at least one scheme moves edge stability materially, "
        "so propagation is not optional")
    return out


# --------------------------------------------------------------------------
# Baselines
# --------------------------------------------------------------------------

def baseline_table(ds: Dataset, *, algorithm: str = "pc", alpha: float = 0.05,
                   B: int = 200, rng: np.random.Generator | None = None) -> dict:
    """The five baselines the protocol commits to, computed where possible."""
    require_causal()
    rng = np.random.default_rng() if rng is None else rng
    discover = make_discoverer(algorithm, alpha=alpha, discrete=False)

    g_extracted = discover(ds.X)
    evaluable = ds.evaluable_rows()
    g_gold = discover(ds.X_gold) if evaluable.size else None

    out = {
        "B3_uniform_vs_weighted": rq5_weighting(ds, algorithm=algorithm,
                                                alpha=alpha, B=B, rng=rng),
        "n_edges_extracted": len(skeleton_edges(g_extracted)),
        "n_edges_gold": len(skeleton_edges(g_gold)) if g_gold is not None else None,
    }
    if g_gold is not None:
        out["shd_extracted_vs_gold"] = int(shd(g_extracted, g_gold))
    return out


# --------------------------------------------------------------------------
# Full report
# --------------------------------------------------------------------------

def full_report(ds: Dataset, *, algorithm: str = "pc", alpha: float = 0.05,
                B: int = 200, max_records: int | None = None,
                rng: np.random.Generator | None = None) -> dict:
    """Everything Stage 4-6 can produce from one domain's dataset."""
    require_causal()
    rng = np.random.default_rng() if rng is None else rng
    return {
        "domain": ds.domain,
        "n_records": ds.n,
        "n_variables": ds.d,
        "variables": ds.variables,
        "gold_coverage": float(ds.gold_mask.mean()),
        "rq4": rq4_impact(ds, algorithm=algorithm, alpha=alpha,
                          max_records=max_records, rng=rng),
        "rq5": rq5_weighting(ds, algorithm=algorithm, alpha=alpha, B=B, rng=rng),
        "baselines": baseline_table(ds, algorithm=algorithm, alpha=alpha, B=B, rng=rng),
    }
