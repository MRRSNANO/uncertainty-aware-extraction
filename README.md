# Uncertainty-aware extraction to causal reliability

Working repository for a study on whether per-value **extraction** uncertainty predicts damage to a
downstream **causal** inference built on the extracted data, calibrated against known ground truth
before being applied to real literature.

Target venues, in order: *Patterns* (Cell Press), *npj Computational Materials*, *Journal of
Cheminformatics*, *Digital Discovery*, *JCIM*. See [the proposal's section 10](Proposal-v2-Simulation-Calibrated.md)
for the measured journal metrics and why the absolute global top ten is not a reachable target.

---

## Status

| Component | State | Verified |
|---|---|---|
| [Proposal v2.3](Proposal-v2-Simulation-Calibrated.md) | Complete: 13 sections, 34 references, no placeholders | By inspection |
| Literature: uncertainty in LLM extraction | Complete | 2 items confirmed directly, 7 pending second confirmation |
| Literature: measurement error in causal discovery | Complete | 2 items confirmed directly, 7 pending |
| Literature: domain feasibility | Complete | All counts from live OpenAlex queries |
| [`protocol/`](protocol/prisma_search.md) | Complete, aligned to the substituted domain | By inspection |
| [`fieldwork/`](fieldwork/README.md) | Ready to execute by hand | — |
| [`stage0/`](stage0/README.md) | Written | **Never executed** |
| [`extraction/`](extraction/README.md) | **Complete** — provider adapters, the runner, validation, and an end-to-end smoke test | **Never executed** |
| [`analysis/`](analysis/README.md) | **Complete** — RQ2, RQ8, cross-domain, and the RQ4/RQ5 causal driver | **Never executed** |
| [`manuscript/`](manuscript/manuscript.md) | Draft v0.1: Introduction, Related Work and Methods complete; Results and Discussion structured with placeholders | By inspection |

**No code in this repository has ever been run.** The sandbox has no working shell, so there is no
Python interpreter. Every module ships with a self test, and the first execution of each is itself a
deliverable rather than a formality — the inspection-only review has already caught two substantive
errors (below).

---

## Eight errors caught without running anything

This code has never been executed. Everything below was found by reading it, and each entry is the
argument for running the self tests before trusting a number.

**Wrong answers, dressed as plausible ones**

1. **The epistemic term had the wrong sign.** Computed as `inter − intra`; the term must be large when
   a model agrees with itself and disagrees with its peers. Written backwards it fires on well-agreed
   values and stays silent on confident mode collapse — the exact failure it exists to detect, and
   **nothing in the output would have looked suspicious**.
2. **Varsortability in the Stage 0 simulation.** Random edge weights with fixed noise variance leave
   effect sizes uncontrolled and make the generator varsortable, so every Structural Hamming Distance
   would have been uninterpretable and a continuous learner could appear to succeed by sorting
   variances. Fixed by standardized SEMs with the property asserted at run time.
3. **Signals on incomparable scales were averaged raw.** CV is unbounded, token entropy is in nats,
   and the epistemic term lives in `[-1, 1]`, so whichever had the widest range would dominate — and
   which one that was varies by domain and variable type rather than being a modelling choice. A
   correct-looking number attributed to the wrong cause.

**Code that exists but does not do anything**

4. **A deleted `@check` decorator.** A test that reported success **because it never ran**.
5. **`np.math.erf`, removed in NumPy 2.0.** On the no-SciPy fallback path, which is the path this
   environment takes, so the power analysis would have crashed on the first run.
6. **`responsiveness_check` was defined and never called.** The third integrity anchor was dead code,
   so an inert mode-collapse axis would have passed unnoticed and every RQ8 number derived from it
   would have been meaningless.
7. **A component key mismatch.** The extractor writes `cross_model_agreement`; the normalisation pass
   writes `epistemic`; the RQ8 diagnostic read only the latter from the raw components. The
   cross-model catch rate — the most important output of that diagnostic — would have been `NaN`
   forever, with no error raised anywhere.
8. **A relative import that only works inside a package.** `stage0/impact.py` had
   `from .discovery import shd`, which raises "attempted relative import with no known parent package"
   whenever the module is reached as a script — and **every** entry point in this repository reaches it
   that way. Worse, `analysis/causal.py` wraps its imports in `try/except ImportError`, so it would
   have reported *causal-learn is missing* while the real fault was an import statement. A misleading
   error is worse than a crash. Now pinned by a top-level-import check in all three self tests.

**The pattern is worth naming.** Items 5–8 are not wrong answers; they are *absent* ones — a crash, a
check that never runs, a statistic that is silently `NaN`, an import that cannot load. A reader
skimming results would not notice, and a test suite that only asserts "no exception" would not catch
them either. That is why the self tests assert **directional** behaviour (AUC above chance on
constructed data, a planted variance component recovered, a known sign) rather than merely that
functions return.

---

## Document map

```
Proposal-v2-Simulation-Calibrated.md      the study, complete
uncertainty_llm_extraction_literature.md  full literature report (730 lines)
feasibility-assessment.md                 domain feasibility report (246 lines)

protocol/       what the study must do, fixed before data collection
  extraction_schema.json      record schema, two controlled vocabularies
  prompts_and_uncertainty.md  paraphrase set, the three signals, calibration, RQ7/RQ8
  annotation_codebook.md      gold standard, error taxonomy, dual coding, kappa
  prisma_search.md            search strings, inclusion rules, PRISMA counts

fieldwork/      manual tasks that need no code and can start today
  bdd_substrate_sampling.md       measures the Domain 1 record ceiling (~1 day)
  perovskite_matching_checklist.md verifies the external gold standard (1-2 days)
  variance_decomposition_pilot.md  measures where the extraction variance is

stage0/         simulation calibration -> sets the corpus target
  core.py         standardized SEM, error injection, mode-collapse regime
  discovery.py    causal-learn wrappers, SHD, edge stability
  impact.py       per-record causal impact, high/low contrast, placebo test
  power.py        power analysis
  run_stage0.py   resumable design-grid driver
  analysis.py     aggregation, integrity anchors, mode-collapse price list
  selftest.py     run this first

extraction/     the measurement instrument
  uncertainty.py     signals A/B/C, composite, split conformal, isotonic
  variance.py        variance decomposition, paper-level bootstrap, decision rule
  adapters.py        provider-neutral clients, offline replay
  run_extraction.py  the runner: prompts, attempts, signals, records, resumable writer
  validate.py        schema validation, structural and semantic
  selftest.py        unit checks; NumPy alone
  smoke_test.py      end-to-end chain with a scripted model; NumPy alone

analysis/       results
  empirical.py    RQ2, RQ8, calibration, cluster bootstrap, cross-domain
  causal.py       Stage 4-6 driver: RQ4, RQ5, baselines, null tests
  selftest.py     units and directional checks; causal checks skip loudly

manuscript/     the paper itself
  manuscript.md   draft v0.1; Methods complete, Results mapped to code outputs
```

## Pipeline

```
fieldwork/   measure the literature ceiling and the variance budget (manual, no code)
     |
stage0/      simulate with known ground truth -> power analysis -> corpus target
     |
protocol/    freeze search, prompts, schema and codebook before collecting anything
     |
extraction/  run extraction, quantify uncertainty, validate records
     |
analysis/    RQ2 (does the metric work), RQ8 (mode collapse), RQ4-RQ6 (causal impact)
     |
manuscript/  drafted a section ahead of each stage, so results are dropped into
             a fixed structure rather than the structure being written around them
```

## Dependencies

```
numpy>=1.22         # everything
scipy>=1.9          # the analytic Fisher-z power column; other statistics fall back
causal-learn>=0.1.3 # BLOCKING: PC/GES and the official SHD implementation
jsonschema>=4.0     # structural record validation; the semantic layer runs without it
```

Nothing else. No paid software, no specialised hardware, no laboratory access.

### ⚠ Known gap in the bundled runtime

The Python shipped with this environment has `numpy 2.3.5`, `pandas 3.0.1`, `python-docx` 1.2.0 and
`openpyxl`, but **not `scipy`** and **not `causal-learn`**. The consequence is specific: **Stage 0
cannot run even once the shell works**, because `discovery.py` imports causal-learn for PC/GES and for
the official SHD implementation, and `impact.py` imports `discovery`. The self tests are written to
report this as a failure rather than to paper over it.

`extraction/` and `analysis/` need only NumPy, so they are runnable the moment a shell exists.

**Run this first once a shell exists:**

```bash
python check_environment.py
```

It prints the interpreter, every dependency with its version, what is missing, **what each gap
blocks**, and the exact install command. A failed first run should produce a fix, not a stack trace.

## The three open blockers

Every one of these needs a decision, not more work.

1. **Shell access.** The session workspace is on a removable drive whose permissions the sandbox cannot
   provision (`SetNamedSecurityInfoW failed, Win32 5`), so no command runs. Two fixes: reopen the
   session with the workspace set to a local NTFS folder, or switch the session to full access.
   **Until this is resolved the power analysis cannot run, and every Stage 0 number is pending.**

2. **People.** The screening protocol needs two independent screeners and a third adjudicator; the BDD
   gold standard needs a second annotator. Without them there is no Cohen's κ — and without κ the gold
   standard's validity claim, which the entire paper rests on, is unsupported. This has been raised
   five times and is still unanswered.

3. **Model provider.** Three instruction-tuned models from independent families, hosted or local. The
   epistemic term is defined over an ensemble, so this is not a convenience choice. It gates the
   extraction runner.

## The cheapest useful next action

Not blocked by any of the three. Run the four BDD substrate queries (Ti, Nb, Ta, Si), hand-sample
thirty hits each, and score the four inclusion flags. **One working day.** It produces the Domain 1
record ceiling, which decides whether the corpus plan is viable — and that number is an **input** to the
power analysis, not an output of it. Templates are in
[`fieldwork/bdd_substrate_sampling.md`](fieldwork/bdd_substrate_sampling.md).

## A note on how this document set is written

Claims are labelled by how they were verified. Items marked **verified directly** were read against the
publisher or repository record by the author of this repository. Items marked as pending a second
confirmation were returned by a search agent with a URL but not re-fetched, and **must not appear in a
submitted manuscript until they are**. Where verification failed, the item is omitted rather than
approximated — two papers that match this study's method closely are quarantined in the appendix
rather than cited on the strength of a title.

Novelty claims have been withdrawn three times as prior work was located, and the empirical domain pair
was substituted once when the literature ceiling proved immovable. Both are recorded in the proposal's
Appendix B. A study that keeps its original novelty claim after three searches is not a study that was
looking.
