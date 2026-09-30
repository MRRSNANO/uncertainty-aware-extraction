"""
Stage 0 — causal discovery wrappers and structure-stability metrics.

Design note
-----------
Structural Hamming Distance is taken from causal-learn's own ``SHD`` class rather
than reimplemented. A hand-rolled SHD would silently depend on an endpoint-mark
convention that is easy to get backwards, and a wrong SHD invalidates every
number downstream. If the official API is unavailable the code raises rather
than guessing.

Every discovery call runs with stdout suppressed, because causal-learn is
verbose and the Stage 0 grid issues tens of thousands of calls.
"""

from __future__ import annotations

import contextlib
import io
import warnings
from typing import Callable, Iterable, Sequence

import numpy as np


# --------------------------------------------------------------------------
# Quiet execution
# --------------------------------------------------------------------------

@contextlib.contextmanager
def _quiet():
    buf = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            yield


# --------------------------------------------------------------------------
# Discovery wrappers
# --------------------------------------------------------------------------

def run_pc(X: np.ndarray, alpha: float = 0.05, discrete: bool = False):
    """PC algorithm. Returns the causal-learn graph object.

    The keyword set is tried from richest to simplest so that the code survives
    causal-learn version drift instead of dying on an unexpected kwarg.
    """
    from causallearn.search.ConstraintBased.PC import pc

    indep = "chisq" if discrete else "fisherz"
    attempts = (
        dict(alpha=alpha, indep_test=indep, stable=True, show_progress=False),
        dict(alpha=alpha, indep_test=indep, stable=True),
        dict(alpha=alpha, indep_test=indep),
        dict(alpha=alpha),
    )
    last: Exception | None = None
    for kw in attempts:
        try:
            with _quiet():
                return pc(np.asarray(X, dtype=float), **kw)
        except TypeError as exc:                     # unexpected kwarg
            last = exc
            continue
    raise RuntimeError(f"PC could not be invoked: {last}")


def run_ges(X: np.ndarray, score: str = "local_score_BIC"):
    """GES algorithm. Returns the causal-learn graph object."""
    from causallearn.search.ScoreBased.GES import ges

    with _quiet():
        record = ges(np.asarray(X, dtype=float), score_func=score)
    return record["G"]


def make_discoverer(algorithm: str = "pc", alpha: float = 0.05,
                    discrete: bool = False) -> Callable[[np.ndarray], object]:
    """Return a callable X -> graph object, for use in bootstrap loops."""
    if algorithm == "pc":
        return lambda X: run_pc(X, alpha=alpha, discrete=discrete)
    if algorithm == "ges":
        return lambda X: run_ges(X)
    raise ValueError(f"unknown algorithm: {algorithm!r}")


def graph_of(result):
    """Normalise: accept either a causal-learn CausalGraph or a bare graph."""
    return getattr(result, "G", result)


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

def shd(result_a, result_b) -> int:
    """Structural Hamming Distance between two discovery results.

    Uses causal-learn's official implementation. Raises if it is unavailable,
    because a substituted value here would be silently wrong.
    """
    from causallearn.graph.SHD import SHD

    with _quiet():
        return int(SHD(graph_of(result_a), graph_of(result_b)).get_shd())


def skeleton_edges(result) -> set[tuple[int, int]]:
    """Undirected edges as normalised (i, j) pairs with i < j.

    Used for edge-stability counting, where orientation is deliberately ignored:
    the question is whether the pipeline recovers the *association*, not whether
    it orients it, which PC cannot be trusted to do at these sample sizes.
    """
    g = graph_of(result)
    nodes = list(g.get_nodes())
    index = {n: k for k, n in enumerate(nodes)}
    edges: set[tuple[int, int]] = set()
    for e in g.get_graph_edges():
        i = index[e.get_node1()]
        j = index[e.get_node2()]
        if i > j:
            i, j = j, i
        edges.add((i, j))
    return edges


def edge_stability(X: np.ndarray, discover: Callable, B: int = 200,
                   weights: np.ndarray | None = None,
                   rng: np.random.Generator | None = None
                   ) -> dict[tuple[int, int], float]:
    """Bootstrap frequency of each undirected edge.

    weights=None gives the uniform-weight baseline (baseline B3 in the design);
    passing uncertainty-derived weights gives the treatment condition. The
    difference between the two is the paper's central empirical question.
    """
    rng = np.random.default_rng() if rng is None else rng
    n = X.shape[0]

    if weights is None:
        p = None
    else:
        w = np.asarray(weights, dtype=float)
        if w.shape[0] != n:
            raise ValueError("weights must have one entry per record")
        total = w.sum()
        if total <= 0:
            raise ValueError("weights must not sum to zero")
        p = w / total

    counts: dict[tuple[int, int], int] = {}
    for _ in range(B):
        idx = rng.integers(0, n, size=n) if p is None else rng.choice(n, size=n, p=p)
        try:
            edges = skeleton_edges(discover(X[idx]))
        except Exception:
            # A degenerate resample (e.g. a constant column) is skipped rather
            # than allowed to abort the whole bootstrap.
            continue
        for key in edges:
            counts[key] = counts.get(key, 0) + 1

    return {k: v / B for k, v in counts.items()}


def stability_series(stability: dict[tuple[int, int], float],
                     all_edges: Iterable[tuple[int, int]]) -> np.ndarray:
    """Stability values aligned to a fixed edge list; absent edges score 0."""
    return np.array([stability.get(e, 0.0) for e in all_edges], dtype=float)


def per_record_uncertainty_vs_edge_stability(
        uncertainty: np.ndarray,
        X_corrupted: np.ndarray,
        discover: Callable,
        B: int = 100,
        rng: np.random.Generator | None = None) -> dict:
    """RQ5: is per-record uncertainty associated with per-edge bootstrap stability?

    Operationalised by splitting records into an uncertain half and a certain
    half, computing edge stability separately in each, and correlating the two
    stability vectors across the union of edges. This is a more direct test than
    correlating a per-record quantity with a per-edge quantity, which has no
    natural pairing.
    """
    rng = np.random.default_rng() if rng is None else rng
    median = float(np.median(uncertainty))
    high = np.where(uncertainty > median)[0]
    low = np.where(uncertainty <= median)[0]
    if high.size < 5 or low.size < 5:
        return {"r": float("nan"), "n_edges": 0, "note": "insufficient split"}

    stab_high = edge_stability(X_corrupted[high], discover, B=B, rng=rng)
    stab_low = edge_stability(X_corrupted[low], discover, B=B, rng=rng)

    edges = sorted(set(stab_high) | set(stab_low))
    if len(edges) < 3:
        return {"r": float("nan"), "n_edges": len(edges), "note": "too few edges"}

    a = stability_series(stab_high, edges)
    b = stability_series(stab_low, edges)
    if np.std(a) == 0 or np.std(b) == 0:
        return {"r": float("nan"), "n_edges": len(edges), "note": "no variance"}

    r = float(np.corrcoef(a, b)[0, 1])
    return {"r": r, "n_edges": len(edges),
            "mean_stability_high_uncertainty": float(a.mean()),
            "mean_stability_low_uncertainty": float(b.mean())}
