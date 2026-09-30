"""
Stage 2 pilot — variance decomposition (RQ7).

Pure NumPy. Answers one question: *where is the variance?* — before the
extraction budget is spent on the wrong axis.

Motivation. Ẓatuchin (2026) decomposes response variance into resampling, prompt
paraphrase, model identity and query language, and finds the paraphrase component
near zero, with repeats past the fifth buying roughly 0.0003 in relative-error
variance. That was measured on brand-answer questions. If it holds for scientific
extraction, then ten paraphrased runs per value is ten times the cost for a
fraction of the signal — and the dispersion used as the uncertainty metric would
be dominated by decoding noise rather than by anything about the source text.

Design, from `fieldwork/variance_decomposition_pilot.md`:

    cell A   model M1, fixed prompt,      5 runs   -> decoding variance
    cell B   model M1, paraphrases P1-P10, 3 runs each -> paraphrase variance
    cell C   models M2 and M3, fixed prompt, 5 runs each -> model variance

Three runs per paraphrase cell rather than one is deliberate: with a single run,
the observed spread across paraphrases is `sigma2_paraphrase + sigma2_decoding`
and the two cannot be separated, which is precisely the confusion the pilot
exists to resolve.

Estimates are **moment-based**, and negative values are returned as negative.
A negative component estimate is the standard signal that the component is
indistinguishable from noise at this sample size. Truncating it to zero would
invent a component that is not there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np


# --------------------------------------------------------------------------
# Scale
# --------------------------------------------------------------------------

def log_transform(values: Sequence[float], require_positive: bool = True
                  ) -> np.ndarray:
    """Put numeric values on a comparable scale.

    Without this the decomposition is dominated by whichever variable happens to
    have the largest units: a thickness in micrometres will swamp an efficiency
    in percent. Log scale also matches how relative extraction error behaves --
    getting 21.3 instead of 21.0 is a different magnitude of mistake from
    getting 2.13 instead of 21.0.

    The pilot is restricted to strictly positive numeric variables. Raising
    rather than silently taking log|v| keeps that restriction visible.
    """
    arr = np.asarray(values, dtype=float)
    if require_positive and np.any(arr <= 0):
        raise ValueError(
            "log transform requires strictly positive values; restrict the "
            "pilot to positive numeric variables rather than patching the scale")
    return np.log(arr)


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------

@dataclass
class VarianceComponents:
    sigma2_decoding: float
    sigma2_paraphrase: float
    sigma2_model: float
    n_paraphrase_cells: int
    n_per_paraphrase_cell: int
    n_model_cells: int
    n_per_model_cell: int
    n_decoding_runs: int

    @property
    def total(self) -> float:
        return self.sigma2_decoding + self.sigma2_paraphrase + self.sigma2_model

    @property
    def share_decoding(self) -> float:
        return self._share(self.sigma2_decoding)

    @property
    def share_paraphrase(self) -> float:
        return self._share(self.sigma2_paraphrase)

    @property
    def share_model(self) -> float:
        return self._share(self.sigma2_model)

    def _share(self, x: float) -> float:
        t = self.total
        if not np.isfinite(t) or t <= 0:
            return float("nan")
        return x / t

    def as_dict(self) -> dict:
        return {
            "sigma2_decoding": self.sigma2_decoding,
            "sigma2_paraphrase": self.sigma2_paraphrase,
            "sigma2_model": self.sigma2_model,
            "share_decoding": self.share_decoding,
            "share_paraphrase": self.share_paraphrase,
            "share_model": self.share_model,
            "negative_components": [k for k, v in
                                    (("decoding", self.sigma2_decoding),
                                     ("paraphrase", self.sigma2_paraphrase),
                                     ("model", self.sigma2_model))
                                    if v < 0],
        }


def _pooled_within_variance(cells: Iterable[np.ndarray]) -> float:
    """Pooled within-cell variance, weighting each cell by its degrees of freedom."""
    num = 0.0
    den = 0.0
    for c in cells:
        c = np.asarray(c, dtype=float)
        c = c[np.isfinite(c)]
        if c.size < 2:
            continue
        num += (c.size - 1) * float(np.var(c, ddof=1))
        den += (c.size - 1)
    if den <= 0:
        return float("nan")
    return num / den


def variance_components(decoding_values: Sequence[float],
                        paraphrase_cells: Sequence[Sequence[float]],
                        model_cells: Sequence[Sequence[float]],
                        ) -> VarianceComponents:
    """Moment-based decomposition of one value's extraction variance.

    `paraphrase_cells` should contain 10 cells of 3 runs; `model_cells` should
    contain 3 cells of 5 runs. Fewer is tolerated but widens the confidence
    interval on the corresponding component, and the cell counts are returned so
    the caller can weight or filter accordingly.
    """
    a = np.asarray([v for v in decoding_values if np.isfinite(v)], dtype=float)
    b = [np.asarray([v for v in c if np.isfinite(v)], dtype=float) for c in paraphrase_cells]
    c = [np.asarray([v for v in cell if np.isfinite(v)], dtype=float) for cell in model_cells]
    b = [x for x in b if x.size >= 1]
    c = [x for x in c if x.size >= 1]

    if a.size < 2 or len(b) < 2 or len(c) < 2:
        raise ValueError("need >= 2 decoding runs, >= 2 paraphrase cells, "
                         ">= 2 model cells")

    # Decoding variance is pooled across every cell in the design, since the
    # decoding process is the same everywhere. Cells A, B and C are all
    # replicate runs at fixed model and prompt, so all contribute.
    sigma2_dec = _pooled_within_variance([a] + b + c)

    n_b = int(round(float(np.mean([x.size for x in b]))))
    n_c = int(round(float(np.mean([x.size for x in c]))))
    n_b = max(n_b, 1)
    n_c = max(n_c, 1)

    means_b = np.array([float(np.mean(x)) for x in b], dtype=float)
    means_c = np.array([float(np.mean(x)) for x in c], dtype=float)

    # Sample variance of cell means is inflated by the estimation error of each
    # mean; subtracting sigma2_dec / n leaves the between-cell component. It may
    # go negative, and it is returned that way on purpose.
    sigma2_para = float(np.var(means_b, ddof=1) - sigma2_dec / n_b)
    sigma2_model = float(np.var(means_c, ddof=1) - sigma2_dec / n_c)

    return VarianceComponents(
        sigma2_decoding=float(sigma2_dec),
        sigma2_paraphrase=sigma2_para,
        sigma2_model=sigma2_model,
        n_paraphrase_cells=len(b),
        n_per_paraphrase_cell=n_b,
        n_model_cells=len(c),
        n_per_model_cell=n_c,
        n_decoding_runs=int(a.size),
    )


# --------------------------------------------------------------------------
# Pooling and bootstrap
# --------------------------------------------------------------------------

def pool(components: Sequence[VarianceComponents]) -> dict:
    """Average components across values, then compute shares from the averages.

    Averaging the components rather than the shares is the right order: a share
    is a ratio, and averaging ratios across values with different total variances
    over-weights the low-variance values.

    Negative components are **not** dropped before averaging. Dropping them would
    bias every remaining estimate upward and would hide exactly the case the
    pilot is looking for.
    """
    if not components:
        raise ValueError("no components to pool")
    dec = float(np.mean([x.sigma2_decoding for x in components]))
    para = float(np.mean([x.sigma2_paraphrase for x in components]))
    mod = float(np.mean([x.sigma2_model for x in components]))
    total = dec + para + mod
    share = (lambda v: v / total if np.isfinite(total) and total > 0 else float("nan"))
    return {
        "n_values": len(components),
        "sigma2_decoding": dec,
        "sigma2_paraphrase": para,
        "sigma2_model": mod,
        "share_decoding": share(dec),
        "share_paraphrase": share(para),
        "share_model": share(mod),
        "n_negative_paraphrase": int(sum(1 for x in components if x.sigma2_paraphrase < 0)),
        "n_negative_model": int(sum(1 for x in components if x.sigma2_model < 0)),
    }


def bootstrap_shares(by_paper: dict[str, Sequence[VarianceComponents]],
                     B: int = 2000, rng: np.random.Generator | None = None) -> dict:
    """Bootstrap the pooled shares by resampling **papers**, not values.

    Values within a paper are not independent: they come from one document, one
    set of prompts, and often one table. Resampling values would produce
    confidence intervals that are too narrow, and this is the single most common
    way a variance decomposition is made to look more precise than it is.
    """
    rng = np.random.default_rng() if rng is None else rng
    keys = list(by_paper.keys())
    if len(keys) < 3:
        raise ValueError("need at least 3 papers to bootstrap")

    draws = {"share_decoding": [], "share_paraphrase": [], "share_model": []}
    for _ in range(B):
        sample = rng.choice(len(keys), size=len(keys), replace=True)
        flat: list[VarianceComponents] = []
        for idx in sample:
            flat.extend(by_paper[keys[idx]])
        if not flat:
            continue
        pooled = pool(flat)
        for k in draws:
            draws[k].append(pooled[k])

    out = {}
    for k, v in draws.items():
        arr = np.asarray([x for x in v if np.isfinite(x)], dtype=float)
        if arr.size == 0:
            out[k] = {"mean": float("nan"), "ci95": [float("nan"), float("nan")]}
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        out[k] = {"mean": float(arr.mean()),
                  "ci95": [float(lo), float(hi)]}
    out["n_papers"] = len(keys)
    out["n_bootstrap"] = B
    return out


# --------------------------------------------------------------------------
# Decision rule
# --------------------------------------------------------------------------

def decide(share_paraphrase: float) -> dict:
    """The pre-registered decision rule from the pilot protocol.

    Frozen before the pilot runs. Changing it after seeing the number converts a
    pre-registered study into an exploratory one, and the paper would then have
    to say so.
    """
    if not np.isfinite(share_paraphrase):
        return {"band": "undefined", "action": "report the undefined share; do not guess"}

    if share_paraphrase >= 0.40:
        return {"band": ">=40%", "n_paraphrase": 10, "n_model": 3,
                "action": "Original design stands. Report a measured disagreement with "
                          "Zatuchin (2026) on extraction tasks.",
                "note": "publishable as a positive result about the paraphrase axis"}
    if share_paraphrase >= 0.20:
        return {"band": "20-39%", "n_paraphrase": 10, "n_model": 3,
                "action": "Keep paraphrase as one signal; reallocate a third of the "
                          "repeats to model diversity."}
    if share_paraphrase >= 0.10:
        return {"band": "10-19%", "n_paraphrase": 4, "n_model": 4,
                "action": "Paraphrase is a minor axis. Cut paraphrases to 4 and "
                          "reallocate to models. State explicitly that dispersion is "
                          "dominated by decoding noise."}
    return {"band": "<10%", "n_paraphrase": 0, "n_model": 5,
            "action": "Dispersion is measuring the wrong thing. Report this as the "
                      "pilot's primary finding and rebuild Signal A around model "
                      "diversity and token entropy.",
            "note": "publishable as a negative result; not a setback"}
