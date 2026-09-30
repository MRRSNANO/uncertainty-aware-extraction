# Stage 2 — prompt set and uncertainty quantification protocol

This document fixes the extraction instrument **before** any data is collected.
It is written to be published verbatim as supplementary material, because an
uncertainty metric whose prompts are not public cannot be audited, and an
unauditable uncertainty metric is the exact failure mode this paper criticises in
existing work.

---

## 0. Why the prompts must be frozen and public

Signal A is *dispersion across paraphrases*. That number is meaningless unless a
reader can re-run the identical paraphrase set. Therefore:

- The 10 paraphrases per extraction task are **frozen before Stage 1 screening**.
- They are released with the paper, in full, with a fixed random seed used to
  select them.
- Any later change to a prompt invalidates every uncertainty value computed
  before it. There is no "minor wording fix" after extraction begins.

---

## 1. The ten paraphrases: how they are built

Literal repetition gives near-zero dispersion and measures nothing. The set must
vary *surface form* while holding *semantics* fixed. Procedure:

1. **Generate 40 candidates** per extraction task using an LLM, under the
   instruction: *"Rewrite the following instruction so that it asks for exactly
   the same information, using different wording and a different sentence
   structure. Do not add, remove, or narrow the requested information."*
   Vary along axes: imperative vs. interrogative, formal vs. plain, explicit
   schema listing vs. prose description, field-order permutation.
2. **Back-translation filter.** Round-trip each candidate through a second
   language and back. Discard any candidate whose round-trip differs in the
   requested field set. This is a cheap automatic proxy for semantic equivalence.
3. **Field-set audit.** Ask the frozen extraction model, at temperature 0, to
   list the fields each candidate requests. Discard any candidate whose field set
   differs from the reference. This catches the common failure where a paraphrase
   silently drops "and report the units".
4. **Human check** on the surviving candidates by two authors, who must agree that
   the candidate is semantically equivalent. Disagreements are discarded, not
   adjudicated — with 40 candidates there is no need to argue over a marginal one.
5. **Sample 10** from the survivors with a recorded seed and publish all 40
   survivors plus the exclusion log.

**Report the discard count at every step.** A paraphrase set that lost 32 of 40
candidates is evidence that "paraphrase" is a fragile operation, and that is a
finding about the method, not a nuisance.

---

## 2. Extraction task template

```
SYSTEM
You extract quantitative data from scientific text. You return JSON only.
If a value is not stated in the supplied text, return null. Never infer,
interpolate, or convert between units unless the conversion is exact and the
source states both values.

USER
Source text:
---
{paper_text}
---

Extract the following {n_fields} variables:
{field_list}

Return a JSON object with exactly these keys. For each value also report the
verbatim span it came from.

{paraphrase_instruction}
```

The `{field_list}` is generated from `extraction_schema.json`, so the schema and
the prompts cannot drift apart. A validator rejects any response whose key set
differs from the schema's.

## 3. Model configuration

| Setting | Value | Why |
|---|---|---|
| Models | two instruction-tuned models from **independent families** | Signal C requires genuine model diversity; two sizes of the same family is not diversity |
| Weights | frozen, open-weight, exact revision hash recorded | A hosted model whose version changes mid-study makes the result unreproducible |
| Quantisation | recorded exactly (e.g. bf16, or 4-bit with the method named) | Quantisation changes output distributions and therefore dispersion |
| Temperature | 0.7 for the N attempts; 0.0 for the field-set audit | Non-zero is required for Signal A to exist at all; 0.0 is required for the audit |
| Top-p | recorded | |
| Seed | recorded per attempt where the backend supports it | |
| Max tokens | recorded | |

**Report the full configuration table in the paper.** Where a backend does not
expose seeds, say so explicitly rather than implying determinism.

---

## 4. The three uncertainty signals

For each target value, with **N attempts, where N is set by the RQ7 variance decomposition below
rather than fixed in advance.** The working assumption of N = 10 is provisional and must be replaced
by a measured allocation before the main extraction run.

> **Do not hard-code N = 10.** This document originally specified it; Ẓatuchin (2026) shows the
> paraphrase axis may carry almost no variance, in which case ten paraphrased runs is ten times the
> cost for a fraction of the signal. Section 6 defines the measurement and the decision rule.

### Signal A — paraphrase self-consistency

*Numeric.* Coefficient of variation across attempt values, after excluding
attempts beyond `3 × MAD` from the median.

```
CV = sd(values) / |mean(values)|          (mean near zero -> report as undefined)
```

Range-normalise before use in the composite, since CV is scale-free but not
[0, 1]. Report the raw CV as well.

*Categorical.* `1 − (majority agreement proportion)` over the N attempts.
Range: 0 (unanimous) to a maximum that depends on the number of levels; report
the normalised value `(1 − p_majority) / (1 − 1/k)` so that a 3-level and a
5-level variable are comparable.

**Always report `outlier_exclusion_rate`.** A value whose N attempts scatter
widely enough to trigger exclusions is a value the source text does not pin down,
and hiding that rate would hide the paper's own best evidence for Gap 2.

### Signal B — token-level uncertainty

