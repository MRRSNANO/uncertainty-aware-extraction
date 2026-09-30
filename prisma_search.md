# Stage 1 — corpus construction and PRISMA protocol

This document fixes the search, screening and inclusion rules **before** the
search runs, so that the corpus size cannot be quietly adjusted after seeing
which way the results point. That discipline is the reason the study can claim
pre-registration at all.

---

## 1. Databases and date range

| Source | Use |
|---|---|
| Scopus | primary structured search |
| Web of Science Core Collection | independent primary search; disagreement between the two is reported |
| ScienceDirect | full-text access for screening |
| Google Scholar | backward/forward snowballing only; never for the primary count |
| Publisher sites | full text where not open access |

**Date range: 2015-01-01 to the search execution date.** Earlier work is
reachable through snowballing, which is reported separately from the structured
search so the two counts are never conflated.

Record the **exact execution date** of every search. A PRISMA count without a date
is not reproducible.

---

## 2. Domain 1 — boron-doped diamond (BDD) electrodes

**Block A (material):**
`("boron-doped diamond" OR "boron doped diamond" OR "BDD electrode" OR "BDD anode" OR "boron-doped diamond electrode")`

**Block B (characterisation):**
`(Raman OR "sp3/sp2" OR "sp2/sp3" OR "doping level" OR "boron concentration")`

**Block C (outcome):**
`("critical current density" OR "Faradaic efficiency" OR "service life" OR "electrode lifetime" OR delamination OR "current efficiency" OR "cell voltage")`

**Query:** `A AND B AND C`, limited to the date range, document type = Article or
Review, language = English.

### Inclusion criteria
1. Peer-reviewed journal article.
2. Reports Raman-derived doping or sp³/sp² information.
3. Reports at least one quantitative performance or failure outcome.
4. Names the substrate (Ti, Nb, Ta, Si, W, Mo).

### Exclusion criteria
- Conference abstracts, theses, patents, editorials.
- BDD used only as a purchased commercial electrode with no deposition or
  characterisation data (no substrate, no Raman).
- Values reported only graphically in a figure with no numeric label.

---

## 3. Domain 2 — halide perovskite solar cells (SUBSTITUTED)

The original Domain 2 (PVDF / hydroxyapatite membranes) was **removed on feasibility grounds**: a live
OpenAlex count returns 122 works total and 90 journal articles for
`(PVDF OR polyvinylidene fluoride) AND hydroxyapatite`, the largest venue holds five papers, and
*Journal of Membrane Science*, *Desalination* and *Separation and Purification Technology* do not
appear in the top forty venues at all. A literature ceiling cannot be fixed by effort; see the
proposal's Stage 1 for the full reasoning.

**Block A (absorber):** `("perovskite solar cell" OR "perovskite solar cells" OR "halide perovskite" OR "perovskite photovoltaic")`

**Block B (device metric):** `("power conversion efficiency" OR "fill factor" OR "open-circuit voltage" OR "short-circuit current")`

**Block C (device stack):** `("electron transport layer" OR "hole transport layer" OR mesoporous OR planar)`

**Query:** `A AND B`, optionally `AND C`, with the same limits as Domain 1.

### Inclusion criteria
1. Peer-reviewed journal article.
2. Reports a device-level power conversion efficiency together with at least two of
   {Voc, Jsc, FF}.
3. Names the absorber composition.

### Exclusion criteria
- Tandem or multi-junction devices where the perovskite sub-cell is not separately reported.
- Efficiency claimed as a record with no device parameters reported.
- Values reported only graphically, with no numeric label.

### The decisive difference from Domain 1 — an external gold standard

Records in this domain are matched against the **Perovskite Database** (Jacobsson et al.,
*Nature Energy*, 2022). This changes what the gold standard *is*, and it moves the principal error risk
from extraction to **matching**. Two consequences follow, and both are protocol requirements rather
than preferences.

1. **Matching is where validation can silently fail.** A paper reporting two devices with the same
   absorber composition and different efficiencies will match ambiguously, and a silent wrong match is
   then scored as an extraction error against the pipeline. That failure is invisible from the
   extraction side, and it would corrupt the study's central measurement. Match on DOI **and**
   composition first, then on composition plus reported PCE, and record `match_method`,
   `match_confidence` and `candidate_count` in every record — the schema enforces these fields.
2. **Report the unmatched and ambiguous rates prominently**, as headline numbers rather than
   footnotes. If the ambiguous rate exceeds 10 %, the matching rule is revised **before** any
   extraction result is analysed. A random sample of 30 matches is verified by hand against the
   source paper before the pipeline runs at all.

