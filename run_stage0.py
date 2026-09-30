"""
Stage 0 — simulation driver.

Runs the design grid, one JSON record per (cell, replication), to a JSONL file so
that a long run is resumable and every number in the paper is traceable to a row.

Grid factors
------------
n            sample size
d            number of variables
topology     'er' (Erdos-Renyi) | 'sf' (scale-free)
edge_prob    graph density
base_rate    marginal extraction-error rate
severity     numeric error magnitude
correlated   whether error probability tracks latent ambiguity (True)
             or is independent of it (False, the null regime)
confident_wrong
             probability of an error drawn independently of ambiguity, modelling
             "confident mode collapse" (Hamidieh et al., ICLR 2026). This is the
             factor that tests whether the proposal's central measurement
             assumption survives the failure mode the literature identifies.
rep          replication index

The p = 0 rows and the correlated = False rows are the study's anchors: at p = 0
no impact may be detected, and with correlated = False no uncertainty-impact
relationship may be detected. If the pipeline reports effects in either regime,
the pipeline is broken and no empirical result from it can be believed.

The confident_wrong axis is the study's stress test. At confident_wrong = 0 the
attainable ceiling should be high. As it rises, the ceiling must fall, because a
share of the errors becomes invisible to a dispersion-based metric by
construction. The size of that fall is the calibrated cost of mode collapse, and
it is a headline Stage 0 result.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

if __package__:
    from .core import (ErrorDesign, ceiling_correlation, correct_records,
                       inject_errors, make_feasible_dag, mode_collapse_fraction,
                       sample_standardized_gaussian, uncertainty_from_ambiguity,
                       varsortability)
    from .discovery import make_discoverer, shd
    from .impact import (_spearman, high_low_contrast, impact_vs_uncertainty,
                         per_record_impact, placebo_test)
else:                                                # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from core import (ErrorDesign, ceiling_correlation, correct_records,
                      inject_errors, make_feasible_dag, mode_collapse_fraction,
                      sample_standardized_gaussian, uncertainty_from_ambiguity,
                      varsortability)
    from discovery import make_discoverer, shd
    from impact import (_spearman, high_low_contrast, impact_vs_uncertainty,
                        per_record_impact, placebo_test)


QUICK_GRID = dict(
    n=[20, 50, 100],
    d=[5, 8],
    topology=["er"],
    edge_prob=[0.3],
    base_rate=[0.0, 0.10, 0.30],
    severity=[0.25],
    correlated=[True, False],
    confident_wrong=[0.0, 0.10],
    effect_size=[0.3],
)

FULL_GRID = dict(
    n=[20, 50, 100, 200, 500],
    d=[5, 6, 8],
    topology=["er", "sf"],
    edge_prob=[0.2, 0.4],
    base_rate=[0.0, 0.05, 0.10, 0.20, 0.30],
    severity=[0.10, 0.25, 0.50],
    correlated=[True, False],
    confident_wrong=[0.0, 0.05, 0.10, 0.20],
    effect_size=[0.1, 0.3, 0.5],
)


def cells(grid: dict, seed: int = 0):
    keys = ["n", "d", "topology", "edge_prob", "base_rate", "severity",
            "correlated", "confident_wrong", "effect_size"]
    for values in itertools.product(*(grid[k] for k in keys)):
        cell = dict(zip(keys, values))
        cell["seed"] = seed
        yield cell


def run_cell(cell: dict, rep: int, algorithm: str, alpha: float,
             max_records: int, bootstrap_B: int, uncertainty_noise: float,
             run_placebo: bool) -> dict:
    rng = np.random.default_rng(
        abs(hash((cell["seed"], rep, cell["n"], cell["d"],
                  cell["base_rate"], cell["severity"], int(cell["correlated"]),
                  cell["confident_wrong"], cell["effect_size"],
                  cell["topology"], cell["edge_prob"]))) % (2 ** 32)
    )

    # Standardized SEM (Kummerfeld et al., 2023). Random-weight generation is
    # varsortable (Reisach et al., 2021) and leaves effect size uncontrolled,
    # which would make every SHD number in the output uninterpretable.
    A, _W, _omega = make_feasible_dag(
        cell["d"], topology=cell["topology"], edge_prob=cell["edge_prob"],
        effect_size=cell["effect_size"], rng=rng)
    X, _W, _omega = sample_standardized_gaussian(
        A, cell["n"], effect_size=cell["effect_size"], rng=rng)

    design = ErrorDesign(base_rate=cell["base_rate"], severity=cell["severity"],
                         correlated=bool(cell["correlated"]),
                         confident_wrong_rate=cell["confident_wrong"],
                         numeric=True)
    Xc, E, amb = inject_errors(X, design, rng)

    discover = make_discoverer(algorithm, alpha=alpha, discrete=False)

    out = dict(cell)
    out["rep"] = rep
    out["algorithm"] = algorithm
    out["n_edges_true"] = int(A.sum())
    # Audited, not assumed: under the standardized sampler this must sit near
    # 0.5 (chance). A value near 1.0 would mean the benchmark is varsortable and
    # the learner could be recovering order by sorting variances.
    out["varsortability"] = varsortability(X, A)
    out["error_rate_realised"] = float(E.mean())
    out["errors_total"] = int(E.sum())
    out["ceiling_r"] = ceiling_correlation(amb, E)
    # Ground-truth analogue of the RQ8 / Stage 5 test 4 diagnostic: what share
    # of errors happened where the source was unambiguous, and paraphrasing
    # therefore had nothing to reveal.
    out["mode_collapse_fraction"] = mode_collapse_fraction(amb, E)

    # Per-record uncertainty signal (imperfect, as a real metric would be).
    u = uncertainty_from_ambiguity(amb, rng, noise=uncertainty_noise)
    out["r_uncertainty_vs_errorcount"] = _spearman_safe(u, E.sum(axis=1).astype(float))

    if E.sum() == 0:
        # Nothing was corrupted: impact must be identically zero. Recorded
        # explicitly rather than skipped, because it is the p = 0 anchor.
        out.update(mean_impact=0.0, frac_nonzero_impact=0.0, r_impact=float("nan"),
                   contrast_difference=float("nan"), contrast_excludes_zero=False)
        return out

    imp = per_record_impact(Xc, X, discover, max_records=max_records, rng=rng)
    impacts = imp["impact"]

    out["mean_impact"] = imp["mean_impact"]
    out["frac_nonzero_impact"] = imp["frac_nonzero_impact"]
    out["n_evaluated"] = imp["n_evaluated"]
    out["n_failed"] = imp["n_failed"]

    rq4 = impact_vs_uncertainty(u, impacts, rows=imp["rows"])
    out["r_impact"] = rq4["r_spearman"]

    contrast = high_low_contrast(u, impacts, rows=imp["rows"],
                                 n_boot=1000, rng=rng)
    out["contrast_difference"] = contrast.get("difference", float("nan"))
    out["contrast_excludes_zero"] = bool(contrast.get("excludes_zero", False))
    out["contrast_ci95"] = contrast.get("ci95")

    if run_placebo:
        pl = placebo_test(u, impacts, rows=imp["rows"], n_perm=500, rng=rng)
        out["placebo_p"] = pl["p_permutation"]

    return out


def _spearman_safe(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return _spearman(a, b)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Stage 0 simulation driver")
    p.add_argument("--grid", choices=["quick", "full"], default="quick")
    p.add_argument("--reps", type=int, default=5)
    p.add_argument("--algorithm", choices=["pc", "ges"], default="pc")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--max-records", type=int, default=15,
                   help="records evaluated for causal impact (cost: 1 discovery each)")
    p.add_argument("--bootstrap-B", type=int, default=100)
    p.add_argument("--uncertainty-noise", type=float, default=0.15)
    p.add_argument("--placebo", action="store_true")
    p.add_argument("--out", type=str, default="stage0_results.jsonl")
    p.add_argument("--limit", type=int, default=0, help="0 = no limit (debugging)")
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    grid = QUICK_GRID if args.grid == "quick" else FULL_GRID

    out_path = Path(args.out)
    done: set[tuple] = set()
    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done.add((rec.get("n"), rec.get("d"), rec.get("topology"),
                          rec.get("edge_prob"), rec.get("base_rate"),
                          rec.get("severity"), rec.get("correlated"),
                          rec.get("confident_wrong"), rec.get("effect_size"),
                          rec.get("rep")))
        print(f"[resume] {len(done)} records already present in {out_path}")

    total = len(list(cells(grid, args.seed))) * args.reps
    if args.limit:
        total = min(total, args.limit)

    started = time.time()
    written = 0
    with out_path.open("a", encoding="utf-8") as fh:
        for cell in cells(grid, args.seed):
            for rep in range(args.reps):
                key = (cell["n"], cell["d"], cell["topology"], cell["edge_prob"],
                       cell["base_rate"], cell["severity"], cell["correlated"],
                       cell["confident_wrong"], cell["effect_size"], rep)
                if key in done:
                    continue
                try:
                    rec = run_cell(cell, rep, args.algorithm, args.alpha,
                                   args.max_records, args.bootstrap_B,
                                   args.uncertainty_noise, args.placebo)
                except Exception as exc:              # keep the run alive
                    rec = dict(cell)
                    rec.update(rep=rep, error=f"{type(exc).__name__}: {exc}")
                fh.write(json.dumps(rec, default=str) + "\n")
                fh.flush()
                written += 1
                if written % 25 == 0 or written == 1:
                    rate = written / max(time.time() - started, 1e-9)
                    print(f"[{written}/{total}] {rate:.2f} rec/s  "
                          f"n={cell['n']} p={cell['base_rate']} "
                          f"corr={cell['correlated']}", flush=True)
                if args.limit and written >= args.limit:
                    print("[limit] reached")
                    return 0

    print(f"[done] wrote {written} records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
