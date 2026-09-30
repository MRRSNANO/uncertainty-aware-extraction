# Fieldwork 3 — variance decomposition pilot (RQ7)

**Purpose.** Find out what the N extraction runs actually buy, *before* spending the budget. This is
the cheapest high-value measurement in the study, and it can be run as soon as model access exists —
it needs no gold standard, no annotation, and no causal analysis.

## Why this is not optional

Ẓatuchin (2026) decomposes response variance into resampling, **prompt paraphrase**, model identity
and query language, and finds the paraphrase component **near zero** — with repeats past the fifth
buying roughly 0.0003 in relative-error variance. That was measured on brand-answer questions, not on
scientific extraction, so it may or may not transfer.

The proposal's original design ran **ten paraphrased samples** per value. If the paraphrase axis
carries almost no variance in extraction either, that is ten times the cost for a fraction of the
signal — and, worse, the dispersion being used as the uncertainty metric would be dominated by
decoding noise rather than by anything about the source text.

Equally important in the other direction: if paraphrase variance *is* large in extraction, that is a
genuine disagreement with Ẓatuchin on a new task class, and it is publishable on its own.

## Scope

- **30 papers**, drawn from the target domains (10 BDD, 20 perovskite — perovskite is easier to obtain
  and the pilot is about variance structure, not about the domains).
- **5 numeric target variables per paper**, chosen to span the plausible ambiguity range: include at
  least one value that is easy (stated explicitly) and one that is hard (unit conversion, or a value
  stated for a different condition).
- **Restrict this pilot to numeric variables.** Categorical and relational variables need a different
  decomposition (agreement probabilities rather than variances) and would double the design. Note the
  restriction in the paper; the categorical case is handled separately in the main run.

## Design — 45 runs per value

| Cell | Model | Prompt | Runs | Estimates |
|---|---|---|---|---|
| A | M1 | fixed P0 | 5 | decoding variance |
| B | M1 | paraphrases P1–P10 | 3 each (30) | paraphrase variance |
| C | M2, M3 | fixed P0 | 5 each (10) | model variance |

**Total per value: 45 runs.** For 30 papers × 5 values: **6,750 calls.** At ordinary API rates this is
a few hours of wall-clock time and a modest cost, and it determines the design of every subsequent
stage.

All decoding settings are recorded exactly: model revision hash, quantisation, temperature, top-p, max
tokens, seed where the backend exposes one. Where a backend does not expose a seed, say so rather than
implying determinism.

### Why each paraphrase gets 3 runs, not 1

With a single run per paraphrase, the observed spread across paraphrases is
`σ²_paraphrase + σ²_decoding`, and the two cannot be separated — which is precisely the confusion this
pilot exists to resolve. Three runs per paraphrase makes the paraphrase cell mean estimable and the
components separable.

## Estimation

Work on the **log scale** for numeric values (or on `log|value|` where values are strictly positive
and may span orders of magnitude). This keeps the decomposition from being dominated by whichever
variable happens to have the largest units.

Moment-based estimators, one per value, then pooled:

```
σ²_decoding   = mean over cells of the within-cell sample variance
                 (cell A alone, and cells B and C combined, reported separately as a consistency check)

σ²_paraphrase = Var(cell means of B) − σ²_decoding / 3

σ²_model      = Var(cell means of C) − σ²_decoding / 5

share_X       = σ²_X / (σ²_decoding + σ²_paraphrase + σ²_model)
```

Negative variance estimates are expected and must be **reported as negative, not truncated to zero** —
they are the standard signal that a component is indistinguishable from noise at this sample size.
Truncating them would invent a component that is not there.

Report the shares per domain, with bootstrap confidence intervals resampling **papers** (not values),
since values within a paper are not independent.

## Decision rule — fix this before running

| Paraphrase share | Action |
|---|---|
| ≥ 40 % | The original design was right. Keep 10 paraphrases, and cite this as a measured disagreement with Ẓatuchin on extraction. |
| 20–39 % | Keep paraphrase as one signal, but reallocate a third of the repeats to model diversity. |
| 10–19 % | Paraphrase is a minor axis. Cut paraphrases to 4 and reallocate to models. Dispersion is dominated by decoding noise, which must be said explicitly in the paper. |
| < 10 % | **The dispersion-based uncertainty metric is measuring the wrong thing.** Report this as the pilot's primary finding, and rebuild Signal A around model diversity and token entropy. This is a publishable result, not a setback. |

## What to record

```csv
paper_id,domain,variable,value_reported,unit,cell,model,prompt_id,run_index,extracted_value,latency_s,raw_response_id
```

The last column is a pointer into the stored raw responses. **Store every raw response.** Without them
the decomposition cannot be recomputed by a reader, and an unverifiable variance decomposition is
worth little.

## Deliverables

| Artifact | Contents |
|---|---|
| `pilot/runs.jsonl` | every individual run, raw |
| `pilot/variance_components.csv` | per-value σ² and shares |
| `pilot/shares.json` | pooled shares per domain, with bootstrap CIs, and the negative estimates kept as negative |
| `pilot/decision.md` | which row of the decision table applies, and the resulting N allocation |

## What this pilot does not do

- It does not validate the uncertainty metric against error. That is RQ2 and it needs the gold
  standard.
- It does not tell you whether dispersion predicts *causal* damage. That is RQ4 and it needs the full
  pipeline.
- It says nothing about categorical or relational variables, by design.

It answers one question — *where is the variance?* — and that question has to be answered before any
of the others can be designed honestly.
