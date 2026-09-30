"""
Stage 2 — uncertainty quantification maths.

Pure NumPy. No model access, no API, no I/O. Everything here is testable from
first principles, which matters because the entire downstream analysis rests on
these numbers and they cannot be sanity-checked by looking at them.

Implements the three signals and the calibration described in
`protocol/prompts_and_uncertainty.md`:

    Signal A  paraphrase self-consistency   (aleatoric)
    Signal B  token-level entropy
    Signal C  cross-model epistemic term, in the form of Hamidieh et al. (2026)

Two deliberate design choices are worth stating, because they are the kind of
thing that gets quietly reversed under pressure:

1. **Outlier exclusions are reported, never silent.** A value whose N attempts
   scatter widely enough to trigger exclusions is a value the source text does
   not pin down. That is the paper's own best evidence and must not be hidden.
2. **Negative variance estimates stay negative.** A negative component estimate
   is the standard signal that a component is indistinguishable from noise at
   this sample size. Clipping it to zero would invent structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


# --------------------------------------------------------------------------
# Signal A — paraphrase self-consistency
# --------------------------------------------------------------------------

def numeric_dispersion(values: Sequence[float], mad_k: float = 3.0
                       ) -> tuple[float, float, int]:
    """Coefficient of variation after 3 x MAD outlier exclusion.

    Returns (cv, exclusion_rate, n_valid).

    CV is `sd / |mean|`. It is undefined when the mean is at or near zero, and
    the function returns NaN rather than a huge number, because a huge CV on a
    near-zero mean is an artefact of the denominator, not evidence of
    disagreement. Those values are reported separately and excluded from the
    composite, with the count reported.

    MAD is scaled by 1.4826 so that it estimates the standard deviation for
    Gaussian data; without that factor the 3 x MAD rule is far stricter than
    "three sigma" and would exclude outliers aggressively.
    """
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    n_total = arr.size
    if n_total == 0:
        return float("nan"), 0.0, 0
    if n_total == 1:
        return 0.0, 0.0, 1

    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median))) * 1.4826
    if mad <= 0.0:
        kept = arr                       # all identical, or too few distinct values
    else:
        kept = arr[np.abs(arr - median) <= mad_k * mad]

    n_valid = int(kept.size)
    exclusion_rate = 1.0 - n_valid / n_total
    if n_valid < 2:
        return float("nan"), exclusion_rate, n_valid

    mean = float(np.mean(kept))
    if abs(mean) < 1e-12:
        return float("nan"), exclusion_rate, n_valid
    cv = float(np.std(kept, ddof=1) / abs(mean))
    return cv, exclusion_rate, n_valid


def categorical_disagreement(labels: Sequence[str | None],
                             n_levels: int | None = None
                             ) -> tuple[float, float, int]:
    """1 - majority proportion, normalised so that different arities compare.

    Raw disagreement has a maximum that depends on the number of levels: a
    3-level variable can never exceed 2/3, a 5-level one 4/5. The normalised
    form `(1 - p_majority) / (1 - 1/k)` maps both onto [0, 1] so that a
    categorical variable and a numeric one can be combined.

    Returns (disagreement_normalised, raw_disagreement, n_valid).
    """
    vals = [v for v in labels if v is not None]
    n = len(vals)
    if n == 0:
        return float("nan"), float("nan"), 0
    counts: dict[str, int] = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    p_majority = max(counts.values()) / n
    raw = 1.0 - p_majority

    k = n_levels if n_levels is not None else len(counts)
    if k is None or k < 2:
        return 0.0, raw, n
    denom = 1.0 - 1.0 / k
    if denom <= 0:
        return 0.0, raw, n
    return float(min(raw / denom, 1.0)), float(raw), n


# --------------------------------------------------------------------------
# Signal B — token-level entropy
# --------------------------------------------------------------------------

def normalised_token_entropy(entropies: Sequence[float],
                             token_counts: Sequence[int]) -> float:
    """Mean per-token entropy over the extracted span.

    Raw entropy grows with span length, so an unnormalised value conflates
    "long answer" with "uncertain answer". Dividing by the token count removes
    that, at the cost of assuming entropy is roughly uniform across the span --
    an assumption worth stating in the paper rather than hiding.
    """
    e = np.asarray(entropies, dtype=float)
    n = np.asarray(token_counts, dtype=float)
    mask = np.isfinite(e) & np.isfinite(n) & (n > 0)
    if not mask.any():
        return float("nan")
    return float(np.sum(e[mask]) / np.sum(n[mask]))


# --------------------------------------------------------------------------
# Signal C — cross-model epistemic term
# --------------------------------------------------------------------------

def ensemble_epistemic_term(intra_model_similarity: float,
                            inter_model_similarity: float) -> float:
    """EU: how much better a model agrees with itself than with its peers.

    This is the term Hamidieh et al. (2026) introduce. **The direction matters
    and is easy to get backwards.** EU must be LARGE when intra-model similarity
    is high and inter-model similarity is low, because that is the signature of a
    model that is confidently and consistently wrong while its peers disagree.
    Their abstract reports that "cross-model semantic disagreement is higher on
    incorrect answers precisely when AU is low", i.e. inter-model *similarity*
    falls on exactly those confident failures where dispersion is flat.

    Writing this as `inter - intra` would make the term fire on well-agreed
    values and stay silent on mode collapse — the precise inverse of its purpose,
    and worse than not having it at all. The self test pins the direction.
    """
    return float(intra_model_similarity - inter_model_similarity)


def sequence_similarity(a: str, b: str, metric: str = "token_f1") -> float:
    """Similarity between two extracted strings, used for both the inter- and
    intra-model terms so the two are on the same scale."""
    if metric != "token_f1":
        raise ValueError(f"unknown similarity metric: {metric!r}")
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    precision = overlap / len(ta)
    recall = overlap / len(tb)
    if precision + recall == 0:
        return 0.0
    return float(2 * precision * recall / (precision + recall))


def _tokens(s: str | None) -> set[str]:
    if s is None:
        return set()
    return {t for t in str(s).lower().replace(",", " ").split() if t}


# --------------------------------------------------------------------------
# Composite
# --------------------------------------------------------------------------

@dataclass
class CompositeSpec:
    """How the three signals are combined.

    **The signals do not share a scale, so they must be normalised before they
    are combined.** CV is unbounded above — a value whose attempts disagree by
    their own magnitude has CV > 1. Token entropy is in nats and can exceed 1.
    The epistemic term lives in [-1, 1]. Averaging them raw means the signal
    that happens to have the widest range dominates the composite, and which
    signal that is would vary by domain and by variable type rather than being a
    modelling choice. `SignalNormaliser` is what puts them on a common footing;
    this spec only says how much each contributes *after* that.
    """
    w_self_consistency: float = 1.0
    w_token_entropy: float = 1.0
    w_epistemic: float = 1.0
    min_signals: int = 1


class SignalNormaliser:
    """Map each raw signal onto a common [0, 1] scale by empirical percentile.

    Percentile rather than min-max or z-score because these signals are heavily
    skewed and long-tailed: many values have dispersion exactly zero, and a
    single large CV would compress everything else to near zero under min-max.
    The percentile transform makes no distributional assumption and is bounded
    by construction.

    Fitted on the calibration set and applied to everything. Values outside the
    fitted range saturate at 0 or 1 rather than extrapolating, which is the
    honest behaviour: a dispersion larger than anything the calibration set
    contained is evidence the calibration does not cover this value, and saying
    "maximally uncertain" is safer than inventing a percentile.

    NaN in gives NaN out, and the composite then renormalises over whatever
    signals remain. A signal that is unavailable must never be replaced by 0.5,
    which would read as a confident middle estimate.
    """

    KEYS = ("self_consistency", "token_entropy", "epistemic")

    def __init__(self) -> None:
        self._sorted: dict[str, np.ndarray] = {}
        self._n: dict[str, int] = {}

    def fit(self, raw: dict[str, Sequence[float]]) -> "SignalNormaliser":
        for key in self.KEYS:
            vals = np.asarray([v for v in raw.get(key, [])
                               if v is not None and np.isfinite(v)], dtype=float)
            if vals.size == 0:
                continue
            # A constant signal carries no discriminative information, and
            # mapping it through a percentile would send EVERY value to 1.0 --
            # reading as maximum uncertainty everywhere, which is worse than
            # useless. It is dropped instead, so the composite renormalises over
            # the signals that actually vary, and `fitted_signals` shows which.
            if float(np.std(vals)) <= 1e-12:
                continue
            self._sorted[key] = np.sort(vals)
            self._n[key] = int(vals.size)
        return self

    def transform_one(self, key: str, value: float) -> float:
        if value is None or not np.isfinite(value):
            return float("nan")
        ref = self._sorted.get(key)
        if ref is None or self._n.get(key, 0) == 0:
            return float("nan")
        # Proportion of calibration values at or below this one.
        return float(np.searchsorted(ref, value, side="right") / self._n[key])

    def transform(self, raw: dict[str, float]) -> dict[str, float]:
        return {k: self.transform_one(k, raw.get(k, float("nan")))
                for k in self.KEYS}

    @property
    def fitted_signals(self) -> list[str]:
        return sorted(self._sorted)


def composite_uncertainty(signals: dict[str, float | None],
                          spec: CompositeSpec | None = None) -> float:
    """Weighted mean of the available signals.

    **Expects normalised signals.** Passing raw CV, raw entropy and a raw
    epistemic term here would let whichever has the widest range dominate; use
    `SignalNormaliser` first. The function does not enforce this, because a
    single-signal call is legitimate and needs no normalisation -- U equals that
    signal by construction.

    Signals that are None or NaN are dropped and the weights renormalised, and
    the count of contributing signals is available from
    `composite_uncertainty_detail` so that a value resting on one signal is never
    presented as though it rested on three.
    """
    return composite_uncertainty_detail(signals, spec)["value"]


def composite_uncertainty_detail(signals: dict[str, float | None],
                                 spec: CompositeSpec | None = None) -> dict:
    spec = spec or CompositeSpec()
    weights = {
        "self_consistency": spec.w_self_consistency,
        "token_entropy": spec.w_token_entropy,
        "epistemic": spec.w_epistemic,
    }
    num = 0.0
    den = 0.0
    used: list[str] = []
    for key, w in weights.items():
        v = signals.get(key)
        if v is None or not np.isfinite(v) or w <= 0:
            continue
        num += w * float(v)
        den += w
        used.append(key)
    if len(used) < spec.min_signals or den <= 0:
        return {"value": float("nan"), "n_signals": len(used), "signals": used}
    return {"value": float(num / den), "n_signals": len(used), "signals": used}


# --------------------------------------------------------------------------
# Split conformal calibration
# --------------------------------------------------------------------------

@dataclass
class ConformalResult:
    threshold: float
    alpha: float
    n_calibration: int
    empirical_coverage: float
    nominal_coverage: float
    miscalibrated: bool


class SplitConformalCalibrator:
    """Turn a heuristic uncertainty score into a risk-controlled decision rule.

    This follows Kim et al. (2025, AAAI Symposium) and Xu & Lu (2025), both of
    which outperform self-consistency-based uncertainty quantification by adding
    a conformal step. The reason to prefer it over isotonic regression is the
    finite-sample coverage guarantee: the interval is guaranteed to cover at the
    nominal rate on exchangeable data, whatever the score's distribution.

    The guarantee holds on the calibration distribution and only there. That
    caveat belongs in the paper, not in a footnote, because the empirical study
    then applies the rule to a different corpus.
    """

    def __init__(self, alpha: float = 0.10):
        if not 0.0 < alpha < 1.0:
            raise ValueError("alpha must be in (0, 1)")
        self.alpha = alpha
        self._scores: np.ndarray | None = None
        self._threshold: float | None = None

    def fit(self, scores: Sequence[float], errors: Sequence[float]) -> "SplitConformalCalibrator":
        """Fit on the calibration split only.

        `scores` are uncertainty scores; `errors` are the corresponding observed
        extraction errors, used here as the nonconformity measure. Scores with
        NaN are dropped, and the dropped count is the caller's responsibility to
        report.
        """
        s = np.asarray(scores, dtype=float)
        e = np.asarray(errors, dtype=float)
        mask = np.isfinite(s) & np.isfinite(e)
        s = s[mask]
        if s.size < 20:
            raise ValueError(
                f"conformal calibration needs at least 20 usable points, got {s.size}")
        self._scores = np.sort(s)
        n = self._scores.size
        # Finite-sample correction: the ceil((n+1)(1-alpha))/n empirical quantile.
        k = int(np.ceil((n + 1) * (1.0 - self.alpha)))
        k = min(max(k, 1), n)
        self._threshold = float(self._scores[k - 1])
        return self

    @property
    def threshold(self) -> float:
        if self._threshold is None:
            raise RuntimeError("calibrator has not been fitted")
        return self._threshold

    def is_uncertain(self, score: float) -> bool:
        return bool(np.isfinite(score) and score >= self.threshold)

    def evaluate(self, scores: Sequence[float], errors: Sequence[float]
                 ) -> ConformalResult:
        """Report empirical coverage on a held-out split.

        Coverage is the share of *erroneous* values that the rule flags. If the
        rule is well behaved this should be at least the nominal rate; falling
        materially below it means the score is not transporting to the new data,
        which is a finding and must be reported as one.
        """
        s = np.asarray(scores, dtype=float)
        e = np.asarray(errors, dtype=float)
        mask = np.isfinite(s) & np.isfinite(e)
        s, e = s[mask], e[mask]
        if s.size == 0:
            raise ValueError("no usable points to evaluate")
        flagged = s >= self.threshold
        erroneous = e > 0
        if erroneous.sum() == 0:
            coverage = float("nan")
        else:
            coverage = float((flagged & erroneous).sum() / erroneous.sum())
        nominal = 1.0 - self.alpha
        return ConformalResult(
            threshold=self.threshold,
            alpha=self.alpha,
            n_calibration=int(self._scores.size) if self._scores is not None else 0,
            empirical_coverage=coverage,
            nominal_coverage=nominal,
            miscalibrated=bool(np.isfinite(coverage) and coverage < nominal - 0.05),
        )


# --------------------------------------------------------------------------
# Isotonic comparison
# --------------------------------------------------------------------------

def isotonic_calibration(scores: Sequence[float], errors: Sequence[float]
                         ) -> tuple[np.ndarray, np.ndarray]:
    """Pool-adjacent-violators isotonic fit, retained as a comparison to the
    conformal rule. Returns (x_knots, y_fitted) on the sorted score axis.

    Implemented directly rather than pulled from scikit-learn so that the
    extraction package has no dependency beyond NumPy.
    """
    s = np.asarray(scores, dtype=float)
    e = np.asarray(errors, dtype=float)
    mask = np.isfinite(s) & np.isfinite(e)
    s, e = s[mask], e[mask]
    if s.size == 0:
        raise ValueError("no usable points")

    order = np.argsort(s, kind="mergesort")
    xs = s[order]
    ys = e[order].astype(float)

    # Pool adjacent violators.
    weights = np.ones_like(ys)
    values = ys.copy()
    i = 0
    blocks: list[list[float]] = []          # [sum_wy, sum_w, start_idx, end_idx]
    for j in range(ys.size):
        blocks.append([values[j], 1.0, j, j])
        while len(blocks) >= 2 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            b2 = blocks.pop()
            b1 = blocks.pop()
            blocks.append([b1[0] + b2[0], b1[1] + b2[1], b1[2], b2[3]])

    fitted = np.empty_like(ys)
    for swy, sw, lo, hi in blocks:
        fitted[lo:hi + 1] = swy / sw
    return xs, fitted