Mean token entropy over the extracted span, or the sequence log-probability where
the backend exposes it. Normalise by span length, because raw entropy grows with
the number of tokens and would otherwise conflate "long answer" with "uncertain
answer".

### Signal C — cross-model agreement

Agreement between model 1 and model 2 on the same value, computed with the same
numeric tolerance and categorical-matching rule as Signal A. This is the only
signal that varies the *model*, and Ali (2026) shows this is the dimension a
single model provably lacks.

---

## 5. Composite and calibration

```
U_i = f(A_i, B_i, C_i)
```

`f` is fitted on the **gold-standard subset only**, by **split conformal
prediction** (primary) and isotonic regression (comparison), and evaluated
**cross-fitted** so the composite is never scored on the data that fitted it.

Calibration is reported as:

- a reliability diagram (predicted uncertainty vs. observed error rate, binned),
- the empirical coverage of the conformal interval at nominal 90% and 95%,
- the incremental Spearman correlation of each signal against error, alone and
  in combination, with bootstrap confidence intervals.

**Pre-registered decision rule.** If the conformal intervals are badly
miscalibrated (empirical coverage below the nominal level by more than 5
percentage points), Signal B is promoted to primary and the failure is reported
as a result, because it would contradict Xu & Lu (2025) on a new task class and
that is itself publishable.

---

## 6. Variance decomposition (RQ7) and the mode-collapse diagnostic (RQ8)

These two additions exist because of two papers published after the original design, either of which
would otherwise invalidate it. Both are now load-bearing rather than optional.

### RQ7 — measure the variance budget before spending it

Ẓatuchin (2026) decomposes response variance into resampling, **prompt paraphrase**, model identity
and query language, and finds the paraphrase component **near zero**, with repeats past the fifth
buying roughly 0.0003 in relative-error variance. If that holds for extraction, then N paraphrased
runs spends the whole budget on the axis carrying the least variance.

**Required measurement, taken before the main extraction run.** On a pilot set of 30 papers:

- B = 5 samples at a fixed prompt — decoding variance.
- 10 samples across the frozen paraphrase set — paraphrase variance.
- 5 samples from each of the three models at fixed prompt — model variance.
- Fit a crossed variance-components model with paper and variable as grouping factors, and report the
  share of total variance attributable to each component, with bootstrap confidence intervals.

**Decision rule, fixed in advance.** Allocate N in proportion to the measured shares. If the
paraphrase component falls below 20 % of the total, cut paraphrase repeats and reallocate to model and
decoding diversity. **The decomposition is itself reported as a result** — it is the first such
decomposition measured on an extraction task rather than on question answering, and disagreement with
Ẓatuchin would be a finding.

### RQ8 — the mode-collapse diagnostic

Hamidieh et al. (ICLR 2026) show that self-consistency "collapses when models are overconfident and
produce the same incorrect answer across samples", and that cross-model disagreement flags those cases
where dispersion does not. For extraction this is the failure that matters most: a confidently wrong
value is exactly the error a downstream causal analysis cannot absorb.

**Required diagnostic.** Among gold-standard values labelled incorrect, partition by dispersion:

- **collapsed** — dispersion at or near zero, i.e. all N paraphrases agree;
- **diffuse** — dispersion above the threshold used elsewhere in the analysis.

Report (a) the share of errors that are collapsed, (b) the share of collapsed errors that Signal C
flagged, and (c) both numbers restricted to the `hallucinated` and `wrong_value` classes, since those
are the epistemic errors the diagnostic targets.

**Pre-registered interpretation.** A collapsed share above 30 % means dispersion alone is not a
sufficient uncertainty instrument for extraction, whatever its per-value reliability on question
answering, and that becomes the paper's primary statement about the metric. A collapsed share below
10 %, with Signal C flagging most of it, supports the multi-signal design. **Both outcomes are
publishable; neither is a failure of the study.**

## 7. What this protocol deliberately does not do

- It does **not** treat dispersion as epistemic uncertainty. It treats it as a
  *measured quantity* whose relationship to error is the object of study (RQ2).
- It does **not** infer uncertainty from a single sample of one model, which
  Ali (2026) shows carries no cross-question structure.
- It does **not** discard outliers silently. Exclusion rates are reported.
- It does **not** allow the extraction temperature to be tuned to make Signal A
  look better; the temperature is fixed before any gold-standard annotation
  exists, precisely so that this tuning is impossible.

---

## 8. Outputs of this stage

| Artifact | Purpose |
|---|---|
| `prompts/frozen_paraphrases.json` | the 10 × task set, with generation seed |
| `prompts/paraphrase_candidates.jsonl` | all 40 candidates with filter verdicts |
| `prompts/config.json` | model revisions, quantisation, decoding settings |
| `extracted/records.jsonl` | records conforming to `extraction_schema.json` |
| `extracted/attempts.jsonl` | every individual attempt, retained for audit |
| `uncertainty/components.csv` | A, B, C and U per value |

`attempts.jsonl` is not optional. Without the raw attempts, the dispersion cannot
be recomputed by a reader and the central measurement is unverifiable.
