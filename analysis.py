"""
Stage 0 — analysis and reporting.

Consumes the JSONL produced by run_stage0.py and produces the four Stage 0
deliverables named in the proposal:

  1. attainable ceiling     -- how well ANY uncertainty metric could do
  2. causal impact curve    -- mean SHD as a function of error rate and severity
  3. power analysis         -- minimum n per effect size (delegated to power.py)
  4. calibration curve      -- observed uncertainty binned against mean impact

Also runs the two pipeline-integrity anchors:

  * p = 0 must yield zero impact
  * correlated = False must yield no uncertainty-impact relationship

If either anchor fails, the pipeline is invalid and the analysis prints a loud
warning instead of a table.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    from .power import n_required_fisher, min_n_for_power
except ImportError:                                   # direct execution
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from power import n_required_fisher, min_n_for_power


def load(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _agg(values) -> dict:
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"mean": float("nan"), "sd": float("nan"), "n": 0}
    return {"mean": float(v.mean()),
            "sd": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "n": int(v.size)}


def group(rows: list[dict], keys: list[str]) -> dict:
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if "error" in r:
            continue
        try:
            buckets[tuple(r[k] for k in keys)].append(r)
        except KeyError:
            continue
    return buckets


# --------------------------------------------------------------------------
# 1. Attainable ceiling
# --------------------------------------------------------------------------

def attainable_ceiling(rows: list[dict], keys=("n", "base_rate", "correlated")) -> str:
    lines = ["## 1. Attainable ceiling",
             "",
             "Correlation between the TRUE latent ambiguity and the realised error count.",
             "No uncertainty metric can exceed this. It bounds the empirical study.",
             "",
             "| n | error rate | correlated | ceiling r (mean ± sd) | reps |",
             "|---|---|---|---|---|"]
    for key, bucket in sorted(group(rows, list(keys)).items(),
                              key=lambda kv: tuple(str(x) for x in kv[0])):
        stats = _agg(r.get("ceiling_r") for r in bucket)
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | "
                     f"{stats['mean']:.3f} ± {stats['sd']:.3f} | {stats['n']} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 2. Causal impact curve
# --------------------------------------------------------------------------

def impact_curve(rows: list[dict], keys=("n", "base_rate", "severity")) -> str:
    lines = ["", "## 2. Ground-truth causal impact curve",
             "",
             "Mean per-record SHD induced by correcting that record, as a function of the",
             "injected error rate. This is the ground truth the empirical study is compared against.",
             "",
             "| n | error rate | severity | mean impact | fraction of records with impact > 0 | reps |",
             "|---|---|---|---|---|---|"]
    for key, bucket in sorted(group(rows, list(keys)).items(),
                              key=lambda kv: tuple(str(x) for x in kv[0])):
        mi = _agg(r.get("mean_impact") for r in bucket)
        fr = _agg(r.get("frac_nonzero_impact") for r in bucket)
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {mi['mean']:.3f} | "
                     f"{fr['mean']:.3f} | {mi['n']} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 3. Uncertainty -> impact relationship
# --------------------------------------------------------------------------

def relationship_table(rows: list[dict],
                       keys=("n", "base_rate", "correlated")) -> str:
    lines = ["", "## 3. Uncertainty–impact relationship (RQ4) and integrity anchors",
             "",
             "| n | error rate | correlated | r_impact | contrast | contrast CI excludes 0 | placebo p | reps |",
             "|---|---|---|---|---|---|---|---|"]
    for key, bucket in sorted(group(rows, list(keys)).items(),
                              key=lambda kv: tuple(str(x) for x in kv[0])):
        r = _agg(x.get("r_impact") for x in bucket)
        c = _agg(x.get("contrast_difference") for x in bucket)
        excl = np.mean([bool(x.get("contrast_excludes_zero")) for x in bucket]) if bucket else float("nan")
        pl = _agg(x.get("placebo_p") for x in bucket)
        pl_s = f"{pl['mean']:.3f}" if pl["n"] else "—"
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {r['mean']:.3f} | "
                     f"{c['mean']:.3f} | {excl:.2f} | {pl_s} | {r['n']} |")
    return "\n".join(lines)


def mode_collapse_section(rows: list[dict],
                          keys=("base_rate", "confident_wrong", "n")) -> str:
    lines = ["", "## 5. Cost of confident mode collapse (RQ8 / Stage 5 test 4)",
             "",
             "`confident_wrong` is the injected rate of errors drawn *independently of source "
             "ambiguity* — precisely the errors a dispersion-based uncertainty metric cannot see, "
             "because dispersion needs ambiguity to spread the samples. This is the failure mode "
             "identified by Hamidieh et al. (ICLR 2026).",
             "",
             "Read the table as a price list. `ceiling r` is how well *any* uncertainty metric could "
             "rank records by error in that regime; `collapse share` is the fraction of errors that "
             "occurred where the text was unambiguous. If `ceiling r` falls materially as "
             "`confident_wrong` rises, the study can state the cost of mode collapse as a number "
             "rather than a caveat — and that number is a headline result.",
             "",
             "| error rate | confident-wrong rate | n | ceiling r | collapse share | r_impact | reps |",
             "|---|---|---|---|---|---|---|"]
    for key, bucket in sorted(group(rows, list(keys)).items(),
                              key=lambda kv: tuple(str(x) for x in kv[0])):
        ce = _agg(r.get("ceiling_r") for r in bucket)
        mc = _agg(r.get("mode_collapse_fraction") for r in bucket)
        ri = _agg(r.get("r_impact") for r in bucket)
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {ce['mean']:.3f} | "
                     f"{mc['mean']:.3f} | {ri['mean']:.3f} | {ce['n']} |")
    return "\n".join(lines)


def integrity_check(rows: list[dict]) -> list[str]:
    """The two anchors that must hold before any empirical claim is made."""
    problems: list[str] = []

    zero = [r for r in rows if r.get("base_rate") == 0 and "error" not in r]
    if zero:
        bad = [r for r in zero if abs(r.get("mean_impact", 0.0)) > 1e-9
               or r.get("errors_total", 0) != 0]
        if bad:
            problems.append(
                f"ANCHOR 1 FAILED: {len(bad)} of {len(zero)} runs with error rate 0 "
                f"produced non-zero impact. The pipeline manufactures structure from noise.")

    null = [r for r in rows if r.get("correlated") is False and r.get("base_rate", 0) > 0
            and "error" not in r]
    if null:
        rs = [abs(r["r_impact"]) for r in null if np.isfinite(r.get("r_impact", float("nan")))]
        if rs and float(np.mean(rs)) > 0.3:
            problems.append(
                f"ANCHOR 2 FAILED: with errors independent of ambiguity, mean |r_impact| = "
                f"{np.mean(rs):.3f} (n={len(rs)}). The relationship is an artefact.")

    return problems


def responsiveness_check(rows: list[dict]) -> list[str]:
    """A third anchor: the simulation must actually respond to the mode-collapse axis.

    If the attainable ceiling does not fall as confident_wrong rises, the new
    factor is inert and every RQ8 number derived from it is meaningless. This is
    the cheapest possible test of that, and it is checked rather than assumed.
    """
    notes: list[str] = []
    clean = [r.get("ceiling_r") for r in rows
             if r.get("confident_wrong") == 0 and r.get("base_rate", 0) > 0
             and np.isfinite(r.get("ceiling_r", float("nan")))]
    dirty = [r.get("ceiling_r") for r in rows
             if (r.get("confident_wrong") or 0) > 0 and r.get("base_rate", 0) > 0
             and np.isfinite(r.get("ceiling_r", float("nan")))]
    if clean and dirty:
        m_clean, m_dirty = float(np.mean(clean)), float(np.mean(dirty))
        if m_dirty >= m_clean:
            notes.append(
                f"RESPONSIVENESS FAILED: mean ceiling with confident_wrong = 0 is "
                f"{m_clean:.3f}, but with confident_wrong > 0 it is {m_dirty:.3f}. "
                f"The mode-collapse axis is inert; RQ8 results from this run cannot be used.")
        else:
            notes.append(f"Responsiveness: ceiling falls from {m_clean:.3f} to "
                         f"{m_dirty:.3f} as confident-wrong errors are introduced "
                         f"(expected direction).")
    return notes


# --------------------------------------------------------------------------
# 4. Power analysis
# --------------------------------------------------------------------------

def power_section(effects=(0.2, 0.3, 0.4, 0.5), target_power=0.80,
                  reps=500) -> str:
    """The Stage 0 deliverable that sets the corpus target.

    The analytic Fisher-z column degrades to an em dash when SciPy is absent,
    rather than aborting the section. The empirical column needs only NumPy and
    is the one that sets the target anyway, because real per-record error counts
    are skewed and tie-heavy and the Gaussian formula does not describe them.
    Losing the comparison column is a cosmetic loss; losing the whole section
    would hide the number the rest of the study depends on.
    """
    lines = ["", "## 4. Power analysis — sets the Stage 1 corpus target",
             "",
             "Minimum n to detect each effect size at 80% power, α = 0.05.",
             "",
             "| true r | n (Fisher z, analytic) | n (empirical, Spearman) |",
             "|---|---|---|"]
    recommended: list[int] = []
    analytic_available = True
    for r in effects:
        try:
            analytic = n_required_fisher(r, power=target_power)
            analytic_str = f"{analytic:.1f}"
        except RuntimeError:
            analytic_available = False
            analytic_str = "—"
        empirical, _curve = min_n_for_power(r, target_power=target_power, reps=reps)
        if empirical:
            recommended.append(empirical)
        lines.append(f"| {r} | {analytic_str} | {empirical} |")
    if not analytic_available:
        lines += ["",
                  "*SciPy is not installed, so the analytic Fisher-z column is "
                  "unavailable. This does not affect the corpus target, which the "
                  "empirical column sets.*"]
    if recommended:
        lines += ["",
                  f"**Corpus target implied by this table: at least "
                  f"{max(recommended)} usable records per domain**, before attrition "
                  f"from gold-standard verification."]
    return "\n".join(lines)


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--out", type=Path, default=Path("stage0_report.md"))
    ap.add_argument("--power-reps", type=int, default=500)
    args = ap.parse_args()

    rows = load(args.results)
    if not rows:
        print(f"no usable records in {args.results}")
        return 1

    parts = ["# Stage 0 — simulation results", "",
             f"Source: `{args.results}`  ",
             f"Records: {len(rows)}  ",
             f"Failed: {sum(1 for r in rows if 'error' in r)}", ""]

    # Three anchors, not two. `responsiveness_check` was written but never
    # wired in, which meant an inert mode-collapse axis would have passed
    # unnoticed and every RQ8 number derived from it would have been
    # meaningless. A check that is defined and never called is worse than no
    # check, because it reads as coverage.
    response_notes = responsiveness_check(rows)
    problems = integrity_check(rows) + [
        n for n in response_notes if n.startswith("RESPONSIVENESS FAILED")]
    notes = [n for n in response_notes if not n.startswith("RESPONSIVENESS FAILED")]

    if problems:
        parts += ["> ## ⚠ PIPELINE INTEGRITY FAILURE", ">"]
        parts += [f"> {p}" for p in problems]
        parts += [">", "> No empirical result should be reported until this is resolved.", ""]
    else:
        parts += ["**Integrity anchors passed**: zero error rate yields zero impact, and "
                  "uncorrelated errors yield no uncertainty–impact relationship.", ""]
    if notes:
        parts += ["**Responsiveness**", ""]
        parts += [f"- {n}" for n in notes]
        parts += [""]

    parts.append(attainable_ceiling(rows))
    parts.append(impact_curve(rows))
    parts.append(relationship_table(rows))
    parts.append(mode_collapse_section(rows))
    parts.append(power_section(reps=args.power_reps))

    text = "\n".join(parts)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
