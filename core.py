"""
Stage 0 — core simulation primitives.

Pure NumPy. No causal-discovery dependency here, so this module can be
validated independently of causal-learn.

Components
----------
1. DAG generators (Erdos-Renyi, scale-free) in a fixed topological order.
2. Structural equation model samplers (linear Gaussian, discrete).
3. Error-injection models with a latent per-cell ambiguity field, which is
   what creates a *known* ground-truth correlation between ambiguity and error.
4. Synthetic uncertainty signals derived from that latent field.

Terminology
-----------
*A* : adjacency matrix, shape (d, d). A[i, j] == 1 means i -> j.
*X* : observed data matrix, shape (n, d).
*amb* : latent ambiguity field, shape (n, d), in [0, 1]. Higher = more
        likely to be extracted wrongly. This is the ground truth that a real
        uncertainty metric is trying to recover.
*E* : realised error indicator, shape (n, d), in {0, 1}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


# --------------------------------------------------------------------------
# 1. DAG generation
# --------------------------------------------------------------------------

def topo_order(A: np.ndarray) -> list[int]:
    """Kahn's algorithm. Raises if the graph contains a cycle."""
    d = A.shape[0]
    indeg = A.sum(axis=0).astype(int).copy()
    ready = [j for j in range(d) if indeg[j] == 0]
    order: list[int] = []
    while ready:
        j = ready.pop(0)
        order.append(j)
        for k in np.where(A[j] == 1)[0]:
            indeg[k] -= 1
            if indeg[k] == 0:
                ready.append(k)
    if len(order) != d:
        raise ValueError("graph is not acyclic")
    return order


def random_dag(d: int, edge_prob: float = 0.3,
               rng: Optional[np.random.Generator] = None) -> np.ndarray:
    """Erdos-Renyi DAG: random topological order, then independent edges."""
    rng = np.random.default_rng() if rng is None else rng
    order = rng.permutation(d)
    A = np.zeros((d, d), dtype=int)
    for a in range(d):
        for b in range(a + 1, d):
            if rng.random() < edge_prob:
                A[order[a], order[b]] = 1
    return A


def scale_free_dag(d: int, m: int = 1,
                   rng: Optional[np.random.Generator] = None) -> np.ndarray:
    """Preferential-attachment DAG: new nodes attach to m earlier nodes with
    probability proportional to current degree. Produces hub structure, which
    is common in real scientific variable sets."""
    rng = np.random.default_rng() if rng is None else rng
    A = np.zeros((d, d), dtype=int)
    order = rng.permutation(d)
    degree = np.ones(d, dtype=float)
    for pos in range(1, d):
        j = order[pos]
        candidates = order[:pos]
        k = min(m, len(candidates))
        w = degree[candidates]
        w = w / w.sum()
        chosen = rng.choice(candidates, size=k, replace=False, p=w)
        for i in np.atleast_1d(chosen):
            A[i, j] = 1
        degree[candidates] += 1.0
    return A


def make_dag(d: int, topology: str = "er", edge_prob: float = 0.3,
             rng: Optional[np.random.Generator] = None) -> np.ndarray:
    if topology == "er":
        return random_dag(d, edge_prob=edge_prob, rng=rng)
    if topology == "sf":
        return scale_free_dag(d, m=1, rng=rng)
    raise ValueError(f"unknown topology: {topology!r}")


# --------------------------------------------------------------------------
# 2. Structural equation models
# --------------------------------------------------------------------------

def _draw_weights(A: np.ndarray, lo: float, hi: float,
                  rng: np.random.Generator) -> np.ndarray:
    d = A.shape[0]
    W = np.zeros((d, d))
    for i in range(d):
        for j in range(d):
            if A[i, j]:
                sign = -1.0 if rng.random() < 0.5 else 1.0
                W[i, j] = sign * rng.uniform(lo, hi)
    return W


def sample_linear_gaussian(A: np.ndarray, n: int,
                           rng: Optional[np.random.Generator] = None,
                           noise_scale: float = 1.0,
                           weight_lo: float = 0.5, weight_hi: float = 1.5
                           ) -> Tuple[np.ndarray, np.ndarray]:
    """Linear Gaussian SEM over the DAG. Returns (X, W)."""
    rng = np.random.default_rng() if rng is None else rng
    d = A.shape[0]
    W = _draw_weights(A, weight_lo, weight_hi, rng)
    order = topo_order(A)
    X = np.zeros((n, d))
    for j in order:
        parents = np.where(A[:, j] == 1)[0]
        if parents.size:
            X[:, j] = X[:, parents] @ W[parents, j]
        X[:, j] += rng.normal(0.0, noise_scale, size=n)
    return X, W


