"""
Extraction record validation.

Two layers, because they catch different things.

**Structural** — JSON Schema validation against `protocol/extraction_schema.json`.
Uses the `jsonschema` package when available, because the schema is the
published artifact and validating against it guarantees the two cannot drift
apart.

**Semantic** — the rules a schema cannot express, which are the ones that
actually matter here:

  1. Every key in `variables` must come from the controlled vocabulary named by
     `domain_variable_set`. The schema states this requirement in prose; only
     code can enforce it.
  2. `database_match` must be present when `ground_truth_source` is
     `external_database`, and absent otherwise.
  3. `evidence_span` must be non-empty for every variable. Without a verbatim
     span the gold standard cannot be adjudicated, and the protocol says so.
  4. Uncertainty components and the composite must lie in range, and the
     composite must not be present while every component is missing.
  5. Records whose `provenance.location` is `table` must not carry a
     `value_location` claim of `prose`, and vice versa. Prose-versus-table
     provenance is the study's cross-domain variable; a mislabelled one silently
     corrupts RQ6.

`validate_record` returns a list of problems rather than raising, so a whole
corpus can be validated in one pass and the failures reported together.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "protocol" / "extraction_schema.json"

# The controlled vocabularies, mirrored from the schema's $defs. Kept here as a
# literal rather than read out of the JSON because the semantic layer needs the
# key names as strings, and reading them out would make a silent schema edit
# change validation behaviour without any visible diff in this file.
VOCABULARIES: dict[str, set[str]] = {
    "BDD_v1": {
        "boron_doping_level", "sp3_sp2_ratio", "raman_fwhm", "film_thickness",
        "substrate", "deposition_method", "current_density", "faradaic_efficiency",
        "service_life", "delamination", "electrolyte", "cell_voltage",
    },
    "PEROVSKITE_v1": {
        "absorber_composition", "bandgap", "pce", "voc", "jsc", "ff",
        "device_architecture", "etl", "htl", "deposition_method",
        "annealing_temperature", "active_area", "stability_t80", "additives",
    },
}

# Variables whose value must be numeric, and whose uncertainty is a CV.
NUMERIC_VARIABLES = {
    "boron_doping_level", "sp3_sp2_ratio", "raman_fwhm", "film_thickness",
    "current_density", "faradaic_efficiency", "service_life", "cell_voltage",
    "bandgap", "pce", "voc", "jsc", "ff", "annealing_temperature",
    "active_area", "stability_t80",
}


def load_schema(path: Path | str = SCHEMA_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Structural
# --------------------------------------------------------------------------

def _structural_problems(record: dict, schema: dict) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        # Returned as a NOTE, not a problem. It is prefixed with 'note:' so that
        # `problems_only` can separate it -- otherwise a perfectly valid corpus
        # would be counted as entirely invalid whenever jsonschema is absent,
        # and the validator would report a failure that is really a missing
        # package.
        return ["note: structural layer skipped (jsonschema not installed); "
                "only the semantic rules were checked"]
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(record), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        out.append(f"schema: {loc}: {err.message}")
    return out


def problems_only(issues: Iterable[str]) -> list[str]:
    """Drop informational notes, keeping only genuine failures.

    Exists so that a missing optional package cannot be reported as a corpus of
    invalid records. Anything not prefixed 'note:' is treated as a problem.
    """
    return [i for i in issues if not i.startswith("note:")]


# --------------------------------------------------------------------------
# Semantic
# --------------------------------------------------------------------------

def _semantic_problems(record: dict) -> list[str]:
    problems: list[str] = []

    domain_set = record.get("domain_variable_set")
    variables = record.get("variables") or {}

    # 1. Controlled vocabulary membership.
    if domain_set in VOCABULARIES:
        allowed = VOCABULARIES[domain_set]
        unknown = sorted(set(variables) - allowed)
        if unknown:
            problems.append(
                f"semantic: variables/{domain_set}: not in the controlled vocabulary: "
                f"{', '.join(unknown)}")
        # A numeric variable must carry a numeric value.
        for name, entry in variables.items():
            if name in NUMERIC_VARIABLES:
                v = entry.get("value")
                if v is not None and not isinstance(v, (int, float)):
                    problems.append(
                        f"semantic: variables/{name}: declared numeric but value is "
                        f"{type(v).__name__} ({v!r})")
    elif domain_set is not None:
        problems.append(f"semantic: domain_variable_set: unknown vocabulary {domain_set!r}")

    # 2. database_match presence follows ground_truth_source.
    source = record.get("ground_truth_source")
    match = record.get("database_match")
    if source == "external_database" and not match:
        problems.append(
            "semantic: database_match: required when ground_truth_source is "
            "external_database, because the matching step is where an external "
            "gold standard silently fails")
    if source != "external_database" and match:
        problems.append(
            f"semantic: database_match: present but ground_truth_source is {source!r}")

    # 3. Evidence spans, and uncertainty range checks.
    for name, entry in variables.items():
        span = (entry or {}).get("as_reported")
        if not span or not str(span).strip():
            problems.append(
                f"semantic: variables/{name}/as_reported: empty; a value without a "
                f"verbatim source span cannot be adjudicated against the gold standard")

        u = entry.get("uncertainty")
        if u is not None and not (0.0 <= float(u) <= 1.0):
            problems.append(f"semantic: variables/{name}/uncertainty: {u} outside [0, 1]")

        comps = entry.get("uncertainty_components") or {}
        present = [k for k, v in comps.items() if v is not None]
        if u is not None and not present:
            problems.append(
                f"semantic: variables/{name}/uncertainty: set, but every component is "
                f"null; a composite with no components is not traceable")
        for k, v in comps.items():
            if v is None:
                continue
            lo, hi = (0.0, 1.0) if k in ("self_consistency", "cross_model_agreement") \
                else (0.0, float("inf"))
            if not (lo <= float(v) <= hi):
                problems.append(
                    f"semantic: variables/{name}/uncertainty_components/{k}: {v} "
                    f"outside [{lo}, {hi}]")

    # 4. Provenance consistency (RQ6's independent variable).
    #
    # `value_location` and `provenance.location` describe the same axis, and the
    # cross-domain contrast in RQ6 depends on them being right. Only a direct
    # contradiction between the two prose/table values is flagged; a value
    # marked `figure` against a table-level provenance is a different axis, not
    # an inconsistency.
    prov = record.get("provenance") or {}
    loc = prov.get("location")
    for name, entry in variables.items():
        vl = (entry or {}).get("value_location")
        if vl and loc and vl != loc and {vl, loc} <= {"table", "prose"}:
            problems.append(
                f"semantic: variables/{name}/value_location: says {vl!r} while "
                f"provenance.location says {loc!r}; RQ6's cross-domain contrast "
                f"depends on this being right")

    return problems


# --------------------------------------------------------------------------

def validate_record(record: dict, schema: dict | None = None) -> list[str]:
    """Return every issue found: failures (`schema:` / `semantic:`) and notes
    (`note:`). Use `problems_only` to separate them. An empty list means the
    record is valid and nothing was skipped."""
    schema = schema if schema is not None else load_schema()
    return _structural_problems(record, schema) + _semantic_problems(record)


def validate_corpus(records: Iterable[dict], schema: dict | None = None,
                    max_reported: int = 50) -> dict:
    """Validate many records and summarise.

    Returns per-record problems (capped for readability), counts, and the
    problem classes ranked by frequency -- because when a corpus fails
    validation it usually fails the same way thousands of times, and the ranked
    list is what tells you which rule to fix first.
    """
    schema = schema if schema is not None else load_schema()
    all_problems: list[tuple[str, list[str]]] = []
    counts: dict[str, int] = {}
    notes_seen: set[str] = set()

    n = 0
    for rec in records:
        n += 1
        issues = validate_record(rec, schema)
        for note in issues:
            if note.startswith("note:"):
                notes_seen.add(note)
        probs = problems_only(issues)
        if probs:
            rid = rec.get("record_id", f"<record {n}>")
            all_problems.append((rid, probs))
            for p in probs:
                kind = p.split(":")[1].strip() if ":" in p else p
                counts[kind] = counts.get(kind, 0) + 1

    return {
        "n_records": n,
        "n_valid": n - len(all_problems),
        "n_invalid": len(all_problems),
        "valid_fraction": (n - len(all_problems)) / n if n else float("nan"),
        "problems_by_field": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "notes": sorted(notes_seen),
        "examples": all_problems[:max_reported],
    }
