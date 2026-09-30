"""
End-to-end smoke test — the whole chain, with no model access.

This is the artifact that makes the pipeline verifiable in an environment that
cannot reach a model. It exercises, in order:

    adapters.ScriptedClient
        -> run_extraction.run_attempts
            -> run_extraction.build_record
                -> validate.validate_record
                    -> empirical.flatten_records
                        -> empirical.rq2_uncertainty_vs_error
                        -> empirical.rq8_mode_collapse

If this passes, the plumbing between extraction and analysis is sound, and the
only untested surface left is the HTTP client and the real data.

Run:

    python smoke_test.py

Needs only NumPy. `jsonschema` is optional and its absence is reported as a note.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "analysis"))

PASS, FAIL = "PASS", "FAIL"
_checks: list[tuple[str, object]] = []


def check(name: str):
    def deco(fn):
        _checks.append((name, fn))
        return fn
    return deco


# --------------------------------------------------------------------------

def _responses(centre: float, spread: float, filler: str) -> list[str]:
    """Ten JSON responses with a controlled spread, so Signal A is non-degenerate."""
    out = []
    for i in range(10):
        v = centre + spread * (i - 4.5) / 4.5
        out.append(json.dumps({
            "current_density": {"value": round(v, 3),
                                "span": f"a current density of {v:.2f} mA cm-2"},
            "substrate": {"value": filler, "span": f"deposited on {filler}"},
        }))
    return out


def _task():
    from run_extraction import ExtractionTask
    return ExtractionTask(
        record_id="BDD-000001", domain="BDD", domain_variable_set="BDD_v1",
        paper_text=("Boron-doped diamond films were deposited on titanium "
                    "substrates by HFCVD. The current density reached 12.5 mA cm-2 "
                    "with a Faradaic efficiency of 94 %."),
        variables=["current_density", "substrate"],
        source={"doi": "10.1/test", "title": "A test study", "year": 2024,
                "venue": "Test Journal"},
        provenance_location="prose", page=3)


def _clients():
    from adapters import ScriptedClient
    # Three families with different centres: this is what makes the cross-model
    # term meaningful rather than identically zero.
    return [
        ScriptedClient({"Source text": _responses(12.5, 0.4, "Ti")},
                       name="m1", revision="r1", family="famA"),
        ScriptedClient({"Source text": _responses(12.6, 0.5, "Ti")},
                       name="m2", revision="r2", family="famB"),
        ScriptedClient({"Source text": _responses(12.4, 0.3, "Nb")},
                       name="m3", revision="r3", family="famC"),
    ]


def _paraphrases():
    return [{"id": f"p{i:02d}", "instruction": f"Instruction variant {i}."}
            for i in range(10)]


# --------------------------------------------------------------------------
# Stage by stage
# --------------------------------------------------------------------------

@check("parsing: bare JSON, fenced JSON, and JSON with a preamble all parse")
def _parsing():
    from run_extraction import robust_json_loads
    assert robust_json_loads('{"a": 1}')[0] == {"a": 1}
    assert robust_json_loads('```json\n{"a": 2}\n```')[0] == {"a": 2}
    assert robust_json_loads('Here is the result:\n{"a": 3}')[0] == {"a": 3}
    assert robust_json_loads('{"a": {"b": 1}}')[0] == {"a": {"b": 1}}
    obj, err = robust_json_loads("no json here")
    assert obj is None and err
    assert robust_json_loads("")[1] == "empty response"
    assert robust_json_loads("[1, 2]")[0] is None, "a JSON array is not a record"


@check("parsing: a null stays null and is never coerced to zero")
def _null_not_zero():
    from run_extraction import parse_number
    assert parse_number(None) is None
    assert parse_number("not reported") is None
    assert parse_number(0) == 0.0
    assert parse_number("0") == 0.0
    assert parse_number("12.5 mA cm-2") == 12.5
    assert parse_number("-3.2e-2") == -0.032


@check("paraphrase loader: refuses a set that would make Signal A identically zero")
def _loader():
    from run_extraction import load_paraphrases
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "one.json"
        p.write_text(json.dumps({"paraphrases": [{"instruction": "only one"}]}),
                     encoding="utf-8")
        try:
            load_paraphrases(p)
        except ValueError as exc:
            assert "identically zero" in str(exc), str(exc)
        else:
            raise AssertionError("a single-paraphrase set was accepted")

        p2 = Path(d) / "empty.json"
        p2.write_text(json.dumps({"paraphrases": []}), encoding="utf-8")
        try:
            load_paraphrases(p2)
        except ValueError:
            pass
        else:
            raise AssertionError("an empty paraphrase set was accepted")


@check("attempts: every model x paraphrase combination is executed")
def _attempts():
    from run_extraction import run_attempts
    atts = run_attempts(_task(), _clients(), _paraphrases())
    assert len(atts) == 30, f"expected 3 models x 10 paraphrases, got {len(atts)}"
    assert {a.model for a in atts} == {"m1", "m2", "m3"}
    assert len({a.paraphrase_id for a in atts}) == 10
    assert all(a.parsed is not None for a in atts), "a scripted response failed to parse"


@check("signals: dispersion is non-zero, entropy is finite, and C is computable")
def _signals():
    from run_extraction import run_attempts, signals_for_variable
    atts = run_attempts(_task(), _clients(), _paraphrases())
    s = signals_for_variable(atts, "current_density", is_numeric=True)
    print(f"    A={s['signal_a_self_consistency']:.4f}  "
          f"B={s['signal_b_token_entropy']:.4f}  C={s['signal_c_epistemic']:.4f}  "
          f"U={s['uncertainty']:.4f}")
    assert s["n_attempts"] == 30
    assert s["n_parsed"] == 30
    assert np.isfinite(s["signal_a_self_consistency"])
    assert s["signal_a_self_consistency"] > 0, (
        "scripted responses differ, so dispersion must be non-zero")
    assert np.isfinite(s["signal_b_token_entropy"])
    assert np.isfinite(s["signal_c_epistemic"]), (
        "three models produced values, so the cross-model term must be computable")
    assert np.isfinite(s["uncertainty"])


@check("signals: an unparseable response counts against N, it is not discarded")
def _parse_failures():
    from adapters import ScriptedClient
    from run_extraction import run_attempts, signals_for_variable
    bad = ScriptedClient({"Source text": ["not json at all"]},
                         name="bad", revision="r", family="f")
    atts = run_attempts(_task(), [bad], _paraphrases())
    s = signals_for_variable(atts, "current_density", is_numeric=True)
    assert s["n_attempts"] == 10, "the denominator shrank; N must reflect all attempts"
    assert s["n_parsed"] == 0
    assert s["parse_failure_rate"] == 1.0


@check("record: assembly produces a schema-valid record")
def _record():
    from run_extraction import build_record, run_attempts
    from validate import problems_only, validate_record
    atts = run_attempts(_task(), _clients(), _paraphrases())
    rec = build_record(_task(), atts, {"current_density"})
    issues = validate_record(rec)
    probs = problems_only(issues)
    assert probs == [], f"the built record is invalid: {probs}"
    assert rec["record_id"] == "BDD-000001"
    assert rec["ground_truth_source"] == "none", (
        "ground truth must never be guessed at extraction time")
    assert set(rec["variables"]) == {"current_density", "substrate"}
    v = rec["variables"]["current_density"]
    assert v["value"] is not None
    assert v["uncertainty"] is not None
    assert v["n_attempts"] == 10
    for note in issues:
        assert note.startswith("note:")


@check("corpus: records and raw attempts both land on disk, and the run resumes")
def _corpus():
    from run_extraction import load_paraphrases, run_corpus
    with tempfile.TemporaryDirectory() as d:
        rec_p, att_p, par_p = (Path(d) / "records.jsonl",
                               Path(d) / "attempts.jsonl",
                               Path(d) / "paraphrases.json")
        par_p.write_text(json.dumps({"paraphrases": _paraphrases()}), encoding="utf-8")

        out = run_corpus([_task()], _clients(), load_paraphrases(par_p),
                         {"current_density"}, record_path=rec_p, attempt_path=att_p)
        assert out["records_written"] == 1
        assert rec_p.exists() and att_p.exists()

        n_attempts = sum(1 for _ in att_p.open(encoding="utf-8"))
        assert n_attempts == 30, (
            f"raw attempts are required for reproducibility, got {n_attempts}")

        # Second pass must skip, not duplicate
        out2 = run_corpus([_task()], _clients(), load_paraphrases(par_p),
                          {"current_density"}, record_path=rec_p, attempt_path=att_p)
        assert out2["records_written"] == 0 and out2["records_skipped"] == 1
        assert sum(1 for _ in rec_p.open(encoding="utf-8")) == 1, "run is not resumable"


@check("record/replay: the written attempt log is directly replayable")
def _replayable_log():
    """The capability most easily claimed and least easily delivered: that the
    pipeline's own output can be fed back in as a recording, so the whole chain
    runs offline. It could not be, until the log started carrying a `prompt_key`.

    This check runs the extractor against a scripted client, then replays the
    written log against a ReplayClient and asserts the same answers come back.
    Nothing else in the suite would notice if the two formats drifted apart.
    """
    import json
    from adapters import ReplayClient, prompt_key
    from run_extraction import (SYSTEM_PROMPT, build_user_prompt,
                                load_paraphrases, run_corpus)

    with tempfile.TemporaryDirectory() as d:
        rec_p, att_p, par_p = (Path(d) / "records.jsonl",
                               Path(d) / "attempts.jsonl",
                               Path(d) / "paraphrases.json")
        par_p.write_text(json.dumps({"paraphrases": _paraphrases()}), encoding="utf-8")
        reps = load_paraphrases(par_p)

        task = _task()
        run_corpus([task], _clients(), reps, {"current_density"},
                   record_path=rec_p, attempt_path=att_p)

        # Replay the log we just wrote, through the client meant to read it.
        for client_name in ("m1", "m2", "m3"):
            rp = ReplayClient(att_p, name=client_name, revision="replay",
                              family="replay")
            for p in reps:
                user = build_user_prompt(task, p["instruction"])
                c = rp.complete(SYSTEM_PROMPT, user)
                assert c.text, (
                    f"replay returned nothing for {client_name}/{p['id']}; the "
                    f"attempt log is not in the ReplayClient schema")
                assert c.top_logprobs, (
                    "log-probabilities did not survive the round trip, so a "
                    "replayed corpus would report NaN token entropy")
        print(f"    replayed {3 * len(reps)} completions from the written log")
def _normalise_constants():
    import copy
    from run_extraction import build_record, normalise_corpus, run_attempts
    atts = run_attempts(_task(), _clients(), _paraphrases())
    base = build_record(_task(), atts, {"current_density"})
    recs = []
    for i in range(4):
        r = copy.deepcopy(base)
        r["record_id"] = f"BDD-{i:06d}"
        recs.append(r)

    out, rep = normalise_corpus(recs)
    assert rep["n_records"] == 4
    assert all(r["uncertainty_normalised"] for r in out)
    # Every record is identical here, so every signal is constant. A percentile
    # transform of a constant maps everything to 1.0 -- maximum uncertainty
    # everywhere -- which is worse than useless, so it must be dropped.
    assert rep["signals_fitted"] == [], (
        f"a constant signal was fitted as a scale: {rep['signals_fitted']}")
    for r in out:
        for e in r["variables"].values():
            assert e["uncertainty"] is None, (
                "with no fittable signal the composite must be null, not zero")
    print(f"    constant corpus -> signals fitted: {rep['signals_fitted']}")

    varied = []
    for i in range(4):
        r = copy.deepcopy(base)
        r["record_id"] = f"BDD-{i:06d}"
        r["variables"]["current_density"]["uncertainty_components"]["self_consistency"] = i / 10
        varied.append(r)
    _out2, rep2 = normalise_corpus(varied)
    assert "self_consistency" in rep2["signals_fitted"], rep2
    print(f"    varied corpus   -> signals fitted: {rep2['signals_fitted']}")


@check("end to end: extraction output feeds the empirical analysis, in the right direction")
def _end_to_end():
    """The join that matters. Records produced by the extractor are normalised,
    given a simulated Stage 3 annotation, flattened, and run through RQ2 and RQ8.

    The corpora are built so that noisy papers have both higher dispersion and a
    larger deviation from the known truth, which means the chain must recover
    **above-chance** ranking. Asserting the direction and not merely that the
    functions return without raising is the point: a sign error anywhere between
    the extractor and the analyser would still produce a number.
    """
    from adapters import ScriptedClient
    from empirical import (flatten_records, rq2_uncertainty_vs_error,
                           rq8_mode_collapse)
    from run_extraction import build_record, normalise_corpus, run_attempts

    TRUTH = 12.5
    records = []
    for i in range(12):
        spread = 0.1 if i % 2 == 0 else 1.5
        clients = [ScriptedClient({"Source text": _responses(TRUTH, spread, "Ti")},
                                  name=f"m{k}", revision=f"r{k}", family=f"fam{k}")
                   for k in range(3)]
        task = _task()
        task.record_id = f"BDD-{i:06d}"
        atts = run_attempts(task, clients, _paraphrases())
        rec = build_record(task, atts, {"current_density"})

        # Simulated Stage 3 annotation against a known truth.
        v = rec["variables"]["current_density"]
        is_err = v["value"] is None or abs(v["value"] - TRUTH) > 0.5
        v["extraction_correct"] = not is_err
        v["error_type"] = "wrong_value" if is_err else "none"
        v["gold_value"] = TRUTH
        rec["ground_truth_source"] = "manual_annotation"
        records.append(rec)

    # The second pass is part of the chain, not an optional extra: the composite
    # written during extraction sits on raw, mutually incomparable scales.
    records, nrep = normalise_corpus(records)
    assert nrep["n_records"] == 12
    assert all(r["uncertainty_normalised"] for r in records), (
        "records reaching the analysis must carry normalised composites")
    print(f"    signals fitted: {nrep['signals_fitted']}")

    rows = flatten_records(records)
    assert len(rows) == 24, f"expected 12 records x 2 variables, got {len(rows)}"
    scored = [r for r in rows if r.correct is not None]
    assert len(scored) == 12, len(scored)
    assert len({r.record_id for r in rows}) == 12

    rq2 = rq2_uncertainty_vs_error(rows, B=200)
    assert "auc" in rq2, rq2
    print(f"    flattened {len(rows)} values from {len(records)} records; "
          f"AUC={rq2['auc']:.3f} error_rate={rq2['error_rate']:.2f}")
    assert np.isfinite(rq2["auc"])
    assert 0.0 <= rq2["error_rate"] <= 1.0
    assert rq2["auc"] > 0.5, (
        f"AUC {rq2['auc']:.3f} is at or below chance on data where dispersion and "
        f"error were constructed to agree; the chain is inverted somewhere")

    rq8 = rq8_mode_collapse(rows)
    assert "collapsed_share" in rq8 or "note" in rq8, rq8
    print(f"    RQ8 collapsed share = {rq8.get('collapsed_share', float('nan')):.3f}")


# --------------------------------------------------------------------------

def main() -> int:
    import contextlib
    import io

    print("End-to-end smoke test\n" + "=" * 66)
    width = max(len(n) for n, _ in _checks)
    n_fail = 0
    for name, fn in _checks:
        buf = io.StringIO()
        status, detail = PASS, ""
        try:
            with contextlib.redirect_stdout(buf):
                fn()
        except AssertionError as exc:
            status, detail = FAIL, str(exc)
        except Exception as exc:                       # noqa: BLE001
            status, detail = FAIL, f"{type(exc).__name__}: {exc}"
        print(f"[{'  ok  ' if status == PASS else ' FAIL '}] {name.ljust(width)}")
        for line in buf.getvalue().splitlines():
            print(line)
        if detail:
            print(f"         -> {detail}")
            n_fail += 1
    print("=" * 66)
    if n_fail:
        print(f"{n_fail} check(s) FAILED.")
        return 1
    print("All checks passed. The extraction-to-analysis chain is wired correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