# --------------------------------------------------------------------------
# 2b. Standardized SEM (Kummerfeld, Williams & Ma, 2023)
# --------------------------------------------------------------------------
#
# Why this exists, and why the sampler above is NOT sufficient for Stage 0.
#
# `sample_linear_gaussian` draws random weights and fixes the noise variance to
# 1. That produces two well-documented artefacts:
#
#   1. Uncontrolled effect size. Kummerfeld et al. (2023) criticise the prior
#      simulation literature on exactly this point: "previous simulations have
#      not carefully controlled the causal effect sizes in their data generating
#      models ... without knowing the effect sizes of the edges we can not make
#      reliable inferences about the method's real world performance." An SHD
#      number reported without an effect-size convention is uninterpretable.
#
#   2. Varsortability. Reisach, Seiler & Weichwald (NeurIPS 2021, "Beware of the
#      Simulated DAG!") show that when marginal variance increases along the
#      causal order, continuous structure learners can appear to succeed merely
#      by sorting variances. Standard random-weight simulations are
#      varsortable, so they flatter the learner.
#
# The fix, following Kummerfeld et al.: set every edge weight to the same value
# and choose independent noise variances so that EVERY variable has marginal
# variance exactly 1. Then the edge weight equals the standardized effect size
# r, and varsortability is zero by construction.
#
# `varsortability` below verifies that second property rather than assuming it.

def standardized_noise_variances(A: np.ndarray, effect_size: float):
    """Return (W, omega) or (None, None) if the model is infeasible.

    X = eps @ inv(I - W), so Cov(X) = Amat.T @ diag(omega) @ Amat with
    Amat = inv(I - W). Requiring diag(Cov(X)) == 1 gives the linear system
    B @ omega = 1 with B[i, k] = Amat[k, i]^2. B has unit diagonal and is
    triangular in topological order, so it is solvable exactly.

    A DAG can be infeasible (some required omega <= 0) when a node has too many
    or too strong parents; Kummerfeld et al. handle this by resampling the DAG,
    and `make_feasible_dag` does the same.
    """
    d = A.shape[0]
    W = np.zeros((d, d))
    W[A == 1] = effect_size
    try:
        Amat = np.linalg.inv(np.eye(d) - W)
    except np.linalg.LinAlgError:
        return None, None
    B = Amat.T ** 2
    try:
        omega = np.linalg.solve(B, np.ones(d))
    except np.linalg.LinAlgError:
        return None, None
    if not np.all(np.isfinite(omega)) or np.any(omega <= 0.0):
        return None, None
    return W, omega


