# Fieldwork 2 — Perovskite Database linkage check

**Purpose.** Verify, by hand and before anything is frozen, that the Perovskite Database can actually
support **per-value** validation for Domain 2. The database's existence is confirmed
(Jacobsson et al., *Nature Energy*, 2022; perovskitedatabase.com). Its **usability as a gold standard
for this specific study** is not, and the entire Domain 2 plan depends on it.

**Do this before the PRISMA search is frozen.** If the linkage is too weak, Domain 2 reverts to a
hand-annotated gold standard, the corpus-cost estimate changes, and that decision must be taken before
screening rather than after.

---

## Why this check exists

With a hand-built gold standard, the error can only enter through annotation. With an external
database, it can enter through **matching** — and matching failure is invisible from the extraction
side. A wrong match is scored as an extraction error against the pipeline, and the pipeline is then
penalised for the curator's ambiguity. That is a silent corruption of the study's central
measurement.

So the question is not "does the database exist". It is: **can a value extracted from a given paper be
tied to a specific database record, unambiguously, often enough to be useful?**

---

## Step 1 — obtain a real record and its paper

1. Open perovskitedatabase.com and export a small sample — 20 records is enough, 50 is better.
2. Filter to records from **2018 or later** with a DOI present. Older or DOI-less records are not
   usable, because the paper cannot be retrieved.
3. For each record, retrieve the paper.

**Record immediately:** what fraction of the export has a DOI? **If under ~70 % of recent records
carry a DOI, the linkage is too weak and Domain 2 must be re-planned.** That single number is the
go/no-go.

| Metric | Value |
|---|---|
| Records in export | |
| Records with DOI | |
| DOI coverage % | |
| Records 2018+ | |
| Records 2018+ with DOI | |

## Step 2 — attempt the per-value match by hand

For **20 records**, do the following, reading the paper as a scientist would.

1. From the database record, note the values it asserts: composition, PCE, Voc, Jsc, FF, architecture.
2. Find those values in the paper. **Note whether each was in a table, in prose, or only in a figure.**
3. Score the match:

| Column | Values |
|---|---|
| `db_record_id` | database key |
| `doi` | |
| `paper_reports_value_in` | table / prose / figure / absent |
| `match_method` | doi_and_composition / doi_only / composition_and_pce / unmatched |
| `match_confidence` | exact / probable / ambiguous / failed |
| `candidate_count` | how many database records could plausibly correspond to this paper's device |
| `ambiguous_reason` | free text — e.g. "two devices, same composition, PCE 21.3 and 19.8" |

### The cases that matter most

Watch specifically for these, because each one breaks the naive matching rule:

- **Multiple devices per paper.** Very common in perovskite work. If the database keys on device and
  the paper reports several, `doi_only` matching is wrong by construction.
- **Champion versus average.** A paper may report a best-cell PCE in the abstract and a distribution
  in the results. The database picks one; which?
- **Same composition, different stack.** Matching on composition alone will collide.
- **Stability values.** `T80` is frequently reported differently across the paper and its SI, or
  defined differently (T80 vs T90 vs "retained 80 % after X h"). Expect the worst agreement here.
- **Unit and reference ambiguity.** Efficiency under reverse scan vs forward scan; stabilised vs
  scanned. The database records one convention; the paper may report both.

## Step 3 — compute the three rates that decide the plan

```
doi_coverage        = records_with_doi / records_sampled
matchable_rate      = (exact + probable) / sampled
ambiguous_rate      = ambiguous / sampled
```

### Decision rule — fix this now, before looking

| Outcome | Action |
|---|---|
| `doi_coverage ≥ 0.7` and `ambiguous_rate ≤ 0.10` | Domain 2 proceeds as planned. Per-value validation against the database is viable. |
| `ambiguous_rate` in 0.10–0.25 | Proceed, but restrict to **single-device papers** or to a fixed matching rule decided in advance, and report the ambiguous rate prominently as a limitation. |
| `ambiguous_rate > 0.25` | The database cannot serve as a per-value gold standard. Domain 2 reverts to hand annotation, and the corpus plan is revised to reflect the added cost. |
| `doi_coverage < 0.7` | Linkage too weak. Re-plan Domain 2 entirely. |

## Step 4 — confirm licence, export and reproducibility

- **Licence.** Confirm that redistribution of a derived validation set is permitted. If not, the
  released artifact is the matching script and the DOI list, not the values.
- **Export format and version.** Record the CSV/JSON format and the database version or access date.
  A gold standard that changes under you is not a gold standard.
- **Stability of the record.** Re-export the same 20 records after two weeks and diff them. If curated
  values change, say so in the paper — and pin the version used.

## Step 5 — write down what the database is not

The Perovskite Database is **community-curated**, not experimentally verified, and it was built for a
different purpose than validating an extraction pipeline. Two consequences must appear in the paper:

1. Where a database value disagrees with the source paper, **the paper governs**, and the
   disagreement is logged as a database issue rather than an extraction error.
2. The database's own curation process has its own error rate, which is unknown to us and is therefore
   a floor on the measured extraction accuracy for Domain 2. State that floor explicitly rather than
   presenting the measured accuracy as if the gold standard were infallible.

---

## Deliverable

A short memo with: the four coverage/matching rates, the decision-rule outcome, the licence and version
details, and the list of ambiguous cases with their reasons. **One to two days.** It converts Domain 2
from an assumption into a verified plan — or kills it before months are spent on it.