---

## 4. Screening procedure

**Two independent screeners** at both stages. Reviewers do not screen papers on
which they are authors.

**Stage 1 — title and abstract.** Screeners mark include / exclude / maybe, with
an exclusion reason code. Both screeners screen **all** records.

**Stage 2 — full text.** Only records passing Stage 1. Both screeners screen all
records that Stage 1 did not unanimously exclude.

**Agreement.** Cohen's κ on the Stage 1 decision is reported. If κ < 0.70, the
criteria are revised and the screening restarts — a low κ at screening means the
inclusion criteria are not operational, and a corpus built on ambiguous criteria
cannot support a claim about extraction difficulty.

**Conflicts** are resolved by the third person, and the conflict rate is reported.

## 5. PRISMA flow — the numbers that must be recorded

Every one of these is a required number in the paper's flow diagram. Do not
summarise; the point of PRISMA is that a reader can reproduce the funnel.

```
records identified (Scopus)                    = ___
records identified (Web of Science)            = ___
duplicates removed                             = ___
records screened (title/abstract)              = ___
  excluded at title/abstract                   = ___   (by reason code)
  ── reason codes: not BDD/perovskite, no device metric, no absorber composition, wrong type
full texts assessed                            = ___
  excluded at full text                        = ___   (by reason code)
  ── reason codes: no Raman/sp3, single characterisation modality,
                    no substrate named, values figure-only, no full text
studies included (structured search)           = ___
studies added by backward snowballing          = ___
studies added by forward snowballing           = ___
studies included (final)                       = ___
usable records extracted                       = ___
records lost to gold-standard verification     = ___
```

**Track two different quantities and never conflate them:**

- **studies included** — how many papers,
- **usable records** — how many extractable rows. One paper can yield several
  records (multiple substrates, multiple conditions), and the causal analysis
  needs records, not papers.

The Stage 0 power analysis sets the **record** target. If the funnel yields fewer
records than the target, that is the trigger for Plan B (single-domain reframing),
and the decision must be taken **before Stage 4 begins** — exactly as the original
proposal's feasibility statement required.

---

## 6. Snowballing

Backward (reference lists of included studies) and forward (citing articles) from
the included set, one iteration only. Same inclusion criteria. Report counts
separately from the structured search so that the contribution of snowballing to
the final corpus is visible.

---

## 7. Data management

- One row per screened record in a screening log: `record_id`, `source_db`,
  `doi`, `screener_id`, `stage`, `decision`, `reason_code`, `timestamp`.
- Full texts stored locally, named by `record_id`, never by title.
- The screening log is a deliverable. It is the only way a reader can audit the
  corpus, and it is cheap to produce if it is produced from the start rather
  than reconstructed afterwards.

## 8. What must be decided before this protocol runs

Three items are still open. **All three block Stage 1.**

1. **Who performs the dual screening**, and who is the third adjudicator. Two people minimum; three
   for adjudication as specified. This is not administrative: without a second screener there is no κ,
   and without κ the gold standard's validity claim — which the whole paper rests on — is unsupported.
2. **Corpus target in records**, which comes out of the Stage 0 power analysis
   (`stage0/analysis.py` prints it). Do not start screening until that number exists, because it
   determines whether the inclusion criteria need widening, and widening them after screening has
   begun is not defensible.
3. **Confirm Perovskite Database access before Domain 2 is committed.** The database's existence is
   verified (Jacobsson et al., *Nature Energy*, 2022; perovskitedatabase.com), but its **export
   interface, licence, and the exact record-to-paper linkage** have not been inspected, and the device
   count is currently a second-hand figure. Retrieve one real record and match it to its paper by hand
   before the protocol is frozen. If the linkage turns out to be too weak to support per-value
   matching, Domain 2 reverts to a hand-annotated gold standard and the corpus-cost estimate changes
   accordingly — which is a decision that must be taken before screening, not after.

### One prior action that is cheap and determines the whole corpus plan

Run the four BDD substrate queries (Ti, Nb, Ta, Si) and hand-sample roughly thirty hits each to measure
the true conjunction rate between "BDD on a named substrate" and "reports Raman-derived sp³/sp² data".
The literature ceiling for Domain 1 is currently estimated at **60–120 records** on the strength of
`"boron-doped diamond" AND "titanium"` returning only 128 articles — and that 128 is an upper bound,
since it also matches papers that merely compare BDD against Ti₄O₇ anodes. **One afternoon of manual
sampling decides whether Domain 1 targets 100 records or 60**, and that number is an input to the
power analysis rather than an output of it.