def make_feasible_dag(d: int, topology: str = "er", edge_prob: float = 0.3,
                      effect_size: float = 0.3,
                      rng: Optional[np.random.Generator] = None,
                      max_attempts: int = 60
                      ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resample the DAG until a positive-definite noise assignment exists."""
    rng = np.random.default_rng() if rng is None else rng
    for _ in range(max_attempts):
        A = make_dag(d, topology=topology, edge_prob=edge_prob, rng=rng)
        W, omega = standardized_noise_variances(A, effect_size)
        if W is not None:
            return A, W, omega
    raise ValueError(
        f"no feasible noise assignment found in {max_attempts} attempts "
        f"(d={d}, topology={topology}, edge_prob={edge_prob}, "
        f"effect_size={effect_size}). Lower edge_prob or effect_size.")


def sample_standardized_gaussian(A: np.ndarray, n: int, effect_size: float = 0.3,
                                 rng: Optional[np.random.Generator] = None
                                 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw data from the standardized SEM. Returns (X, W, omega).

    Every variable has marginal variance 1 in the population, so the edge weight
    equals the standardized effect size and varsortability is eliminated.
    """
    rng = np.random.default_rng() if rng is None else rng
    W, omega = standardized_noise_variances(A, effect_size)
    if W is None:
        raise ValueError("infeasible model; use make_feasible_dag to resample")
    d = A.shape[0]
    order = topo_order(A)
    eps = rng.normal(0.0, np.sqrt(omega), size=(n, d))
    X = np.zeros((n, d))
    for j in order:
        parents = np.where(A[:, j] == 1)[0]
        if parents.size:
            X[:, j] = X[:, parents] @ W[parents, j]
        X[:, j] += eps[:, j]
    return X, W, omega


def population_variance(A: np.ndarray, W: np.ndarray, omega: np.ndarray) -> np.ndarray:
    """Exact marginal variances implied by the model. Should be all ones."""
    Amat = np.linalg.inv(np.eye(A.shape[0]) - W)
    cov = Amat.T @ np.diag(omega) @ Amat
    return np.diag(cov)


def varsortability(X: np.ndarray, A: np.ndarray, tol: float = 1e-9) -> float:
    """Reisach et al. (2021) VAR-sortability.

    Fraction of variable pairs whose marginal-variance ordering agrees with the
    causal ordering. 0.5 is uninformative; near 1.0 means a continuous learner
    could appear to recover the causal order by sorting variances alone. Under
    the standardized sampler this must be close to 0.5 (ties count as half),
    which the self test asserts.
    """
    order = topo_order(A)
    var = X.var(axis=0)
    agree = 0.0
    total = 0
    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            i, j = order[a], order[b]          # i causally precedes j
            total += 1
            if var[i] < var[j] - tol:
                agree += 1.0
            elif abs(var[i] - var[j]) <= tol:
                agree += 0.5
    return agree / total if total else float("nan")


def sample_discrete(A: np.ndarray, n: int, n_levels: int = 3,
                    rng: Optional[np.random.Generator] = None
                    ) -> np.ndarray:
    """Discrete SEM with a random conditional probability table per node.
    Returns an integer array of shape (n, d) with values in [0, n_levels)."""
    rng = np.random.default_rng() if rng is None else rng
    d = A.shape[0]
    order = topo_order(A)
    X = np.zeros((n, d), dtype=int)
    for j in order:
        parents = np.where(A[:, j] == 1)[0]
        if parents.size == 0:
            p = rng.dirichlet(np.ones(n_levels))
            X[:, j] = rng.choice(n_levels, size=n, p=p)
            continue
        table = rng.dirichlet(np.ones(n_levels), size=(n_levels,) * parents.size)
        idx = tuple(X[:, p] for p in parents)
        probs = table[idx]                       # shape (n, n_levels)
        cum = np.cumsum(probs, axis=1)
        u = rng.random((n, 1))
        X[:, j] = np.minimum((u > cum).sum(axis=1), n_levels - 1)
    return X


# --------------------------------------------------------------------------
# 3. Error injection
# --------------------------------------------------------------------------

@dataclass
class ErrorDesign:
    """Controls how extraction errors are injected.

    base_rate     : marginal probability that any given cell is corrupted through the
                    ambiguity-linked channel.
    severity      : numeric errors are multiplicative, X -> X * (1 + N(0, sev)).
    ambiguity_a/b : Beta parameters for the latent ambiguity field. The default
                    (2, 5) concentrates ambiguity mass below its mean, leaving a
                    right tail of genuinely ambiguous values, which is what real
                    extraction corpora look like.
    correlated    : if False, errors are independent of ambiguity. This is the
                    NULL regime and is used to verify that the pipeline reports
                    no relationship when none exists.
    confident_wrong_rate
                  : probability of an error occurring INDEPENDENTLY of the ambiguity
                    field. This models "confident mode collapse" (Hamidieh et al.,
                    ICLR 2026): the extractor commits to a wrong value, all N
                    paraphrased samples agree, and dispersion is flat zero at exactly
                    the errors that matter. At 0.0 the attainable ceiling is high; as
                    it rises the ceiling falls, and the simulation quantifies by how
                    much. This single parameter is what lets Stage 0 test the
                    proposal's core measurement assumption rather than assert it.
    """
    base_rate: float = 0.10
    severity: float = 0.25
    ambiguity_a: float = 2.0
    ambiguity_b: float = 5.0
    correlated: bool = True
    confident_wrong_rate: float = 0.0
    numeric: bool = True
    n_levels: int = 3


def draw_ambiguity(shape: Tuple[int, int], design: ErrorDesign,
                   rng: np.random.Generator) -> np.ndarray:
    return rng.beta(design.ambiguity_a, design.ambiguity_b, size=shape)


def inject_errors(X: np.ndarray, design: ErrorDesign,
                  rng: Optional[np.random.Generator] = None
                  ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X_corrupted, E, amb).

    When design.correlated is True the per-cell error probability is
    proportional to the latent ambiguity field, so a correctly specified
    uncertainty metric *should* recover the error pattern. The maximum
    achievable recovery is what Stage 0 quantifies as the attainable ceiling.
    """
    rng = np.random.default_rng() if rng is None else rng
    n, d = X.shape
    amb = draw_ambiguity((n, d), design, rng)

    if design.correlated:
        scale = amb / max(amb.mean(), 1e-12)
    else:
        scale = np.ones_like(amb)
    p = np.clip(design.base_rate * scale, 0.0, 1.0)
    E = (rng.random((n, d)) < p).astype(int)

    # Confident mode collapse. Errors drawn independently of ambiguity are the
    # ones a dispersion-based metric structurally cannot see: the metric's only
    # signal is that ambiguity spreads the sampled answers, and here there is no
    # ambiguity to spread them.
    if design.confident_wrong_rate > 0.0:
        E_conf = (rng.random((n, d)) < design.confident_wrong_rate).astype(int)
        E = np.maximum(E, E_conf)

    Xc = X.astype(float).copy()
    if design.numeric:
        delta = rng.normal(0.0, design.severity, size=(n, d))
        Xc = np.where(E == 1, Xc * (1.0 + delta), Xc)
    else:
        k = design.n_levels
        for i, j in zip(*np.where(E == 1)):
            cur = int(X[i, j])
            choice = rng.integers(0, k - 1)
            if choice >= cur:
                choice += 1
            Xc[i, j] = choice

    return Xc, E, amb


def correct_records(Xc: np.ndarray, X_clean: np.ndarray,
                    rows) -> np.ndarray:
    """Return a copy of Xc with the given rows restored to their clean values."""
    out = Xc.copy()
    rows = np.atleast_1d(rows)
    out[rows, :] = X_clean[rows, :]
    return out


# --------------------------------------------------------------------------
# 4. Synthetic uncertainty signals
# --------------------------------------------------------------------------

def uncertainty_from_ambiguity(amb: np.ndarray, rng: np.random.Generator,
                               noise: float = 0.15, per_record: bool = True
                               ) -> np.ndarray:
    """A *synthetic but imperfect* uncertainty signal.

    A real paraphrase-self-consistency metric is a noisy function of the true
    ambiguity; this models exactly that, so that the attainable ceiling is
    measured for a realistic, not an oracle, instrument. Set noise=0 for the
    oracle ceiling.
    """
    u_cell = amb + rng.normal(0.0, noise, size=amb.shape)
    u_cell = np.clip(u_cell, 0.0, 1.0)
    if per_record:
        return u_cell.mean(axis=1)
    return u_cell


def ceiling_correlation(amb: np.ndarray, E: np.ndarray) -> float:
    """Oracle attainable ceiling: correlation between the TRUE latent ambiguity
    and the realised per-record error count. No metric can beat this."""
    return float(np.corrcoef(amb.mean(axis=1), E.sum(axis=1))[0, 1])


def mode_collapse_fraction(amb: np.ndarray, E: np.ndarray,
                           low_quantile: float = 0.5) -> float:
    """Observable analogue of RQ8, computed from ground truth.

    Fraction of erroneous cells whose ambiguity lies below the `low_quantile` of
    the ambiguity distribution — that is, errors the extractor made while the
    source text was unambiguous and paraphrasing therefore could not reveal
    anything. A dispersion-based metric cannot flag these by construction.

    Stage 5 test 4 estimates this quantity on real data against the gold
    standard. Here it is computed from ground truth, so the simulation can
    establish which values are reachable and what they cost the downstream
    uncertainty-impact correlation. That mapping is what turns RQ8 from a
    caveat into a calibrated prediction.
    """
    err = E == 1
    if err.sum() == 0:
        return float("nan")
    threshold = float(np.quantile(amb, low_quantile))
    return float((amb[err] <= threshold).mean())
