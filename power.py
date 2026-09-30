"""
Stage 0 — power analysis.

Answers the question the original proposal asserted rather than derived:
*how many records are needed to detect an effect of a given size?*

Two complementary routes are provided.

1. Analytic: Fisher z-transform power for a bivariate correlation. Fast, and
   the standard reference value.
2. Empirical: Monte-Carlo power under a *rank-correlated, non-normal* pair,
   which is closer to what per-record uncertainty and per-record error counts
   actually look like (bounded, skewed, many ties at zero).

The empirical route is the one that should be reported, because the analytic
route assumes bivariate normality that these variables do not satisfy.

Pure NumPy/SciPy. Independently runnable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

try:
    from scipy import stats
    _HAVE_SCIPY = True
except Exception:                                    # pragma: no cover
    _HAVE_SCIPY = False


# --------------------------------------------------------------------------
# Analytic power
# --------------------------------------------------------------------------

def n_required_fisher(r: float, power: float = 0.80, alpha: float = 0.05,
                      two_sided: bool = True) -> float:
    """Minimum n for detecting correlation r via the Fisher z transform.

    n ~= ((z_{1-alpha/2} + z_power) / atanh(r))^2 + 3
    """
    if not _HAVE_SCIPY:
        raise RuntimeError("scipy is required for n_required_fisher")
    if abs(r) >= 1.0:
        raise ValueError("|r| must be < 1")
    if abs(r) < 1e-9:
        return float("inf")
    z_a = stats.norm.ppf(1.0 - alpha / 2.0) if two_sided else stats.norm.ppf(1.0 - alpha)
    z_b = stats.norm.ppf(power)
    return float((z_a + z_b) ** 2 / np.arctanh(r) ** 2 + 3.0)


# --------------------------------------------------------------------------
# Empirical power
# --------------------------------------------------------------------------

@dataclass
class PowerResult:
    r_true: float
    n: int
    power: float
    alpha: float
    method: str
    reps: int


def _corr_pvalue(x: np.ndarray, y: np.ndarray, method: str) -> float:
    if _HAVE_SCIPY:
        if method == "pearson":
            return float(stats.pearsonr(x, y)[1])
        return float(stats.spearmanr(x, y)[1])
    # Fallback: t-test on Pearson r, normal approximation for Spearman is not
    # attempted. Reported as an approximation only.
    n = len(x)
    r = float(np.corrcoef(x, y)[0, 1])
    if abs(r) >= 1.0:
        return 0.0
    t = r * np.sqrt((n - 2) / (1 - r ** 2))
    return float(2.0 * (1.0 - _norm_cdf(abs(t))))


def _norm_cdf(z: float) -> float:
    """Standard normal CDF, used only by the no-SciPy fallback path.

    Uses `math.erf`, NOT `np.math.erf`. NumPy removed the `np.math` alias in
    NumPy 2.0, and the runtime here ships NumPy 2.3.5 -- so the old form raised
    AttributeError on exactly the path taken when SciPy is absent, which is the
    case in this environment. The bug would have surfaced on the first run of
    the power analysis and taken the whole Stage 0 report with it.
    """
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def simulate_pair(n: int, r: float, rng: np.random.Generator,
                  skew: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Generate a correlated (uncertainty, error-count) pair.

    With skew=True the error count is drawn as a Poisson whose rate increases
    with uncertainty, which mirrors the real data structure: most records have
    zero or one extraction error, a few have many.
    """
    z = rng.normal(size=n)
    eps = rng.normal(size=n)
    x_raw = r * z + np.sqrt(max(1.0 - r * r, 0.0)) * eps
    if not skew:
        return x_raw, z

    # Map x_raw to a bounded uncertainty in [0, 1] via its normal CDF, then to
    # a Poisson error count with rate increasing in uncertainty.
    u = 0.5 * (1.0 + _erf_vec(x_raw / np.sqrt(2.0)))
    rate = 0.15 + 2.0 * u
    y = rng.poisson(rate)
    return x_raw, y.astype(float)


def _erf_vec(x: np.ndarray) -> np.ndarray:
    if _HAVE_SCIPY:
        return stats.norm.cdf(x) * 2.0 - 1.0
    # Abramowitz & Stegun 7.1.26
    sign = np.sign(x)
    ax = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * ax)
    poly = ((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
            - 0.284496736) * t + 0.254829592
    return sign * (1.0 - poly * t * np.exp(-ax * ax))


def empirical_power(n: int, r: float, reps: int = 2000, alpha: float = 0.05,
                    method: str = "spearman", skew: bool = True,
                    seed: int = 0) -> PowerResult:
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(reps):
        x, y = simulate_pair(n, r, rng, skew=skew)
        if np.std(x) == 0 or np.std(y) == 0:
            continue
        if _corr_pvalue(x, y, method) < alpha:
            hits += 1
    return PowerResult(r_true=r, n=n, power=hits / reps, alpha=alpha,
                       method=method, reps=reps)


def min_n_for_power(r: float, target_power: float = 0.80, alpha: float = 0.05,
                    n_grid: Iterable[int] = (10, 15, 20, 25, 30, 40, 50, 60,
                                             75, 100, 125, 150, 200, 300),
                    reps: int = 2000, method: str = "spearman",
                    skew: bool = True, seed: int = 0) -> tuple[int | None, list[PowerResult]]:
    """Smallest n on the grid reaching target_power. Returns (n, all_results)."""
    results: list[PowerResult] = []
    hit: int | None = None
    for n in n_grid:
        res = empirical_power(n, r, reps=reps, alpha=alpha, method=method,
                              skew=skew, seed=seed)
        results.append(res)
        if hit is None and res.power >= target_power:
            hit = n
    return hit, results


def power_table(effects: Iterable[float] = (0.2, 0.3, 0.4, 0.5, 0.6),
                target_power: float = 0.80, alpha: float = 0.05,
                reps: int = 2000, seed: int = 0) -> dict:
    """The headline Stage 0 deliverable that sets the corpus target.

    Reports, for each candidate effect size, the analytic n and the empirical n
    required to reach `target_power`. The corpus target in Stage 1 is the
    maximum empirical n across the effect sizes the study commits to detecting.
    """
    out = {"target_power": target_power, "alpha": alpha, "effects": {}}
    for r in effects:
        analytic = None
        if _HAVE_SCIPY:
            analytic = n_required_fisher(r, power=target_power, alpha=alpha)
        empirical, curve = min_n_for_power(r, target_power=target_power,
                                           alpha=alpha, reps=reps, seed=seed)
        out["effects"][float(r)] = {
            "n_analytic_fisher": analytic,
            "n_empirical": empirical,
            "power_curve": [{"n": c.n, "power": c.power} for c in curve],
        }
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(power_table(reps=500), indent=2))
