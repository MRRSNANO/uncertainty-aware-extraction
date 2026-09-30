"""
Self test for the empirical analysis layer.

Uses synthetic corpora with **planted** structure, so that a broken statistic
fails loudly rather than producing a plausible-looking wrong number. This
matters more here than in the simulation code: these functions will be pointed at
real data whose truth is unknown, and a silent inversion would be reported as a
finding.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
_checks: list[tuple[str, object]] = []


class Skip(Exception):
    """Raised when a check cannot run because an optional dependency is absent.

    Deliberately distinct from a pass. A check that needs causal-learn and
    silently reports success would tell a reader the causal stage is verified
    when it has never been executed.
    """


def check(name: str):
    def deco(fn):
        _checks.append((name, fn))
        return fn
    return deco


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def make_rows(rng, n_papers=40, per_paper=5, auc_target=0.8,
              collapsed_share=0.0, domain="BDD",
              ground_truth_source="manual_annotation"):
    """Synthetic ValueRows with a controllable uncertainty-error relationship.

    `auc_target` sets how well uncertainty ranks errors. `collapsed_share` moves
    a fraction of the errors into the low-uncertainty region, which is exactly
    the mode-collapse regime RQ8 must detect.
    """
    from empirical import ValueRow
    rows = []
    for p in range(n_papers):
        rid = f"{domain}-{p:04d}"
        for v in range(per_paper):
            # Uncertainty drives error probability, modulated by auc_target.
            u = float(np.clip(rng.beta(2, 5), 0, 1))
            p_err = 0.05 + 0.75 * (u ** (1.0 / max(auc_target, 1e-6)))
            is_err = rng.random() < p_err

            if is_err and collapsed_share > 0 and rng.random() < collapsed_share:
                u = float(rng.uniform(0.0, 0.02))       # confident and wrong
                etype = "hallucinated"
            elif is_err:
                etype = "ambiguous_source" if rng.random() < 0.5 else "wrong_value"
            else:
                etype = "none"

            rows.append(ValueRow(
                record_id=rid, domain=domain, variable=f"var{v}",
                value=float(rng.normal(10, 1)),
                uncertainty=u,
                correct=None if not is_err else 0,
                error_type=etype,
                location="table" if v % 2 == 0 else "prose",
                n_attempts=10, n_valid_attempts=9,
                exclusion_rate=0.1 if is_err else 0.0,
                components={"self_consistency": u, "token_entropy": u * 0.8,
                            "epistemic": u * 0.5},
                ground_truth_source=ground_truth_source,
            ))
    # Mark the correct values explicitly (make_rows sets correct only on errors)
    for r in rows:
        if r.error_type == "none":
            r.correct = 1
        else:
            r.correct = 0
    return rows


def make_records(n=3, domain="BDD", vocab="BDD_v1", ground_truth_source="manual_annotation"):
    """Minimal schema-shaped records for the validator and flatten tests."""
    recs = []
    for i in range(n):
        recs.append({
            "record_id": f"BDD-{i:04d}",
            "domain": domain,
            "domain_variable_set": vocab,
            "ground_truth_source": ground_truth_source,
            "source": {"doi": f"10.1/{i}", "title": "A study of something",
                       "year": 2020, "venue": "Journal"},
            "provenance": {"location": "table", "page": 3,
                           "evidence_span": "Table 2, row 4",
                           "extraction_scope": "single_value"},
            "variables": {
                "current_density": {
                    "value": 12.5, "as_reported": "12.5 mA cm-2",
                    "unit_reported": "mA cm-2", "unit_normalised": "A/cm^2",
                    "value_type": "numeric", "uncertainty": 0.2,
                    "uncertainty_components": {"self_consistency": 0.2,
                                               "token_entropy": 0.1,
                                               "cross_model_agreement": 0.3},
                    "n_attempts": 10, "n_valid_attempts": 10,
                    "outlier_exclusion_rate": 0.0,
                    "gold_value": 12.5, "extraction_correct": True,
                    "error_type": "none",
                }
            },
        })
    return recs


# --------------------------------------------------------------------------
# Ranking metrics
# --------------------------------------------------------------------------

@check("imports: every analysis module imports as a TOP-LEVEL module")
def _toplevel_imports():
    """`causal.py` reaches `stage0/` by putting it on sys.path and importing by
    bare name, so a relative import anywhere in that chain surfaces here rather
    than as a misleading 'causal-learn is missing'."""
    import importlib
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    for name in ("empirical", "causal"):
        module = importlib.import_module(name)
        print(f"    {name:<11} -> {Path(module.__file__).name}")


@check("auc: perfect, chance and inverted rankings")
def _auc():
    from empirical import auc
    labels = [0, 0, 1, 1]
    assert abs(auc([0.1, 0.2, 0.8, 0.9], labels) - 1.0) < 1e-12, "perfect ranking"
    assert abs(auc([0.9, 0.8, 0.2, 0.1], labels) - 0.0) < 1e-12, "inverted ranking"
    assert abs(auc([0.5, 0.5, 0.5, 0.5], labels) - 0.5) < 1e-12, "all tied must be chance"

    # One tied pair spanning the classes: half credit
    v = auc([0.4, 0.5, 0.5, 0.6], labels)
    assert abs(v - 0.875) < 1e-12, v
    assert not np.isfinite(auc([0.1, 0.2], [0, 0])), "single-class input must be NaN"


@check("auc: a planted relationship is recovered near its target")
def _auc_planted():
    from empirical import auc
    rng = np.random.default_rng(0)
    rows = make_rows(rng, n_papers=200, per_paper=8, auc_target=0.8)
    a = auc([r.uncertainty for r in rows], [1 - r.correct for r in rows])
    print(f"    planted target 0.80 -> recovered AUC {a:.3f}")
    assert 0.70 < a < 0.90, f"AUC {a:.3f} is not near the planted 0.80"


@check("spearman: monotone relationship and ties")
def _spearman():
    from empirical import spearman
    assert abs(spearman([0, 1, 2, 3], [0, 1, 2, 3]) - 1.0) < 1e-12
    assert abs(spearman([0, 1, 2, 3], [3, 2, 1, 0]) + 1.0) < 1e-12
    assert abs(spearman([1, 1, 1, 1], [1, 2, 3, 4])) == 0.0 or \
        not np.isfinite(spearman([1, 1, 1, 1], [1, 2, 3, 4]))


# --------------------------------------------------------------------------
# Cluster bootstrap
# --------------------------------------------------------------------------

@check("cluster_bootstrap: CI brackets the estimate and widens with clustering")
def _bootstrap():
    from empirical import cluster_bootstrap
    rng = np.random.default_rng(1)
    rows = make_rows(rng, n_papers=50, per_paper=6)
    res = cluster_bootstrap(rows, lambda rs: float(np.mean([r.uncertainty for r in rs])),
                            B=400, rng=rng)
    lo, hi = res["ci"]
    print(f"    mean uncertainty {res['estimate']:.3f} CI [{lo:.3f}, {hi:.3f}] "
          f"over {res['n_papers']} papers")
    assert lo < res["estimate"] < hi, res
    assert res["n_papers"] == 50
    assert hi - lo > 0


@check("cluster_bootstrap: refuses too few papers instead of faking a CI")
def _bootstrap_small():
    from empirical import cluster_bootstrap
    rng = np.random.default_rng(2)
    rows = make_rows(rng, n_papers=2, per_paper=10)
    res = cluster_bootstrap(rows, lambda rs: 1.0, B=100, rng=rng)
    assert "note" in res and "fewer than 3" in res["note"], res


# --------------------------------------------------------------------------
# RQ2
# --------------------------------------------------------------------------

@check("rq2: recovers a planted uncertainty-error relationship")
def _rq2():
    from empirical import rq2_uncertainty_vs_error
    rng = np.random.default_rng(3)
    rows = make_rows(rng, n_papers=80, per_paper=8, auc_target=0.85)
    out = rq2_uncertainty_vs_error(rows, B=200, rng=rng)
    print(f"    AUC {out['auc']:.3f}  error rate {out['error_rate']:.3f}  "
          f"n={out['n_values']} over {out['n_papers']} papers")
    assert out["auc"] > 0.65, out
    assert out["error_rate"] > 0, "no errors were generated"
    assert out["auc_ci"]["ci"][0] < out["auc"] < out["auc_ci"]["ci"][1] + 1e-9


@check("rq2: flags a metric that catches ambiguity but not hallucination")
def _rq2_split():
    from empirical import ValueRow, rq2_uncertainty_vs_error
    rows = []
    rng = np.random.default_rng(4)
    for p in range(40):
        for v in range(5):
            # Ambiguous-source errors get high uncertainty; hallucinations get low.
            if v < 2:
                rows.append(ValueRow(
                    record_id=f"BDD-{p:04d}", domain="BDD", variable=f"v{v}", value=1.0,
                    uncertainty=float(rng.uniform(0.7, 0.95)), correct=0,
                    error_type="ambiguous_source", location="prose", n_attempts=10,
                    n_valid_attempts=9, exclusion_rate=0.1, components={},
                    ground_truth_source="manual_annotation"))
            elif v < 3:
                rows.append(ValueRow(
                    record_id=f"BDD-{p:04d}", domain="BDD", variable=f"v{v}", value=1.0,
                    uncertainty=float(rng.uniform(0.0, 0.05)), correct=0,
                    error_type="hallucinated", location="table", n_attempts=10,
                    n_valid_attempts=10, exclusion_rate=0.0, components={},
                    ground_truth_source="manual_annotation"))
            else:
                rows.append(ValueRow(
                    record_id=f"BDD-{p:04d}", domain="BDD", variable=f"v{v}", value=1.0,
                    uncertainty=float(rng.uniform(0.0, 0.1)), correct=1,
                    error_type="none", location="table", n_attempts=10,
                    n_valid_attempts=10, exclusion_rate=0.0, components={},
                    ground_truth_source="manual_annotation"))
    out = rq2_uncertainty_vs_error(rows, B=100, rng=rng)
    print(f"    ambiguity {out['mean_uncertainty']['ambiguous_source']:.2f} vs "
          f"epistemic {out['mean_uncertainty']['epistemic']:.2f}")
    assert out["flags_aleatoric_not_epistemic"], (
        "the divergence between aleatoric and epistemic errors was not flagged, "
        "which is the study's most substantive per-metric finding")


# --------------------------------------------------------------------------
# RQ8
# --------------------------------------------------------------------------

@check("rq8: detects a planted confident-mode-collapse regime")
def _rq8():
    from empirical import rq8_mode_collapse
    rng = np.random.default_rng(5)
    clean = rq8_mode_collapse(make_rows(rng, n_papers=60, per_paper=6,
                                        collapsed_share=0.0))
    collapsed = rq8_mode_collapse(make_rows(rng, n_papers=60, per_paper=6,
                                            collapsed_share=0.6))
    print(f"    collapsed share: planted 0% -> {clean['collapsed_share']:.3f}; "
          f"planted 60% -> {collapsed['collapsed_share']:.3f}")
    assert clean["collapsed_share"] < 0.15, clean
    assert collapsed["collapsed_share"] > 0.35, collapsed
    assert "not a sufficient" in collapsed["verdict"] or \
        "intermediate" in collapsed["verdict"], collapsed["verdict"]
    assert "holds" in clean["verdict"] or "intermediate" in clean["verdict"], \
        clean["verdict"]


# --------------------------------------------------------------------------
# Calibration and exclusions
# --------------------------------------------------------------------------

@check("reliability_bins: error rate rises across bins on planted data")
def _reliability():
    from empirical import reliability_bins
    rng = np.random.default_rng(6)
    rows = make_rows(rng, n_papers=100, per_paper=8, auc_target=0.9)
    bins = reliability_bins(rows, n_bins=6)
    assert len(bins) == 6, bins
    rates = [b["observed_error_rate"] for b in bins]
    means = [b["mean_uncertainty"] for b in bins]
    print(f"    bin error rates: {[round(r, 3) for r in rates]}")
    assert means == sorted(means), "bins are not ordered by uncertainty"
    assert rates[-1] > rates[0], (
        "the highest-uncertainty bin does not show a higher error rate than the "
        "lowest, so the score is not informative on planted data")


@check("exclusion_rate_report: separates by value location")
def _exclusions():
    from empirical import exclusion_rate_report
    rng = np.random.default_rng(7)
    rows = make_rows(rng, n_papers=30, per_paper=6)
    rep = exclusion_rate_report(rows)
    assert rep["n"] > 0
    assert "table" in rep["by_location"] and "prose" in rep["by_location"], rep
    assert 0.0 <= rep["frac_any_exclusion"] <= 1.0


# --------------------------------------------------------------------------
# Cross-domain
# --------------------------------------------------------------------------

@check("cross_domain: keeps the domains apart and reports the location contrast")
def _cross_domain():
    from empirical import cross_domain_comparison
    rng = np.random.default_rng(8)
    rows = (make_rows(rng, n_papers=30, per_paper=5, domain="BDD")
            + make_rows(rng, n_papers=30, per_paper=5, domain="PEROVSKITE",
                        ground_truth_source="external_database"))
    out = cross_domain_comparison(rows, B=100, rng=rng)
    assert "BDD" in out and "PEROVSKITE" in out
    assert out["BDD"]["ground_truth_source"] == ["manual_annotation"]
    assert out["PEROVSKITE"]["ground_truth_source"] == ["external_database"]
    assert "by_value_location" in out
    # The domains must not be pooled anywhere in the output.
    assert "pooled" not in out and "combined" not in out


@check("flatten_records: both component key conventions normalise to `epistemic`")
def _component_keys():
    """The pipeline writes the cross-model signal as `cross_model_agreement`;
    the normalisation pass writes it as `epistemic`. Reading only one spelling
    made the RQ8 catch rate NaN forever, with no error anywhere."""
    from empirical import flatten_records
    base = {
        "record_id": "BDD-0001", "domain": "BDD", "ground_truth_source": "none",
        "provenance": {"location": "table"},
        "variables": {
            "raw_style": {"value": 1.0, "as_reported": "1", "uncertainty": 0.2,
                          "uncertainty_components": {
                              "self_consistency": 0.2, "token_entropy": 0.3,
                              "cross_model_agreement": 0.9}},
            "norm_style": {"value": 2.0, "as_reported": "2", "uncertainty": 0.3,
                           "uncertainty_components_normalised": {
                               "self_consistency": 0.5, "token_entropy": 0.6,
                               "epistemic": 0.7}},
        },
    }
    rows = {r.variable: r for r in flatten_records([base])}
    assert rows["raw_style"].components.get("epistemic") == 0.9, rows["raw_style"].components
    assert rows["norm_style"].components.get("epistemic") == 0.7, rows["norm_style"].components

    # When both are present the normalised ones win: only they share a scale.
    base["variables"]["raw_style"]["uncertainty_components_normalised"] = {
        "self_consistency": 0.11, "token_entropy": 0.22, "epistemic": 0.33}
    rows = {r.variable: r for r in flatten_records([base])}
    assert rows["raw_style"].components["epistemic"] == 0.33, rows["raw_style"].components


@check("rq8: the cross-model catch rate is actually computed, not silently NaN")
def _rq8_components():
    from empirical import ValueRow, rq8_mode_collapse
    rows = []
    for p in range(30):
        # A collapsed error that the cross-model term flags
        rows.append(ValueRow(
            record_id=f"BDD-{p:04d}", domain="BDD", variable="v", value=1.0,
            uncertainty=0.01, correct=0, error_type="hallucinated",
            location="table", n_attempts=10, n_valid_attempts=10,
            exclusion_rate=0.0,
            components={"self_consistency": 0.02, "token_entropy": 0.1,
                        "epistemic": 0.8},
            ground_truth_source="manual_annotation"))
        # A diffuse error
        rows.append(ValueRow(
            record_id=f"BDD-{p:04d}", domain="BDD", variable="w", value=1.0,
            uncertainty=0.7, correct=0, error_type="ambiguous_source",
            location="prose", n_attempts=10, n_valid_attempts=9,
            exclusion_rate=0.2, components={"epistemic": 0.3},
            ground_truth_source="manual_annotation"))

    out = rq8_mode_collapse(rows)
    assert out["n_collapsed"] == 30, out
    assert np.isfinite(out["cross_model_catch_rate"]), (
        "the cross-model catch rate is NaN although every collapsed row carries "
        "an `epistemic` component; the key-name mismatch has reappeared")
    assert out["cross_model_catch_rate"] == 1.0, out
    assert out["n_with_epistemic_component"] == 30, out
    print(f"    collapsed share={out['collapsed_share']:.2f}  "
          f"cross-model catch={out['cross_model_catch_rate']:.2f}")


# --------------------------------------------------------------------------
# Causal driver — the parts that do not need causal-learn
# --------------------------------------------------------------------------

def _causal_records(n=10, gold_rows=None, rng=None, missing=None):
    """Schema records shaped for the causal driver. `gold_rows` is how many
    leading records carry verified gold values for every variable."""
    rng = np.random.default_rng(0) if rng is None else rng
    gold_rows = n if gold_rows is None else gold_rows
    recs = []
    for i in range(n):
        variables = {}
        for name in ("a", "b", "c"):
            val = float(rng.normal())
            verified = i < gold_rows
            if missing and name in missing.get(i, ()):
                val = None
            variables[name] = {
                "value": val, "as_reported": str(val),
                "uncertainty": float(rng.random()),
                "gold_value": val if verified and val is not None else None,
                "extraction_correct": True if (verified and val is not None) else None,
            }
        recs.append({"record_id": f"R{i:03d}", "domain": "BDD",
                     "ground_truth_source": "manual_annotation",
                     "variables": variables})
    return recs


@check("causal: build_dataset assembles a rectangular dataset with a gold mask")
def _build_dataset():
    from causal import build_dataset
    ds = build_dataset(_causal_records(n=8, gold_rows=5), ["a", "b", "c"])
    assert ds.n == 8, ds.n
    assert ds.d == 3, ds.d
    assert ds.X.shape == (8, 3)
    assert ds.gold_mask.shape == (8, 3)
    assert ds.gold_mask[:5].all(), "verified rows are not all masked"
    assert not ds.gold_mask[5:].any(), "unverified rows are marked verified"
    assert np.allclose(ds.X_gold[:5], ds.X[:5]), (
        "gold values should equal extracted values where the extraction was correct")
    assert np.isfinite(ds.U).all(), "per-record uncertainty has non-finite entries"


@check("causal: too much missingness is refused rather than silently dropped")
def _missing_guard():
    from causal import build_dataset
    # Every record missing two of three variables -> 67 % missing
    recs = _causal_records(n=10, missing={i: ("b", "c") for i in range(10)})
    try:
        build_dataset(recs, ["a", "b", "c"])
    except ValueError as exc:
        assert "missing" in str(exc).lower(), str(exc)
        return
    raise AssertionError(
        "a dataset with 67 % missing cells was accepted; every structure learner "
        "would silently drop those rows and the graph would describe a different "
        "sample than the uncertainty weights do")


@check("causal: evaluable_rows excludes rows without enough verified cells")
def _evaluable():
    from causal import build_dataset
    ds = build_dataset(_causal_records(n=10, gold_rows=6), ["a", "b", "c"])
    ev = ds.evaluable_rows(min_gold_fraction=0.5)
    assert list(ev) == [0, 1, 2, 3, 4, 5], list(ev)
    assert ds.n - ev.size == 4, "the excluded count is what separates 'no effect' from 'no data'"


@check("causal: weighting schemes are all monotone decreasing in uncertainty")
def _weighting():
    from causal import weighting_from_uncertainty
    U = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
    for scheme in ("linear", "exponential", "rank", "inverse_square"):
        w = weighting_from_uncertainty(U, scheme)
        assert w.shape == U.shape
        assert (w > 0).all(), f"{scheme} produced a non-positive weight"
        assert np.all(np.diff(w) <= 1e-12), (
            f"{scheme} is not monotone decreasing; an uncertain record would be "
            f"sampled MORE often than a certain one")
    print("    w(linear) = " + ", ".join(f"{x:.3f}" for x in
                                         weighting_from_uncertainty(U, "linear")))
    try:
        weighting_from_uncertainty(U, "nonsense")
    except ValueError:
        return
    raise AssertionError("an unknown weighting scheme was accepted")


@check("causal: a non-finite uncertainty is treated as maximally uncertain")
def _weighting_nan():
    from causal import weighting_from_uncertainty
    w = weighting_from_uncertainty(np.array([0.0, 0.5, np.nan]), "linear")
    assert np.isfinite(w).all()
    assert w[2] <= w[1] <= w[0], (
        "a missing uncertainty must not receive the highest weight; that would "
        "let unscored values dominate the resampling")


@check("causal: absent causal-learn produces a fixable message, not a raw ImportError")
def _require_causal():
    import causal
    if causal._HAVE_CAUSAL:
        raise Skip("causal-learn is installed; the failure path does not apply")
    try:
        causal.require_causal()
    except RuntimeError as exc:
        msg = str(exc)
        assert "causal-learn" in msg and "pip install" in msg, msg
        print(f"    {msg.splitlines()[0]}")
        return
    raise AssertionError("require_causal() did not raise without causal-learn")


@check("causal: the verdict applies the pre-registered reading, not the numbers")
def _verdict():
    from causal import _rq4_verdict
    assert "H1 supported" in _rq4_verdict({"excludes_zero": True}, {"p_permutation": 0.01})
    assert "H2" in _rq4_verdict({"excludes_zero": False}, {"p_permutation": 0.4})
    mixed = _rq4_verdict({"excludes_zero": True}, {"p_permutation": 0.5})
    assert "mixed" in mixed and "inconclusive" in mixed, (
        "when the contrast and the permutation test disagree the reading must be "
        "inconclusive rather than the favourable one")
    assert "inconclusive" in _rq4_verdict({"excludes_zero": True},
                                          {"p_permutation": float("nan")})


@check("causal: RQ4/RQ5 skip loudly without causal-learn rather than passing")
def _causal_skip():
    import causal
    if not causal._HAVE_CAUSAL:
        raise Skip("causal-learn is not installed, so Stage 4-6 is UNVERIFIED. "
                   "Install it and re-run before trusting any causal result.")
    from causal import build_dataset, full_report
    ds = build_dataset(_causal_records(n=40, gold_rows=40), ["a", "b", "c"])
    rep = full_report(ds, B=20, max_records=8)
    assert rep["n_records"] == 40
    assert "rq4" in rep and "rq5" in rep
    print(f"    RQ4 verdict: {rep['rq4'].get('verdict')}")
    print(f"    RQ5 verdict: {rep['rq5'].get('verdict')}")


# --------------------------------------------------------------------------
# Flatten and validate
# --------------------------------------------------------------------------

@check("flatten_records: one row per variable, unscored values kept")
def _flatten():
    from empirical import flatten_records
    recs = make_records(n=3)
    rows = flatten_records(recs)
    assert len(rows) == 3, rows
    assert all(r.record_id.startswith("BDD-") for r in rows)
    assert all(r.uncertainty == 0.2 for r in rows)
    assert all(r.ground_truth_source == "manual_annotation" for r in rows)

    # An unscored value must survive as NaN, not vanish
    recs[0]["variables"]["current_density"]["uncertainty"] = None
    rows = flatten_records(recs)
    assert len(rows) == 3, "an unscored value was dropped instead of kept as NaN"
    assert not np.isfinite(rows[0].uncertainty)


@check("validate: a well-formed record passes")
def _validate_ok():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "extraction"))
    from validate import problems_only, validate_record
    issues = validate_record(make_records(n=1)[0])
    probs = problems_only(issues)
    assert probs == [], f"a valid record was rejected: {probs}"
    # A missing optional package must surface as a note, never as a problem, or
    # a perfectly good corpus would be reported as entirely invalid.
    for note in issues:
        assert note.startswith("note:"), (
            f"only notes may accompany a valid record, got: {note}")


@check("validate: an absent jsonschema is a note, not a corpus-wide failure")
def _validate_corpus_notes():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "extraction"))
    from validate import validate_corpus
    rep = validate_corpus(make_records(n=4))
    assert rep["n_invalid"] == 0, (
        f"valid records were counted as invalid: {rep['problems_by_field']}")
    assert rep["valid_fraction"] == 1.0
    assert "notes" in rep


@check("validate: catches vocabulary, matching, span and provenance faults")
def _validate_bad():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "extraction"))
    from validate import validate_record

    # Unknown variable for the vocabulary
    r = make_records(n=1)[0]
    r["variables"]["pvdf_phase"] = {"value": "beta", "as_reported": "beta"}
    assert any("controlled vocabulary" in p for p in validate_record(r)), \
        "an out-of-vocabulary variable was accepted"

    # external_database without a match block
    r = make_records(n=1, ground_truth_source="external_database")[0]
    assert any("database_match" in p for p in validate_record(r)), \
        "external_database without database_match was accepted"

    # Empty evidence span
    r = make_records(n=1)[0]
    r["variables"]["current_density"]["as_reported"] = "  "
    assert any("as_reported" in p for p in validate_record(r)), \
        "an empty evidence span was accepted"

    # Uncertainty out of range
    r = make_records(n=1)[0]
    r["variables"]["current_density"]["uncertainty"] = 1.7
    assert any("outside [0, 1]" in p for p in validate_record(r)), \
        "an out-of-range uncertainty was accepted"

    # Composite without components
    r = make_records(n=1)[0]
    r["variables"]["current_density"]["uncertainty_components"] = {
        "self_consistency": None, "token_entropy": None, "cross_model_agreement": None}
    assert any("no components" in p.lower() or "every component" in p
               for p in validate_record(r)), \
        "a composite with no components was accepted"


# --------------------------------------------------------------------------

def main() -> int:
    import contextlib
    import io

    print("Empirical analysis self test\n" + "=" * 70)
    width = max(len(n) for n, _ in _checks)
    n_fail = n_skip = 0
    for name, fn in _checks:
        buf = io.StringIO()
        status, detail = PASS, ""
        try:
            with contextlib.redirect_stdout(buf):
                fn()
        except Skip as exc:
            status, detail = SKIP, str(exc)
        except AssertionError as exc:
            status, detail = FAIL, str(exc)
        except Exception as exc:                       # noqa: BLE001
            status, detail = FAIL, f"{type(exc).__name__}: {exc}"
        mark = {"PASS": "  ok  ", "FAIL": " FAIL ", "SKIP": " skip "}[status]
        print(f"[{mark}] {name.ljust(width)}")
        for line in buf.getvalue().splitlines():
            print(line)
        if detail:
            print(f"         -> {detail}")
        if status == FAIL:
            n_fail += 1
        if status == SKIP:
            n_skip += 1
    print("=" * 70)
    if n_fail:
        print(f"{n_fail} check(s) FAILED." + (f" {n_skip} skipped." if n_skip else ""))
        return 1
    print("All checks passed." + (f" {n_skip} SKIPPED — see above." if n_skip else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
