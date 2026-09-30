# Stage 3 — gold-standard annotation codebook

The entire validity of this paper rests on a hand-built gold standard. In
proposal v1 this was listed as a limitation ("inter-rater reliability is not
assessed"). That limitation is not survivable at review for a paper whose central
claim is about measurement quality, so this codebook replaces it with a
procedure.

---

## 1. What the gold standard is, and what it is not

It **is** a set of values, drawn from the extracted records, whose true value has
been established by a human reading the source paper, with the evidence span
recorded.

It **is not** a re-extraction by a human. The annotator's job is to determine
*what the paper actually says*, not *what a good extractor would output*.

**150–200 annotated values, for the BDD domain only.** Values, not records: a record with six
variables contributes six values, each annotated independently. This matters because extraction
uncertainty is a per-value property — annotating at record level would destroy the pairing the
analysis depends on. The perovskite domain is validated against an independently curated external
database instead; see section 7.

## 2. Sampling strategy

Stratified, not random. A purely random sample of values would be dominated by
easy, clearly stated numbers and would under-represent exactly the cases the
paper is about. Strata:

| Stratum | Target share | Rationale |
|---|---|---|
| High composite uncertainty | 35% | the cases the metric flags |
| Low composite uncertainty | 35% | needed to estimate the *bottom* of the calibration curve |
| Prose-embedded | 20% | Gap 3; must be present in the gold standard or Gap 3 cannot be evaluated |
| Range / series / derived values | 10% | the structurally hardest cases |

**Oversampling high-uncertainty values biases the error rate upward.** That is
acceptable and expected — the gold standard is for estimating the *relationship*
between uncertainty and error, not the marginal error rate. State this
explicitly in the paper and report the marginal error rate separately from the
full extracted corpus, where no such oversampling applies.

---

## 3. Correctness rules

A value is **correct** if all of the following hold:

1. **Value.** It matches the source within the variable's stated tolerance
   (numeric: relative error ≤ 1%; or exact for integer counts).
2. **Unit.** The normalised value is right *after* a correct conversion. A right
   number with a wrong unit is `wrong_unit` and is **not** correct.
3. **Variable.** The value answers the variable that was asked. A correct number
   attached to the wrong variable is `wrong_variable` and is **not** correct.
4. **Scope.** For a range or series, the extracted value must not silently
   collapse it. Reporting the midpoint of "12–18 h" as `15` is
   `collapsed_range`, not correct.

Rounding: accept the value as reported in the source. Do not require the annotator
to recompute. If the source reports "≈1.2 A/cm²", both `1.2` and `1.20` are
correct.

## 4. Error taxonomy

Must match the `error_type` enum in `extraction_schema.json` exactly:

`none`, `wrong_value`, `wrong_unit`, `wrong_scale`, `collapsed_range`,
`wrong_variable`, `hallucinated`, `missed`, `ambiguous_source`.

Two of these carry most of the theoretical weight:

- **`ambiguous_source`** — the paper genuinely does not pin the value down. This
  is *aleatoric* uncertainty in the source text. A good uncertainty metric
  **should** flag these.
- **`hallucinated` / `wrong_value`** — the paper states the value clearly and the
  extractor got it wrong anyway. This is *epistemic*. A good metric should also
  flag these, but the mechanism is different.

**Record these separately.** If the uncertainty metric turns out to track
`ambiguous_source` but not `hallucinated`, that is a substantive finding about
what self-consistency dispersion measures — and it is exactly the kind of result
that makes the paper worth reading. Collapsing the taxonomy into a binary
right/wrong flag would destroy it.

---

## 5. Dual annotation and agreement

- A **second annotator**, independent of the first, codes a random **25 %** of
  the gold-standard values. The random seed is recorded.
- Annotators work **blinded to the model's uncertainty value and to the other
  annotator's decision.** Blinding is not optional: an annotator who can see that
  the metric flagged a value as uncertain will tend to find it ambiguous. This
  would manufacture the correlation the paper is testing.
- **Cohen's κ** is reported on: (a) the binary correct/incorrect decision and
  (b) the error-type label. Both, separately — agreement on the binary decision
  can be high while agreement on *why* it is wrong is poor, and the taxonomy is
  where the interesting result lives.
- **Target κ ≥ 0.70.** If κ falls below 0.70, the codebook is revised and the
  contested strata are re-annotated. A κ below 0.70 means the gold standard is
  not a standard.
- **Disagreements are adjudicated** by a third person, and the **adjudication
  rate is reported**. A high adjudication rate is itself a limitation and belongs
  in the paper.

If no third person is available, the two annotators must resolve by consensus
with the disagreement, the resolution, and the reasoning all recorded. Report
that the adjudicator was not independent.

---

## 6. Worked boundary cases

These are the cases where annotators will drift apart if left to judgment. Fix
them in the codebook now, before annotation starts.

| Case | Ruling |
|---|---|
| Value given only in a figure, not in text or caption | `missed` if not extracted; annotate from the figure only if the figure is legible. Record that the value is figure-only. |
| Value in supplementary material only | Out of scope unless the paper's main text refers to it numerically. |
| Same quantity reported twice with different values (e.g. abstract vs. results) | The **results section** governs. Record both in `notes`. |
| Percentage reported as a fraction ("0.95" for 95 %) | Correct if the normalised value is right. Report as `wrong_scale` only if normalisation was not applied. |
| Value stated for a *different* sample/condition than the extracted record | `wrong_variable` or `hallucinated` depending on whether the number appears in the source at all. |
| "Not reported" | `missed` — a null extraction of a value that does exist is an error, not a null. |
| Value genuinely absent from the paper | `none`. The extractor's `null` is correct. |

---

## 7. Domain 2 does not use this codebook — and that is the point

Domain 2 (halide perovskites) is validated against the **Perovskite Database**, an independently
curated FAIR resource. The gold standard there is external, so sections 2–6 of this codebook apply to
BDD only.

**Why this is a strength, not an omission.** The single largest threat to this study was that its
gold standard would be our own annotation, judged by us, with our own error taxonomy — which is
exactly the circularity the paper criticises in the extraction literature. An external database breaks
that circle. It also means the perovskite validity check (RQ2) does not depend on human coding effort
at all.

**But it introduces a failure mode with no analogue in BDD: the match.** With an external gold
standard the error can enter through *linking an extracted device to a database record*, not through
extraction. Concretely: a paper reports two devices with the same absorber composition and different
efficiencies, and a silent wrong link then scores as an extraction error. That failure is invisible
from the extraction side.

Mandatory controls, all recorded in the schema's `database_match` block:

1. Match on DOI **and** absorber composition first; fall back to composition plus reported PCE.
2. Record `match_method`, `match_confidence` and `candidate_count` on every perovskite record.
3. Hand-verify a random sample of **30 matches** against the source paper before the pipeline runs.
4. **Report the unmatched and ambiguous rates as headline numbers.** If the ambiguous rate exceeds
   10 %, revise the matching rule before analysing any extraction result.

Note also that the Perovskite Database is community-curated and not infallible. Where a database value
disagrees with the source paper, the **paper governs** and the disagreement is logged — because the
gold standard must be the scientific record, not the database's transcription of it.

Finally, the two domains are **not** pooled for the accuracy estimate. BDD accuracy is measured
against hand annotation and perovskite accuracy against a database; pooling them would report an
average of two different measurement procedures, which is meaningless. Report them side by side and
state the difference explicitly.

## 8. Deliverables

| Artifact | Contents |
|---|---|
| `gold/gold_standard.csv` | one row per value: `record_id`, `variable`, `gold_value`, `error_type`, `evidence_span`, `stratum` |
| `gold/dual_coding.csv` | the 25 % subsample with both annotators' labels, blinded order |
| `gold/agreement.json` | Cohen's κ (binary and taxonomy), adjudication rate, confusion matrix |
| `gold/codebook_changelog.md` | every codebook revision, with the case that forced it |

The changelog is required. If the codebook was amended mid-annotation, the
paper must disclose it, and the changelog is the cheapest honest way to do so.
