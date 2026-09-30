# From Extraction Confidence to Causal Reliability
## A Simulation-Calibrated Framework for Uncertainty Propagation in LLM-Based Scientific Knowledge Extraction

**Version 2 — restructured proposal**
Status: working draft, v2.3. The three systematic literature searches are complete. The novelty
statement has been rewritten three times as prior work was located, and the empirical domain pair has
been substituted once on feasibility grounds. Claims marked **verified directly** were checked against
the publisher or repository record by the author of this document; items in the Appendix marked as
pending a second confirmation were not, and must not appear in a submitted manuscript until they are.

---

## Abstract

Large language models (LLMs) can now extract quantitative data from scientific literature at high
accuracy on structured tables, yet three gaps persist. First, extraction quality is evaluated in
isolation by precision/recall/F1, with no reference to whether an extraction error changes any
downstream conclusion. Second, extraction uncertainty is discarded: once a value enters a database it
is treated as ground truth, so the reliability of a downstream statistical or causal claim is
disconnected from the reliability of its inputs. Third, narrative prose — where performance values,
service lifetimes and failure thresholds are frequently reported — remains largely inaccessible to
automated pipelines.

This proposal develops an uncertainty-aware extraction-to-causal framework that (i) quantifies
per-value extraction uncertainty from three independent signals, (ii) propagates that uncertainty
into causal structure learning through confidence-weighted resampling, and (iii) evaluates extraction
quality by a new criterion — **the causal impact of extraction error**, defined as the per-record
Structural Hamming Distance induced by correcting that record. Crucially, the framework is first
**calibrated on synthetic data with known ground-truth causal structure and controlled error
injection**, which (a) establishes the attainable ceiling of any uncertainty metric, (b) yields a
power analysis that determines the corpus size the empirical study actually requires, and (c)
produces a calibration curve mapping observed uncertainty to expected structural change. The
calibrated framework is then applied across two structurally dissimilar domains — boron-doped
diamond (BDD) electrodes, whose decisive values are largely figure- and prose-bound, and halide
perovskite photovoltaics, whose values are tabulated and for which an independently curated FAIR
database supplies an external ground truth. Hypotheses are pre-registered and all outcomes, including
null results, are designed to be publishable.

---

## 1. Introduction and Research Gap

The exponential growth of scientific literature has created a bottleneck in evidence synthesis: the
accumulated knowledge in any specialised field now exceeds what an individual researcher can manually
integrate. Automated extraction using LLMs has emerged as a response. MaTableGPT demonstrated that
structured tabular data can be extracted from materials science literature at F1 approaching 97% in
water-splitting catalysis, and parallel work has extended extraction to multi-element tabular data in
polymer property literature.

Three limitations persist across this body of work.

**Gap 1 — Evaluation is disconnected from use.** Existing systems report precision, recall and F1
against a gold-standard subset. They do not ask whether an error matters. An error that leaves every
downstream conclusion unchanged is scored identically to an error that reverses a causal conclusion.
No existing framework quantifies this task-dependent impact.

**Gap 2 — Extraction uncertainty is not propagated.** Extracted values are treated as ground truth
once written to the database, even though the extraction process may return different values under
different prompt formulations, and even though some values are inherently more ambiguous in the
source text than others. The reliability of a downstream statistical or causal claim is therefore
disconnected from the reliability of its inputs.

**Gap 3 — Narrative text is largely excluded.** The dominant application domain — structured tabular
data — excludes a substantial fraction of scientific knowledge that appears only in narrative prose.

This proposal addresses all three gaps in a single integrated framework, and adds a fourth element
that the earlier version of this proposal lacked and that reviewers would certainly have demanded:
**the framework is calibrated against known ground truth before it is applied to real literature.**

---

## 2. Related Work

This section is written *against* the proposal's own novelty claim rather than in support of it. Where
prior work anticipates a contribution, that is said plainly and the contribution is narrowed
accordingly. Three strands that were expected to support the proposal turned out to constrain it, and
the novelty statement at the end of this section is materially narrower than the original.

**2.1 LLM-based extraction from scientific literature.** The field moved from rule-based pipelines —
ChemDataExtractor and its successor — to LLM-based extraction, and reported accuracies are now high.
MaTableGPT reports F1 near 97 % on structured tables from materials-science literature; Polak &
Morgan's ChatExtract reports roughly 90 % precision and recall; Dagdelen et al. (2024, *Nature
Communications*) is the canonical demonstration of structured extraction at scale. Two facts about
this literature matter here.

First, **accuracy is measured in isolation.** Every system above is scored by precision, recall and F1
against a gold subset, and none asks whether an extraction error changes any downstream conclusion.
That is Gap 1, and it survives this literature.

Second, **none of it addresses uncertainty.** Dagdelen et al. do not quantify extraction confidence at
all. That is a real gap, not merely an unexamined one.

**The one place the proposal is *not* first.** Khalighinejad et al. (2024, Findings of ACL) already
apply self-consistency to full-document extraction in materials and polymer literature. So
"self-consistency for scientific extraction" is prior art and is not claimed. What that work does not
do — and what remains open — is propagate the resulting uncertainty into a downstream inference and
calibrate that relationship against ground truth. That distinction is the entire basis of the
contribution.

Finally, **no uncertainty-annotated benchmark for LLM scientific extraction was located.** Adjacent
assets exist — Ghosh et al. (2024, Findings of ACL) provide expert manual error analysis on two
materials datasets and are the best available vehicle — but none is annotated for uncertainty. The
absence is a defensible novelty claim, and it is also why building the gold standard is an explicitly
costed aim rather than a formality.

**2.2 Uncertainty quantification in LLM extraction.** Self-consistency originates as a *decoding*
method for accuracy (Wang et al., 2023, ICLR) and was never framed there as calibrated uncertainty.
The lineage that treats sampling as an uncertainty signal is semantic entropy (Kuhn, Gal & Farquhar,
2023, ICLR Spotlight) and its Nature successor (Farquhar et al., 2024), which explicitly restrict
their target to confabulations. For extraction specifically, Kim et al. (2025, AAAI Symposium Series)
is the closest published analogue to this proposal: LLM extraction with an LLM-as-judge verification
stage and conformal prediction over 10k clinical visits, describing state-of-the-art models as
"notoriously miscalibrated and overconfident." **It does not use dispersion — it uses conformal
prediction.** Xu & Lu (2025) likewise report that token-entropy measures with split conformal
calibration outperform self-consistency-based uncertainty quantification. *This strand anticipates
part of the proposal's second contribution and is cited as such; the proposal does not claim to
invent uncertainty quantification for extraction.*

**The uncertainty signal is explicitly prior art.** Paraphrase-induced variance is used as an
uncertainty measure in an independent line of work (Feng et al., 2025, Findings of EMNLP) and analysed
favourably per item by Ali (2026, EIML@ICML). **This proposal therefore makes no novelty claim over the
signal itself.** Its claim begins strictly downstream of it: what the signal *does* to a causal
inference built on the extracted data, and whether that can be calibrated against ground truth.

**The closest prior work, now read in full.** Atalkar, Sohani & Deogaonkar (2026, INSECT) introduce
**PI-EVA — Paraphrase-Induced Epistemic Variance Analysis** — which "measures epistemic uncertainty by
analyzing semantic stability ... by checking how consistent model interpretations are across different
paraphrased queries". Their Epistemic Variance Score (EVS) is a **pre-retrieval routing signal**: it
modifies planning diversity, retrieval redundancy, verification strictness and generation parameters
at query time. Evaluated on HotpotQA dev-distractor, they report an Answer F1 of 54.29 % and an EM of
44 %, with no fine-tuning or labelled data.

Three consequences, stated plainly.

1. **The signal and its use as a control input are prior art.** Nothing in our framework depends on
   being first to paraphrase, first to score dispersion, or first to act on it.
2. **Their evaluation is a downstream *task metric*, not a validity check.** PI-EVA reports that
   routing on EVS improves answer quality. It does not report whether EVS tracks actual extraction
   error, because there is no error to track in HotpotQA — the answers are known. Our RQ2 asks exactly
   that question in a setting where answers are *not* known and must be established by hand, which is
   the setting where an uncertainty metric is most needed and least verified.
3. **A terminological conflict worth resolving.** PI-EVA calls paraphrase-induced variance
   **epistemic**. Under Ali (2026), dispersion within a single model carries no cross-question
   structure; under Hamidieh et al. (2026), epistemic uncertainty is what *cross-model* disagreement
   exposes, and it is precisely the component paraphrase variance lacks. These cannot both be right as
   stated. **Our RQ8 diagnostic settles it empirically for extraction**: if dispersion collapses on
   confidently wrong values, it is not measuring what PI-EVA's name claims, and the field's naming
   should change. We therefore treat this as a contribution of the paper — a clarification of what the
   signal is, at the point where it matters — rather than as a threat to be managed.

**2.3 What sampling-based uncertainty can and cannot do.** Ali (2026, EIML@ICML) separates two
claims that are routinely conflated. Applying a Marchenko–Pastur random-matrix test across five model
families and three benchmarks, it finds that self-consistency gives **accurate per-question
uncertainty but no detectable cross-question structure**: within any single model, at most one
dimension rises above the noise edge, whereas a diverse 24-model ensemble surfaces four — against at
most one in 500 matched-difficulty Bernoulli null draws. The conclusion drawn by the authors is that
only a diverse ensemble reveals what a model does not know.

This distinction maps directly onto the present design. The proposal needs **per-value** uncertainty,
which this result supports; it does **not** need cross-question correlated-error structure, which
this result shows a single model cannot supply. The third uncertainty signal — cross-model agreement
— is therefore not redundant padding: it is the specific mechanism the literature identifies as the
only route to ensemble-level structure. Separately, Xu & Lu (2025) report that token-entropy
measures calibrated by split conformal prediction outperform self-consistency-based uncertainty
quantification. This motivates both the token-level signal (Signal B) and conformal rather than
isotonic calibration. *Together these two results define what the uncertainty instrument is
permitted to claim, and Stage 2 is built to those limits.*

**2.4 Confident mode collapse — the threat that matters most.** Hamidieh, Thost, Gerych, Yurochkin &
Ghassemi (2026, ICLR) identify a failure mode that would break the original design outright: "Recent
works routinely rely on self-consistency to estimate aleatoric uncertainty (AU), yet this proxy
**collapses when models are overconfident and produce the same incorrect answer across samples**. We
analyze this regime and show that cross-model semantic disagreement is higher on incorrect answers
precisely when AU is low." Across five 7–9B instruction-tuned models and ten long-form tasks they
define an epistemic term — the gap between inter-model and intra-model semantic similarity — and show
it "reliably flags confident failures where AU is low."

*Why this is the load-bearing threat.* If the extractor confidently returns the wrong value every
time, all N paraphrased runs agree, dispersion is zero, and the metric reports **maximum confidence
on exactly the errors that matter**. The uncertainty signal does not merely weaken; it inverts. The
mechanism is documented for aligned models generally by Xiao et al. (2025, ICML), who show
pre-trained models are well calibrated and models become poorly calibrated *after* preference
alignment — which is the class of model an extraction pipeline would use.

*Design consequence.* Two changes, both already reflected below. First, cross-model disagreement is
promoted from a supporting signal to the primary defence, computed in the EU form of Hamidieh et al.
rather than as plain agreement, because model diversity is the only axis that varies when prompt
diversity is exhausted by mode collapse. Second, **mode collapse becomes its own pre-registered
diagnostic (RQ8, Stage 5 test 4)** rather than a caveat: the study must report what fraction of
gold-standard errors were produced with near-zero dispersion. That number is a direct test of the
proposal's core measurement assumption, and a large value is a publishable negative result.

**2.5 Measurement error in causal structure learning — prior art, not a gap.** Blom, Klimovskaia,
Magliacane & Mooij (2018, UAI) "show how to obtain an upper bound for the variance of random
measurement error from the covariance matrix of measured variables and how to use this upper bound
**as a correction for constraint-based causal discovery**." That is uncertainty propagated into
inference, published in 2018. **It settles the question: the original claim that "no existing system
propagates extraction uncertainty into downstream causal inference" is false and has been removed.**
Liu, Constantinou & Guo (2022, *JMLR* 23(324)) state the same problem — measurement error "can lead to
spurious edges" — and add a post-hoc correction phase for five learners; Saeed et al. (2020, UAI) give
a method-of-moments estimator used with constraint-based discovery; Zhang et al. (2018, UAI) give
identifiability conditions.

*Consequences, stated plainly.* What remains genuinely open is narrower, and it is the only framing
that survives this literature:

1. **The error object is different.** Every work above models uncertainty as i.i.d. statistical noise
   on an otherwise measured variable — typically additive, zero-mean, homogeneous in variance. The
   error of an LLM extraction pipeline is none of those things: it is correlated across records
   through shared prompts and shared source papers, heterogeneous in variance across relations, not
   zero-mean, and reproducible only under a frozen prompt set. Whether measurement-error theory
   transfers to *that* object is an open empirical question, and it is the question Stage 0 is built
   to answer. If it does not transfer, that is the finding.
2. **The objective is different.** Liu et al. build a *correction* method: given corrupted data,
   remove spurious edges. This proposal builds a *diagnostic*: does per-value extraction uncertainty
   predict downstream causal damage, and does propagating it change the recovered structure relative
   to uniform weighting? A correction and a calibrated diagnostic are complementary. The diagnostic
   is what a practitioner needs *before* deciding whether a correction is warranted, and the
   correction literature does not supply it.
3. **The evaluation is different.** Scoring an extraction system by the per-record structural change
   its correction induces — rather than by F1 in isolation — is not present in either the extraction
   literature or the measurement-error literature as far as this search has established. This is
   stated as a claim to be confirmed by the completed systematic search, not as an assumption.

**2.6 Robustness and stability of causal discovery — and the sample-size floor.** This strand sets the
corpus target, and it does not support a small sample.

**The metrics have known limits.** Structural Hamming Distance originates with Tsamardinos, Brown &
Aliferis (2006, *Machine Learning* 65(1)) — note that the `pcalg` reference list misprints the venue as
JMLR, and that error must not be propagated. SHD counts edge insertions, deletions and flips, and
Peters & Bühlmann (2015, *Neural Computation* 27) show that **Structural Intervention Distance "differs
significantly" from SHD** because it measures closeness in terms of the causal inference statements a
graph supports. **SHD alone is therefore not evidence that a causal claim is sound**, and this proposal
reports SID alongside it. Bootstrap edge stability dates to Friedman, Goldszmidt & Wyner (UAI 1999),
whose stated motivation was precisely the low-data regime — so it is twenty-five-year-old standard
practice, not a contribution, and it cannot be used to rescue a small sample. Colombo & Maathuis (2014,
*JMLR* 15) show PC is order-dependent, so run-to-run SHD variance can be an implementation artefact
rather than a property of the data.

**The sample-size evidence is unambiguous, and it is not in the proposal's favour.** Kummerfeld,
Williams & Ma (2023) give the first power-analysis method for causal discovery, and also criticise the
prior benchmark literature for failing to control effect sizes: "without knowing the effect sizes of
the edges we can not make reliable inferences about the method's real world performance." Scheines &
Ramsey (2016) supply the concrete numbers this study must answer to: their grid begins at **n = 100**,
and at that size "the accuracy of FGES decays severely" once measurement error reaches roughly 17 %,
with orientation accuracy suffering most. Their key trade-off — that the decay slows at larger sample
sizes — means small n and measurement error **compound rather than substitute**. Kalisch & Bühlmann
(2007, *JMLR* 8) give the asymptotic condition for PC: n must grow faster than the number of nodes,
with neighbourhood sizes of lower order than n; and because PC runs conditional independence tests of
increasing order, at n = 15–25 the data is exhausted before the algorithm terminates. Every
quantitative study located begins at n = 100, and the modal regime is 1,000–5,000. **No paper was found
validating structure recovery at n = 15–25, and no numeric minimum n for PC was found at all.**

**Real-data benchmarks carry their own caveats.** The Sachs protein-signalling data is the standard
real-data benchmark, but its ground truth is a literature-curated consensus rather than experimentally
verified edges, and its interventions are assumed perfect although they have documented off-target
effects (Sinha, Tadepalli & Ramsey, 2021). CausalBench (Chevalley et al., NeurIPS 2023 D&B) finds that
"methods that use interventional information do not outperform those that only use observational data,
contrary to what is observed on synthetic benchmarks" — the same lesson the measurement-error
literature teaches: synthetic and real performance diverge.

**Two genuine gaps emerge, and both are citable.** First, no paper was found that quantifies how
unstable SHD or bootstrap edge-stability estimates are **as a function of n** — which is exactly what
Stage 0 measures. Second, and more importantly, no paper was found that applies **information-extraction
confidence** to causal structure learning: the measurement-error literature propagates *statistical*
noise, while nobody propagates *extraction* uncertainty. That is the opening, and it is narrow.

### Revised novelty statement

The original proposal claimed novelty for uncertainty propagation itself. That claim is not
defensible. The defensible claim is narrower and stronger:

> The contribution is not uncertainty propagation in the abstract, nor LLM extraction in isolation,
> but **the definition and empirical calibration of extraction quality by its causal impact**, the
> quantification of how a measurement-error model behaves when the measurement instrument is a
> language model, and a **simulation-calibrated** demonstration of whether and when uncertainty
> propagation changes downstream causal conclusions in real scientific literature.

---

## 3. Research Questions

**RQ1.** Can per-value extraction uncertainty be quantified reliably for numerical and categorical
variables drawn from narrative scientific text, using three independent signals (paraphrase
self-consistency, token-level entropy, cross-model agreement), and does a calibrated combination
outperform any single signal?

**RQ2.** Does per-value extraction uncertainty correlate with per-value extraction error against a
dual-annotated gold standard? *(Validity check for the uncertainty metric itself. If this fails, the
pipeline's central claim fails, and this is stated in advance as a possible outcome.)*

**RQ3.** *(New — Stage 0.)* Under controlled error injection into synthetic data with a known
ground-truth graph, what is the attainable ceiling of the uncertainty–error correlation, how does
Structural Hamming Distance grow as a function of injected error rate and severity, and what sample
size is required to detect an effect of |r| > 0.3 with 80% power?

**RQ4.** Does per-record extraction uncertainty predict **per-record causal impact** — the Structural
Hamming Distance induced by correcting that single record — and is that relationship stronger for
records corrected from high uncertainty than from low uncertainty?

**RQ5.** What is the association between per-record extraction uncertainty and per-edge bootstrap
stability, and does confidence-weighted resampling materially change the recovered structure
relative to uniform weighting?

**RQ6.** Does the strength of the uncertainty–instability relationship differ between BDD
electrochemistry and halide perovskite photovoltaics, and if so, can the difference be attributed to
identifiable structural properties of the data — variable density, unit homogeneity, terminological
consistency, and above all **the proportion of values that are figure-bound, prose-bound, or
tabulated**? Figure-bound extraction is the axis with the least prior benchmarking, and it is the
contrast the domain pairing was chosen to expose.

**RQ7.** *(New — variance decomposition.)* How much of the total variance in extraction output is
attributable to prompt paraphrase, to decoding stochasticity, and to model identity — and does the
N = 10 paraphrase budget spend effort on the component that actually carries the variance? This is
forced by Ẓatuchin (2026), who decomposes response variance in a different domain and finds the
paraphrase component near zero while resampling dominates, with repeats past the fifth buying
approximately 0.0003 in relative-error variance. **N must be justified by measurement on this corpus,
not asserted.** If paraphrase carries little variance on extraction tasks, the budget is reallocated
to model and decoding diversity and that reallocation is itself a reported result.

**RQ8.** *(New — mode collapse.)* Among values the gold standard marks as incorrect, what fraction
were produced with near-zero dispersion across the N paraphrases? Does the cross-model disagreement
term flag those cases where dispersion does not? This is the direct empirical test of the measurement
assumption, derived from Hamidieh et al. (2026, ICLR).

---

## 4. Methodology

### Stage 0 — Simulation-based calibration and power analysis *(NEW; the first thing to build)*

This stage is the methodological backbone and executes before any literature is read.

**Design.** Synthetic datasets are generated to mimic the statistical shape of each target domain:

| Factor | Levels |
|---|---|
| Sample size *n* | 20, 50, 100, 200, 500 |
| Variables *d* | 5, 6, 8 |
| Graph topology | random DAG (Erdős–Rényi), scale-free |
| Structural equation model | **standardized** linear Gaussian; discrete/categorical variant |
| **Standardized effect size *r*** | 0.1, 0.3, 0.5 |
| Edge density | sparse (0.2), moderate (0.4) |
| Error base rate *p* | 0, 0.05, 0.10, 0.20, 0.30 |
| Error severity | small, medium, large (numeric: relative deviation; categorical: label flip) |
| Error assignment | ambiguity-correlated, independent, and both |
| **Confident-wrong rate** | 0.0, 0.05, 0.10, 0.20 |

**Two methodological requirements the first draft of this design missed.** Kummerfeld, Williams & Ma
(2023) — the first published power-analysis method for causal discovery — show that prior simulation
studies "have not carefully controlled the causal effect sizes in their data generating models", so
reported SHD values cannot be compared to anything; and that standard random-weight DAG generators are
**varsortable**, meaning marginal variance increases along the causal order, which lets continuous
learners appear to succeed by sorting variances (Reisach, Seiler & Weichwald, NeurIPS 2021). Both are
corrected here by generating **standardized** SEMs in the manner of Kummerfeld et al.: every edge
weight is set to the same value, and independent noise variances are solved so that every variable has
marginal variance exactly 1. The edge weight then *is* the standardized effect size, and varsortability
is zero by construction. The implementation computes the population variances and the varsortability
statistic and asserts both properties rather than assuming them.

**Consequence for reporting.** Every Stage 0 SHD result is reported as a function of standardized
effect size, and never as a single number. Structural Hamming Distance is reported **alongside
Structural Intervention Distance** (Peters & Bühlmann, *Neural Computation*, 2015), which measures
closeness in terms of causal inference statements and "differs significantly" from SHD; SHD alone is
not evidence that a causal claim is sound. Bootstrap edge stability is reported as established
practice, not as a contribution — it dates to Friedman, Goldszmidt & Wyner (UAI 1999) and its original
motivation was precisely the low-data regime, so it cannot be used to rescue a small sample.

**Procedure.** For each cell of the design, with *R* ≥ 500 replications: generate ground-truth graph
→ generate clean data → inject errors → apply the full uncertainty-weighted causal pipeline → compare
recovered structures to ground truth and to the structure recovered from clean data.

**Outputs.**
1. **Attainable ceiling.** The maximum achievable correlation between a *perfect* uncertainty signal
   and actual error, as a function of *n*, *p* and severity. This bounds what the empirical study can
   possibly achieve and prevents the proposal from setting an unreachable acceptance criterion.
2. **Ground-truth causal impact curve.** SHD(clean vs. corrupted) as a function of *p* and severity.
3. **Power analysis.** Minimum *n* required to detect |r| > 0.3 with 80% power at α = 0.05, for
   per-record causal impact and for per-edge stability. **This number sets the corpus target in
   Stage 1 and replaces the guessed criterion in the original proposal.**
4. **Calibration curve.** A mapping from observed uncertainty to expected structural change, which
   the empirical study then tests against.

**Why this stage is non-negotiable.** With the originally planned n = 15–25 records, the correlation
between uncertainty and edge stability cannot be estimated with usable precision, and the proposed
acceptance criterion is not attainable by construction. Stage 0 converts a fragile case study into a
calibrated methodological result, and it is the single change most likely to move the paper into a
high-impact venue.

### Stage 1 — Corpus construction

Search and screening follow PRISMA-style reporting with a full flow diagram and a documented
screening log.

**Domain 1 (BDD electrochemistry).** Structured search across Scopus, Web of Science and
ScienceDirect (2015–2026) combining "boron-doped diamond" with "Raman", "delamination", "Faradaic
efficiency", "critical current density", "service life", "substrate". Inclusion: peer-reviewed
studies reporting (i) Raman-derived doping or sp³/sp² data **and** (ii) at least one quantitative
performance or failure outcome, for a named substrate (Ti, Nb, Ta, Si).

**Domain 2 (halide perovskites) — SUBSTITUTED.** The original Domain 2 (PVDF/hydroxyapatite
membranes) is **removed**: a live OpenAlex count returns 122 works total and 90 journal articles for
`(PVDF OR polyvinylidene fluoride) AND hydroxyapatite`, at roughly 20 per year. The decisive evidence
is venue structure rather than volume — the largest venue has five papers, and *Journal of Membrane
Science*, *Desalination* and *Separation and Purification Technology* do not appear in the top forty
venues at all. The niche has no journal home, and the achievable yield is 30–60 records against a
power-analysis target that will exceed 100. **No amount of effort fixes a literature ceiling.**

Domain 2 becomes halide perovskite solar cells, extracted against the **Perovskite Database**
(Jacobsson et al., *Nature Energy*, 2022; perovskitedatabase.com), an open FAIR-principled database of
tens of thousands of curated devices. This substitution is the single largest improvement to the
study, because it converts the proposal's weakest point into its strongest:

- **It supplies an externally curated ground truth.** The manual gold standard was the study's
  principal validity risk and its costliest step. For Domain 2 the gold standard is a database built
  by an independent community under published FAIR rules, at a scale of thousands of values rather
  than 150–200 hand-annotated ones.
- **It removes the inter-rater reliability burden for that domain.** κ is still reported on the
  hand-annotated BDD subset, where annotation remains the only available ground truth, but the
  perovskite validity check no longer depends on our own annotation at all.
- **It makes the cross-domain contrast real rather than asserted.** The substantive contrast is
  **figure-bound versus table-bound data**, not "homogeneous electrochemical values versus
  multi-technique characterisation". Perovskite performance values are overwhelmingly tabulated and
  machine-readable; BDD performance values are largely in text, and BDD Raman-derived sp³/sp² data are
  typically figure-only, recovering by deconvolution under unstated assumptions. Figure-bound
  extraction is the genuinely harder and less-benchmarked task, and it is now the axis under test.
- **It removes the scale confound.** The prior pairing compared a large literature against a
  twenty-fold smaller one, so domain difficulty was inseparable from domain size.

**Domain 1 remains BDD, with a corrected feasibility picture.** `"boron-doped diamond"` returns 3,545
articles for 2015–2026 (2,372 with "electrode"), but the substrate criterion collapses this sharply:
`"boron-doped diamond" AND "titanium"` returns only 128, and that is an upper bound because it matches
papers merely comparing BDD against Ti₄O₇ anodes. Realistic Domain 1 yield is therefore **60–120
records**. The main attrition source is expected to be the conjunction with a quantitative failure
outcome (service life, delamination), which is usually reported in dedicated durability papers rather
than alongside Raman doping data. **Action before any screening: run the four substrate queries
(Ti, Nb, Ta, Si) and hand-sample roughly thirty hits each to measure the true conjunction rate.** One
afternoon determines whether Domain 1 targets 100 records or 60.

**Corpus target.** Set by Stage 0's power analysis, not assumed, and now constrained by the measured
ceilings above. The original target of 15–25 records per domain is rejected as underpowered; every
quantitative study located in the causal-discovery robustness literature starts at n = 100, and
Scheines & Ramsey (2016) report that at n = 100 accuracy "decays severely" once measurement error
reaches roughly 17 %, with the decay slowing only at larger n. **If the power analysis implies a
target above what the literature can supply, the study is reframed as a single-domain calibrated
methodological contribution with a reduced-scope transfer test — and that decision is taken before
annotation begins.**

**Extraction schema.** A predefined JSON schema specifies variables per domain — numeric (doping
level, thickness, current density, service life, flux, rejection rate), categorical (substrate type,
deposition method, membrane composition) and relational (reported associations between variables).
The schema is domain-specific but shares a common structure to enable cross-domain comparison.

**Prose target.** Records are tagged by provenance (table-embedded vs. prose-embedded) so that Gap 3
becomes a measurable variable rather than an assertion.

### Stage 2 — Uncertainty-aware extraction with multiple signals

**Model control.** Extraction is performed with **frozen open-weight models** (e.g. a Llama-family
and a Qwen-family instruct model), with exact version, quantisation and decoding parameters reported.
This replaces reliance on a closed hosted model whose version cannot be pinned, and makes the study
independently reproducible.

**Signal A — paraphrase self-consistency (aleatoric term).** Each target value is extracted N times
under *paraphrased* prompts (semantically equivalent reformulations, not literal repetitions), at
controlled temperature. Uncertainty is the coefficient of variation across attempts for numeric
variables (after outlier handling: values beyond 3 × MAD from the median are excluded, and the
exclusion rate is reported) and 1 − (majority agreement proportion) for categorical/relational
variables. **N is provisional, not asserted.** RQ7 measures the variance decomposition on this
corpus first; if the paraphrase component carries little variance, the budget is reallocated to model
and decoding diversity rather than spent on more paraphrases, following Ẓatuchin (2026). The value
chosen and the measurement that justified it are both reported.

**Signal B — token-level uncertainty.** Sequence-level and token-level log-probabilities or entropy
for the extracted span, where the model exposes them.

**Signal C — cross-model disagreement (epistemic term).** Following Hamidieh et al. (2026, ICLR),
this is computed not as raw agreement but as the **gap between inter-model and intra-model semantic
similarity**, which is the form shown to flag confident failures precisely where dispersion is flat.
It requires a **scale-matched ensemble of at least three instruction-tuned models from independent
families**, not two, because the epistemic term is defined over an ensemble. Signal A varies the
prompt; Signal C varies the model, and it is the only signal that survives mode collapse. This is why
the original single-signal design was insufficient and why the multi-signal design is not padding.

**Composite uncertainty.** U_i = f(A_i, B_i, C_i). Calibration of f uses **split conformal
prediction** on the gold-standard subset rather than plain isotonic regression, because conformal
calibration carries finite-sample coverage guarantees for the resulting uncertainty interval and is
the method the recent literature reports as state of the art for this task (Xu & Lu, 2025, TECP).
Isotonic regression is retained as a comparison. Individual signals are always reported alongside
the composite, and the incremental value of each signal is reported as an ablation. Calibration is
cross-fitted so that the composite is never evaluated on the data that fitted it.

**Rationale.** The original single-signal design rested on an assumption the literature does not
support unconditionally. Ali (2026) shows self-consistency is reliable *per item* but carries no
cross-question structure within a single model, and that only a diverse ensemble recovers such
structure; Xu & Lu (2025) show token-entropy UQ with conformal calibration outperforms
self-consistency-based UQ. The three-signal design therefore follows the evidence rather than
assuming one signal suffices: Signal A supplies per-value reliability, Signal B supplies the
logit-level evidence the literature ranks highest, and Signal C supplies the ensemble dimension that
a single model provably lacks. RQ1 makes that comparison itself a result.

### Stage 3 — Gold standard with inter-rater reliability

A manually verified subset of **150–200 values per domain** is annotated against the source text.
Ambiguous cases are resolved by reference to the source.

**Change from v1.** A second independent annotator codes a random **25 %** of values, and Cohen's κ
is reported (target κ ≥ 0.70); disagreements are adjudicated by a third party and the adjudication
rate is reported. The original proposal acknowledged the absence of inter-rater reliability as a
limitation; for a paper whose entire validity rests on a hand-built gold standard, that limitation is
not survivable at review. This is a low-cost, high-credibility fix.

Extraction precision, recall and F1 are computed against this subset. The correlation between
per-value uncertainty and per-value extraction error is then measured — **this is RQ2 and the
validity check for the uncertainty metric itself.**

### Stage 4 — Causal structure learning with uncertainty propagation

**Baseline discovery.** Applied with variable selection guided by domain knowledge to keep the
variable set small (5–8 variables per domain). **Three algorithms are run — PC, GES, and a
score-based/continuous method — rather than PC alone.** Agreement across algorithms is reported, and
any conclusion that depends on a single algorithm is flagged. With the corpus sizes targeted in
Stage 1 the algorithms are used as structure *proposal* mechanisms whose sensitivity to input
uncertainty is the object of study; this framing is stated explicitly and its limits are acknowledged.

**Uncertainty propagation.** Confidence-weighted bootstrap resampling, with record weight
w_i = g(U_i). The original linear form w_i = 1/(1 + CV_i) and categorical form w_i = agreement
proportion are retained as the primary specification, and **linear, exponential and rank-based
alternatives are tested in a formal sensitivity analysis reported as a table**, not a paragraph.

**Structure-stability metrics.**
- **Per-record causal impact (new, replaces the single global SHD).** For each record *i*, correct
  that record alone, relearn the structure, and record CI_i = SHD(G, G_i). This converts the
  proposal's single global number into *n* observations and is what makes RQ4 statistically
  answerable. This is the metric that carries the paper's central claim.
- **Global structural sensitivity.** SHD between the graph learned from original extractions and the
  graph learned after correcting all high-uncertainty extractions.
- **Edge-stability sensitivity.** For each edge, bootstrap stability is the frequency of appearance
  across resamples; the association between per-record uncertainty and per-edge stability is measured
  with confidence intervals.

### Stage 5 — Null and adversarial tests *(NEW)*

Three controls that separate a real effect from an artefact:

1. **Label-shuffling / placebo test.** Uncertainty values are randomly permuted across records and
   the pipeline is re-run. A correlation of similar magnitude to the observed one indicates that the
   effect is an artefact of the pipeline rather than a property of the extraction uncertainty.
2. **High-versus-low correction contrast.** If uncertainty is meaningful, correcting *high*-uncertainty
   records must change the graph more than correcting *low*-uncertainty records matched on variable
   and magnitude. This is a direct, assumption-light test of the paper's central claim.
3. **Cross-domain weight transfer.** Weights estimated in one domain are applied to the other's data.
   If the weighting scheme carries no domain-specific information, the transfer should be neutral.
4. **Mode-collapse diagnostic.** Among gold-standard-incorrect values, the fraction produced with
   dispersion at or near zero is reported, together with whether Signal C flagged them. This test
   operates at the extraction level rather than the causal level, and it is the most direct available
   check on the proposal's core measurement assumption. A large fraction is a negative result about
   dispersion-based uncertainty on extraction tasks — and it is publishable as such, because it would
   contradict Ali (2026) on a task class where that result has not been tested.

### Stage 6 — Cross-domain comparison

The full calibrated pipeline runs independently on both domains. Compared: the distribution of
extraction uncertainty; the uncertainty–error correlation (RQ2); the strength of the
uncertainty–instability relationship (RQ4, RQ5); and the structural properties of each dataset
(variable density, unit homogeneity, terminological consistency, prose-versus-table provenance) that
may explain differences (RQ6).

---

## 5. Baselines and Ablations

The original proposal named no baselines. Reviewers will ask "compared to what?". Five are defined:

| ID | Baseline | Purpose |
|---|---|---|
| B1 | Single prompt, temperature 0, no uncertainty estimation | Standard practice in current extraction systems |
| B2 | Table-only extraction (MaTableGPT-style scope) | Quantifies the value of accessing narrative prose (Gap 3) |
| B3 | **Uniform-weight bootstrap** (no uncertainty propagation) | **The central comparison: does propagation change anything?** |
| B4 | F1-only evaluation of extraction quality | Quantifies the value of the causal-impact criterion (Gap 1) |
| B5 | Best single uncertainty signal vs. composite | Justifies the multi-signal design (RQ1) |
| B6 | Semantic entropy (Kuhn et al., 2023) and token-entropy conformal (Xu & Lu, 2025) | Required comparator: the current literature treats these as the standard, so beating only "no uncertainty" would be uninformative |

B3 is the decisive ablation. If uncertainty-weighted and uniform-weighted resampling produce
indistinguishable structures, the paper's practical recommendation inverts — and that is a
publishable result under H2.

---

## 6. Pre-registered Hypotheses and Analysis Plan

Registered before implementation. Acceptance criteria are derived from Stage 0's power analysis
rather than asserted.

**H1 (substantial effect).** High-uncertainty records are statistically associated with unstable
edges and with elevated per-record causal impact → uncertainty propagation is a necessary, not
optional, component of causal inference on automatically extracted data.

**H2 (negligible effect).** No significant association → causal inference on this class of extracted
data is robust to extraction noise within the observed range. This is a reassurance result, not a
failure, and it requires the confidence interval to exclude |r| > 0.3 to be reported as such.

**H3 (domain-dependent effect).** The relationship differs between domains → a diagnostic criterion
identifying when uncertainty propagation is necessary, based on structural properties of the data.

**Analysis plan.** Effect sizes reported with 95 % confidence intervals; α = 0.05; multiplicity across
the hypothesis family controlled by Holm–Benjamini–Hochberg; all code, prompts, extracted data and
gold-standard annotations released. **The minimum detectable effect and the minimum viable corpus
size are fixed by Stage 0 before any literature is screened, and any deviation is reported as such.**

---

## 7. Contributions

**Methodological.**
1. **Causal impact of extraction error** — a task-aware evaluation criterion for extraction, defined
   per record as the Structural Hamming Distance induced by correcting that record, replacing
   extraction-quality-in-isolation with extraction-quality-in-use.
2. **A simulation-calibrated uncertainty-propagation framework** — a pipeline whose behaviour is
   characterised against known ground truth across sample sizes, error rates and severities before
   being applied to real literature, including a calibration curve from observed uncertainty to
   expected structural change.
3. **Multi-signal uncertainty for scientific extraction** — a calibrated combination of paraphrase
   self-consistency, token-level uncertainty and cross-model agreement, with an ablation establishing
   the incremental value of each.

**Empirical.**
4. A dual-annotated gold-standard dataset for extraction from BDD literature, with reported
   inter-rater reliability, **plus a perovskite validation set constructed against the independently
   curated Perovskite Database** — an externally produced ground truth that does not depend on our own
   annotation.
5. A power analysis and attainable-ceiling result for uncertainty-aware extraction that is reusable
   by the wider community, independent of these two domains.
6. Transparent reporting of negative or null results if the central hypothesis is not supported.

**Repositioned novelty.** The contribution is not uncertainty propagation in the abstract — Liu et
al. (2022) already establish that measurement error corrupts causal structure, and correct for it.
The contribution is three things that literature does not supply: (i) the **causal impact of
extraction error** as an evaluation criterion for extraction systems, defined per record so that it
is statistically usable; (ii) **calibration of the uncertainty–instability relationship against
known ground truth**, producing a calibration curve and a power analysis that bound what any
uncertainty metric can claim on this task; and (iii) empirical evidence on whether a
measurement-error result established for generic perturbations transfers to an **LLM error model**,
across two structurally dissimilar domains. If it does not transfer, that is the finding.

---

## 8. Limitations

- **Sample size.** Despite the enlarged corpus, causal structure learning on observational literature
  data cannot produce definitive causal graphs. The claim is about the sensitivity of proposed
  structures to input uncertainty, not about discovering true causal structure. Stage 0 bounds what can
  be concluded at each *n*, and the literature floor — every quantitative study found begins at
  n = 100 — means anything below that is a **stress test at the infeasible extreme**, reported as such
  rather than presented as adequate.
- **Corpus ceiling, not corpus effort.** Domain 1 yields an estimated 60–120 records because the
  substrate criterion collapses the literature (2,372 → ~128), not because of insufficient search. If
  the power analysis demands more than the literature can supply, the study is reframed — the inclusion
  criteria are not widened.
- **Mode collapse.** A dispersion-based metric can be flatly wrong on confidently wrong extractions
  (Hamidieh et al., ICLR 2026). The cross-model term is designed to cover this, but if the collapsed
  share is large the mitigation is partial. RQ8 exists to measure *how* partial rather than to assume
  it is sufficient.
- **Two gold standards, which must never be pooled.** BDD accuracy is measured against hand annotation
  and perovskite accuracy against an independently curated database. These are **different measurement
  procedures**, so the two figures are reported side by side and never averaged. The external database
  also carries an unknown curation error rate, which is a **floor** on the measured perovskite accuracy
  and cannot be estimated from within this study.
- **Matching failure is invisible from the extraction side.** With an external gold standard, a wrong
  paper-to-record link is silently scored as an extraction error against the pipeline. The protocol
  controls this with DOI-plus-composition matching, recorded confidence and candidate counts, and hand
  verification of a 30-match sample — but a residual rate below the sampling resolution cannot be
  excluded, and this is stated rather than hidden.
- **Uncertainty type.** Only extraction uncertainty is measured directly. Aleatoric uncertainty
  (source-text ambiguity) and epistemic uncertainty (model knowledge gaps) are distinct; the
  token-entropy and cross-model signals partially, but not fully, separate them. The error taxonomy in
  the annotation codebook is what makes the distinction measurable at all.
- **Synthetic-to-real gap.** Simulation calibration assumes the injected error model resembles real
  extraction errors. The design mitigates this with ambiguity-correlated, independent and
  confidence-collapse regimes, but the assumption is not eliminable. The varsortability and
  standardized-effect-size controls make the *simulation* fair; they cannot make it representative.
- **Domain coverage.** Two domains are tested, chosen to contrast figure-bound against tabulated
  extraction. Generalisation to other scientific fields is a hypothesis, not a demonstrated result.
- **Gold-standard subjectivity.** Reduced but not eliminated by dual annotation, blinding and
  adjudication. κ below 0.70 triggers a codebook revision and re-annotation, not a reported result.
- **Model dependence.** Results may vary with model family and version. This is mitigated by frozen
  open-weight models, reported revision hashes and decoding parameters, and is quantified by the
  cross-model term — but a frozen model is a snapshot, not a guarantee.
- **Venue metric.** The figures in Section 10 are OpenAlex 2-year mean citedness, **not** Journal
  Impact Factors. They support a relative ordering and must be replaced with publisher-sourced JIF
  values before submission.

---

## 9. Reproducibility

All components run on open-source tools (Python, `causal-learn`, `numpy`, `pandas`, `scikit-learn`)
plus open-weight LLM inference. No specialised hardware, paid software or laboratory access is
required. Release: pipeline code, prompt sets, extracted records, gold-standard annotations with
annotator identity masking, simulation configurations, and a container definition. Fixed random seeds
and reported hardware for all stochastic components.

---

## 10. Target Venues

**Correction from v1.** The originally listed primary venues (AISTATS, UAI, NeurIPS Datasets &
Benchmarks) are not appropriate. AISTATS and UAI are top-tier statistics/ML venues that require
theory or large-scale empirics and will reject a two-domain sensitivity study; the NeurIPS D&B track
expects a benchmark contribution substantially larger than a few hundred annotated values. It should
also be noted that these are **conferences without journal impact factors** — the stated goal of
publishing in a high-impact-factor journal points to journals.

**Primary targets (journals).** The table reports **2-year mean citedness from the OpenAlex sources
API**, which is *not* the Journal Impact Factor. JIF is computed by Clarivate from the Web of Science
citation graph with a specific denominator; this figure comes from OpenAlex's own citation graph. The
two correlate but diverge, and they diverge in **both directions** — for *Patterns* the OpenAlex figure
exceeds the JIF that third-party sites report, and for *npj Computational Materials* it falls below.
**The column is therefore a defensible relative ordering, not a JIF claim**, and it is labelled as
what it actually is.

| Venue | Publisher | 2-yr mean citedness (OpenAlex) | h-index | Works | Fit |
|---|---|---|---|---|---|
| *Computers & Education* | Elsevier | 14.80 | 325 | 7,204 | **Not a fit for this paper**; listed only to show the field's ceiling |
| *Patterns* | Elsevier (Cell Press) | 12.47 | 80 | 1,006 | Best overall fit: AI-for-science methodology, cross-domain |
| *npj Computational Materials* | Nature Portfolio | 10.77 | 139 | 2,363 | Ambitious; plausible only if the Stage 0 calibration result is strong |
| *Journal of Cheminformatics* | BioMed Central | 8.35 | 123 | 1,899 | Extraction methods and standards |
| *Digital Discovery* | Royal Society of Chemistry | 5.64 | 46 | 1,282 | AI + materials; method-and-data papers; a young venue |
| *Journal of Chemical Information and Modeling* | ACS | 5.29 | 223 | 9,909 | Extraction + cheminformatics methodology; large back catalogue |
| *Data Mining and Knowledge Discovery* | Springer | 4.63 | 145 | 1,419 | Causal / sensitivity methodology framing |

**Reading the table honestly.** *Patterns* is the primary target on both fit and standing. *npj
Computational Materials* carries more prestige per paper but is a harder sell for work whose principal
contribution is methodological rather than a materials result. *Digital Discovery* and *JCIM* are
realistic and faster, and their lower citedness reflects scope and youth rather than quality —
*Digital Discovery* is a young journal whose h-index is still climbing.

**There is no route to the absolute global top ten.** *Nature*, *Science* and the *New England Journal
of Medicine* lead the world impact-factor table, and a paper of this scope and subject does not belong
in them. A proposal that promised otherwise would be selling something it cannot deliver. The
worthwhile and achievable target is **the top slice of this paper's own field**, and the table above
is that list.

**Secondary / conference.** ACL or EMNLP (Findings) for the extraction and uncertainty-quantification
component, and a dedicated NLP-for-science workshop for an early version. These are **conferences and
carry no journal impact factor** — which matters, since impact factor is the stated goal.

**Metric discipline.** Immediately before submission, each candidate's JIF is checked on the
publisher's own page or in Journal Citation Reports, and recorded with its year. **No venue decision
rests on a number whose metric is unnamed or whose source is not the publisher.** Third-party
aggregator figures were deliberately not used here: several were found to conflict with each other and
with OpenAlex in both directions, so quoting one would have been arbitrary.

*Source: OpenAlex sources API, `2yr_mean_citedness`, retrieved for this document via
`api.openalex.org/sources?filter=issn:...`. Publisher sites (RSC, Springer Nature, ACS, Cell Press)
consistently blocked automated retrieval, which is precisely why a publisher-independent source was
used and why the metric is named rather than called an impact factor.*

---

## 11. Timeline

| Phase | Work | Indicative duration |
|---|---|---|
| 0 | Simulation suite, power analysis, attainable-ceiling result | 4–6 weeks |
| 1 | Corpus search, screening, PRISMA reporting, schema finalisation | 4–6 weeks |
| 2 | Extraction runs, uncertainty signals, composite calibration | 4 weeks |
| 3 | Gold standard, dual annotation, κ, adjudication | 4–6 weeks |
| 4 | Causal pipeline, per-record causal impact, sensitivity analyses | 4 weeks |
| 5 | Null and adversarial tests | 2 weeks |
| 6 | Analysis, figures, manuscript, internal review | 6–8 weeks |
| — | **Total to submission-ready manuscript** | **≈ 7–9 months** |

Stage 0 doubles as an early kill-switch: if the attainable ceiling is too low or the required corpus
proves unattainable, the study is reframed before the expensive annotation work begins.

---

## 12. Division of Labour

**Confirmed: three investigators.** One holds a doctorate in materials science, one is in the College
of Computers, and one is in artificial intelligence. This is the minimum viable team: the protocol
requires **two independent screeners plus a third adjudicator**, and the BDD gold standard requires a
**second annotator**. Three people can fill every role, so Stage 1 is unblocked. Allocation:

| Role | Holder | Cannot also be |
|---|---|---|
| Materials lead — BDD electrochemistry, perovskite device physics, decides whether an extracted value genuinely corresponds to a source claim | Materials-science investigator | — |
| AI lead — LLM extraction, uncertainty quantification, conformal calibration, RQ1/RQ7/RQ8 | AI investigator | Second BDD annotator |
| Computing lead — causal discovery methodology, per-record causal impact, RQ4/RQ5 | College of Computers investigator | Second BDD annotator |
| **Screener 1** (title/abstract and full text) | Computing lead | — |
| **Screener 2** (independent) | AI lead | — |
| **Adjudicator** for screening conflicts | Materials lead | Screener |
| **BDD annotator 1** | Materials lead | — |
| **BDD annotator 2** (25 % subsample, blinded) | Computing lead | — |
| **Annotation adjudicator** | AI lead | Annotator |
| Perovskite–database matching audit | Materials lead | — |

**One structural safeguard.** The person who designed the prompt set must not be the only annotator
of the gold standard, and annotation must be blinded to the model's uncertainty (Section 3.4). With
three investigators this is satisfiable — the AI lead owns the prompts, and the two annotators are the
materials and computing leads. **If the team contracts to two people, the design fails**: there would
be no independent screeners, no κ, and therefore no supportable claim about gold-standard validity.

Open and needed before Stage 1 begins: the **target submission date**, and confirmation that the
materials lead can commit the annotation hours, since the BDD annotation is the single largest
personnel cost in the study.

---

## 13. Plan B

**B1 — Uncertainty metric fails its validity check (RQ2 fails).** The study is reframed as a
*negative result* on the validity of self-consistency and sampling-based uncertainty metrics for
scientific extraction, which is a publishable contribution and would caution the community against
adopting such metrics without validation. The pipeline, the simulation suite, the power analysis and
the gold-standard dataset remain as contributions independent of the central hypothesis.

**B2 — Corpus too small after screening.** The study is reframed as a single-domain calibrated
methodological study with the second domain used as a reduced-scope transfer test. Per the original
feasibility statement, this decision is taken before Stage 4 begins.

**B3 — Stage 0 shows the required corpus is unattainable.** The paper is repositioned as a pure
methodological and simulation contribution, with the literature study presented as an illustrative
single-domain application. This is the outcome Stage 0 exists to detect early.

---

## Appendix A — Reference Status

**Verified in preliminary search, to be re-checked in the systematic pass:**

1. MaTableGPT: GPT-based table data extractor from materials science literature. *Advanced Science.*
   https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202408221
2. Liu, Y., Constantinou, A. C. & Guo, Z. (2022). Improving Bayesian network structure learning in
   the presence of measurement error. *Journal of Machine Learning Research*, 23(324), 1–28.
   https://www.jmlr.org/papers/v23/20-1319.html
   — **Abstract verified directly.** Establishes that measurement error induces spurious edges and
   that synthetic benchmark performance overestimates real-world performance; contributes a
   correction phase evaluated on five structure learning algorithms.
   Code: https://github.com/Enderlogic/Spurious-Edge-Detection
3. Conformal prediction and verification of large language model extractions in EHR data.
   *AAAI Symposium Series.* https://ojs.aaai.org/index.php/AAAI-SS/article/download/36929/39067/41006
4. Discovering causal structures in corrupted data: frugality in anchored Gaussian DAG models.
   *Computational Statistics & Data Analysis* (2025).
   https://www.sciencedirect.com/science/article/pii/S0167947325001434
5. Ali, I. (2026). Stochastic sampling is epistemically shallow: the dimensionality gap between
   temperature variation and model diversity in LLMs. *EIML@ICML 2026* (workshop paper);
   arXiv:2607.20464 [cs.AI], submitted 18 May 2026. https://arxiv.org/abs/2607.20464
   — **Abstract verified directly.** Supports per-value self-consistency; establishes that a single
   model carries no cross-question error structure, so an ensemble is required for that.
6. Xu, B. & Lu, Y. (2025). TECP: Token-Entropy Conformal Prediction for LLMs. arXiv:2509.00461
   [cs.CL], v2. https://arxiv.org/abs/2509.00461
   — **Abstract verified directly.** Reports token-entropy UQ with split conformal prediction
   outperforming prior self-consistency-based UQ methods across six LLMs and two benchmarks.
7. Hamidieh, K., Thost, V., Gerych, W., Yurochkin, M. & Ghassemi, M. (2026). Complementing
   self-consistency with cross-model disagreement for uncertainty quantification. *ICLR 2026*
   (poster, 24 Apr 2026). https://iclr.cc/virtual/2026/poster/10007682
   — **Abstract verified directly.** Establishes that self-consistency "collapses when models are
   overconfident and produce the same incorrect answer across samples"; introduces an epistemic term
   from a scale-matched ensemble that flags confident failures where aleatoric uncertainty is low.
   Five 7–9B instruction-tuned models, ten long-form tasks.

**Reported by the systematic search, pending independent second confirmation.** The following were
returned with publisher or repository URLs and read by the search agent, but have not yet been
re-fetched by the author of this document. They must be confirmed at source before appearing in a
submitted manuscript, and titles marked "(title unconfirmed)" are descriptions, not quotations.

**Measurement error in causal structure learning — the novelty constraint set.** These are the
citations that falsify the original novelty claim, and they are required rather than optional:

16. Blom, T., Klimovskaia, A., Magliacane, S. & Mooij, J. M. (2018). An upper bound for random
    measurement error in causal discovery. *UAI 2018*, 570–579. arXiv:1810.07973
    — **Abstract verified directly.** Obtains an upper bound on measurement-error variance from the
    covariance matrix and uses it **as a correction for constraint-based causal discovery**. This is
    uncertainty propagated into inference, so the proposal's original novelty claim cannot stand.
17. Saeed, B., Belyaeva, A., Wang, Y. & Uhler, C. (2020). Anchored causal inference in the presence
    of measurement error. *UAI 2020*, PMLR 124:619–628.
18. Zhang, K., Gong, M., Ramsey, J., Batmanghelich, K., Spirtes, P. & Glymour, C. (2018). Causal
    discovery with measurement error. *UAI 2018*, 1063–1072.
19. Kummerfeld, E., Williams, L. & Ma, S. (2023). Power analysis for causal discovery.
    *International Journal of Data Science and Analytics* 17(3), 289–304.
    DOI 10.1007/s41060-023-00399-4 · open manuscript PMC11581182
    — **Abstract and Methods verified directly.** The first published power-analysis method for causal
    discovery, and the source of the standardized-SEM generation used in Stage 0 and of the
    varsortability critique. The standardization procedure was read in full and matches our
    implementation: choose the independent noise variances so that every variable has marginal
    variance 1, which makes the edge weight equal the standardized effect size r.
    **⚠ The numeric power table could not be retrieved.** The open manuscript truncates the results
    section at the same point on every fetch, regardless of URL anchor, and `web_fetch` rejects PDFs
    outright. **A human must obtain Table 3 (or the Shiny interface the paper describes) before the
    corpus-size argument is finalised.** This is the load-bearing citation for that argument, and the
    proposal currently relies on Scheines & Ramsey for the numeric floor instead.
20. Reisach, A. G., Seiler, C. & Weichwald, S. (2021). Beware of the simulated DAG! Causal discovery
    benchmarks and varsortability. *NeurIPS 2021*. arXiv:2102.13647
21. Scheines, R. & Ramsey, J. (2016). Measurement error and causal discovery. *CEUR Workshop
    Proceedings*. PMC5340263
    — **Quote verified directly** in the source: "For sparse graphs, at sample size 100 the accuracy of
    FGES decays severely for measurement errors of less than 17 % (ME = .2)". Their grid runs
    n ∈ {100, 500, 1000, 5000}, so **n = 100 is their floor, not a recommended value**, and their
    reported trade-off — that the decay slows at larger n — means small n and measurement error
    compound rather than substitute.
22. Tsamardinos, I., Brown, L. E. & Aliferis, C. F. (2006). The max-min hill-climbing Bayesian network
    structure learning algorithm. *Machine Learning* 65(1), 31–78. — **origin of SHD**; note that the
    `pcalg` reference list misprints the venue as JMLR, and that error must not be propagated.
23. Peters, J. & Bühlmann, P. (2015). Structural intervention distance (SID) for evaluating causal
    graphs. *Neural Computation* 27(4), 771–799. — SID "differs significantly" from SHD; report both.
24. Friedman, N., Goldszmidt, M. & Wyner, A. (1999). Data analysis with Bayesian networks: a bootstrap
    approach. *UAI 1999*. — origin of bootstrap edge stability; explicitly motivated by the low-data
    regime, so it is standard practice rather than a contribution.
25. Colombo, D. & Maathuis, M. H. (2014). Order-independent constraint-based causal structure learning.
    *JMLR* 15(116), 3921–3962. — PC is order-dependent; run-to-run SHD variance can be an
    implementation artefact.
26. Jacobsson, T. J. et al. (2022). An open-access database and analysis tool for perovskite solar
    cells based on the FAIR data principles. *Nature Energy*.
    https://www.nature.com/articles/s41560-021-00941-3 — **existence verified**; the exact device
    count and export interface must be confirmed at the source before the corpus plan depends on it.
27. Ritt, C. L. et al. (2022). The open membrane database: synthesis–structure–performance
    relationships of reverse osmosis membranes. *Journal of Membrane Science* 641, 119927. — verified
    as a methodology precedent; **not** a substitute for a membrane domain, since it covers
    RO/polyamide membranes only.
28. Khalighinejad, G., Circi, D., Brinson, L. & Dhingra, B. (2024). LLM-assisted extraction from
    materials science literature. *Findings of ACL 2024*.
    https://aclanthology.org/2024.findings-acl.779/ — **the direct prior-art threat to the input
    signal**: self-consistency already applied to full-document extraction in materials and polymer
    literature. Cited in section 2.1 and load-bearing for the novelty framing.
29. Polak, M. P. & Morgan, D. (2024). Extracting accurate materials data from research papers with
    conversational language models. *Nature Communications* 15, 1569.
    DOI 10.1038/s41467-024-45914-8 — ChatExtract; ~90 % precision and recall via prompt engineering
    plus follow-up verification questions. Note it obtains accuracy by *asking the model to verify*,
    not by resampling.
30. Dagdelen, J. et al. (2024). Structured information extraction from scientific text with large
    language models. *Nature Communications* 15, 1418. DOI 10.1038/s41467-024-45563-x — canonical
    structured extraction; does **not** address uncertainty, which supports the gap claim.
31. Kalisch, M. & Bühlmann, P. (2007). Estimating high-dimensional directed acyclic graphs with the
    PC-algorithm. *JMLR* 8(22), 613–636. — the asymptotic condition for PC: n must grow faster than
    the number of nodes. No finite-n guarantee, which is why the sample-size argument rests on
    Scheines & Ramsey rather than on this.
32. Sinha, M., Tadepalli, S. & Ramsey, J. (2021). *PLOS ONE* 16(2), e0245776. — documents that the
    Sachs ground truth is an expert-curated consensus and that the supposed perfect interventions have
    off-target effects.
33. Chevalley, M., Roohani, Y., Mehrjou, A., Leskovec, J. & Schwab, P. (2023). CausalBench: a
    large-scale benchmark for causal learning on biological data. *NeurIPS 2023 Datasets and
    Benchmarks*. arXiv:2210.17283 — interventional methods do not outperform observational ones on
    real data, contrary to synthetic benchmarks.
34. Scutari, M. & Nagarajan, R. (2013). Identifying significant edges in graphical models of molecular
    networks. *Artificial Intelligence in Medicine* 57(3), 207–217. — bootstrap strength and averaged
    networks; the established practice this proposal must not present as novel.

8. Kim, E., Foty, R., Shrestha, M. & Seyfert-Margolis, V. (2025). Conformal prediction and
   verification of large language model extractions in EHR data. *AAAI Symposium Series* 7(1),
   539–546. DOI 10.1609/aaaiss.v7i1.36929
9. Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A. & Zhou, D. (2023).
   Self-consistency improves chain of thought reasoning in language models. *ICLR 2023*.
   arXiv:2203.11171
10. Kuhn, L., Gal, Y. & Farquhar, S. (2023). Semantic uncertainty: linguistic invariances for
    uncertainty estimation in natural language generation. *ICLR 2023* (Spotlight). arXiv:2302.09664
11. Farquhar, S., Kossen, J., Kuhn, L. & Gal, Y. (2024). Detecting hallucinations in large language
    models using semantic entropy. *Nature* 630(8017), 625–630. DOI 10.1038/s41586-024-07421-0
12. Xiao, J. et al. (2025). Restoring calibration for aligned large language models. *ICML 2025*.
    arXiv:2505.01997
13. Ẓatuchin, D. (2026). Where does the noise come from? A variance-components decomposition of
    non-determinism in LLM brand answers. arXiv:2607.13304 (preprint, 14 Jul 2026).
14. Kunitomo-Jacquin, L., Marrese-Taylor, E., Fukuda, K. & Hamasaki, M. (2026). Evidential semantic
    entropy for LLM uncertainty quantification. *EACL 2026*, 7107–7122.
15. Ghosh, S. et al. (2024). Extraction from materials science literature with expert manual error
    analysis *(title unconfirmed)*. *Findings of ACL 2024*. arXiv:2406.05348

**⚠ High-priority item — resolved.** An IEEE record titled *"Uncertainty Aware Multi-Agent RAG
Using Paraphrase-Induced Epistemic Variance Analysis"* could not be retrieved directly (the
publisher returned HTTP 202 with no body). It was resolved through the Crossref API:
Atalkar, D., Sohani, S. & Deogaonkar, A. (2026), *2026 International Conference on Intelligent and
Sustainable Electronics & Computing Technologies (INSECT)*, May 2026, DOI
10.1109/INSECT68872.2026.11663703. The title overlaps almost exactly with this proposal's input
signal. **Consequence adopted: paraphrase-induced variance as an uncertainty measure is prior art and
is not presented as a contribution of this work.** The referenced paper is a conference contribution
on multi-agent retrieval, not on causal inference, so the downstream contribution is unaffected —
but the citation is load-bearing for the Section 7 framing rather than optional, and Section 2.2 has
been amended accordingly.

**Still quarantined and not cited:** *"Scientific Table Data Extraction with Uncertainty
Quantification"* (JCDL 2024, DOI 10.1145/3677389.3702616) and *"Uncertainty-Aware Complex Scientific
Table Data Extraction"* (ICDAR 2025, DOI 10.1007/978-3-032-04624-6_4) — both relevant by title,
neither readable, so neither can be cited or relied upon.

16. Atalkar, D., Sohani, S. & Deogaonkar, A. (2026). Uncertainty aware multi-agent RAG using
    paraphrase-induced epistemic variance analysis (PI-EVA). *2026 International Conference on
    Intelligent and Sustainable Electronics & Computing Technologies (INSECT)*, Pune, India,
    29–30 May 2026. DOI 10.1109/INSECT68872.2026.11663703
    — **Metadata verified via Crossref; abstract and introduction supplied by a co-author** after the
    publisher blocked automated retrieval. Text confirmed verbatim: PI-EVA "measures epistemic
    uncertainty by analyzing semantic stability ... by checking how consistent model interpretations
    are across different paraphrased queries"; the **Epistemic Variance Score (EVS)** is used as a
    **pre-retrieval routing signal** that "actively modifies planning diversity, retrieval redundancy,
    verification strictness, and generation parameters". Evaluated on HotpotQA dev-distractor:
    Answer F1 54.29 % (+11.91 % over DRAGIN), EM 44 %. No fine-tuning or labelled data.
    **This is the closest prior work and is now cited in Section 2.2 with three specific
    consequences**, including a terminological conflict over the word *epistemic* that our RQ8
    diagnostic is positioned to settle.

**To be added in v2.1** by the running systematic search: prior art on uncertainty propagation in
extraction pipelines; semantic-entropy and token-entropy uncertainty methods; calibration evidence
for verbalised versus logit-based confidence; prompt-sensitivity literature; sample-size guidance
for PC-family algorithms; existing materials-science extraction datasets and databases; systematic
reviews on BDD that may serve as validation sets. **Note the feasibility finding: no PRISMA-style
quantitative meta-analysis exists in either domain, and no review publishes a machine-readable numeric
table**, so reviews are usable for recall checking and query vocabulary only, never as ground truth.

> **Note on citation integrity.** No citation in this document is to be treated as final until its
> bibliographic details have been confirmed against the publisher of record. Preprints are labelled
> as preprints. Where verification failed, the item is omitted rather than approximated.

---

## Appendix B — What Changed from v1, and Why

| # | Change | Reason |
|---|---|---|
| 1 | Added Stage 0: simulation-based calibration and power analysis | n = 15–25 makes the v1 acceptance criterion statistically unattainable; this is the decisive fix |
| 2 | Replaced global SHD with **per-record causal impact** | Converts one number into *n* observations, restoring statistical power for the central claim |
| 3 | Added Stage 5: label-shuffling, high/low correction contrast, cross-domain weight transfer | Separates a real effect from a pipeline artefact |
| 4 | Rewrote the novelty claim | v1's claim is falsified by existing measurement-error literature |
| 5 | Single uncertainty signal → **three calibrated signals** | Directly answers published critiques of sampling-based uncertainty |
| 6 | Added dual annotation and Cohen's κ | The gold standard carries the paper's validity; v1's limitation was not survivable at review |
| 7 | Added five explicit baselines, with uniform-weight bootstrap as central | v1 named no baseline; "compared to what?" is the first reviewer question |
| 8 | Frozen open-weight models | Reproducibility; removes unpinnable hosted-model version dependence |
| 9 | Corpus target 15–25 → **≥ 60–100 per domain**, set by power analysis | Direct consequence of change 1 |
| 10 | Recalibrated acceptance criteria; added multiplicity control | v1's criteria were asserted, not derived |
| 11 | Replaced the venue list | AISTATS/UAI/NeurIPS D&B would reject this scope; they are also conferences, not impact-factor journals |
| 12 | Added PRISMA reporting and prose/table provenance tagging | Makes Gap 3 measurable rather than asserted |
| 13 | Added the **mode-collapse diagnostic** (RQ8, Stage 5 test 4) | Hamidieh et al. (ICLR 2026): dispersion *inverts* on confident errors. This is now the load-bearing threat, not a caveat |
| 14 | Signal C reframed as an ensemble **epistemic term**; ensemble raised from two models to ≥ 3 | The EU formulation and ensemble size are what the literature shows is required; pairwise agreement is not enough |
| 15 | N = 10 demoted from a design choice to a **measured** one (RQ7) | Ẓatuchin (2026) finds the paraphrase variance component near zero; N must be justified on this corpus, not asserted |
| 16 | Added semantic entropy and token-entropy conformal as baselines (B6) | Beating only "no uncertainty" is uninformative against the current state of the art |
| 17 | Added a self-consistency lineage correction to Section 2.2 | Wang et al. (2023) framed agreement as a *decoding* method for accuracy, never as calibrated uncertainty; the proposal must not inherit that overclaim |
| 18 | **Domain 2 replaced**: PVDF/HAp → halide perovskites validated against the Perovskite Database | Live counts: 122 works total, 90 journal articles, largest venue has 5 papers, no journal home. A literature ceiling cannot be fixed by effort |
| 19 | **Corpus feasibility corrected**: BDD yields 60–120 records, not 100+ comfortably | The substrate criterion collapses the pool from 2,372 to ~128, and that 128 is an upper bound |
| 20 | Cross-domain contrast redefined as **figure-bound vs tabulated**, not "homogeneous vs multi-technique" | The original contrast was confounded with domain size, and BDD's own Raman criterion is multi-technique |
| 21 | Stage 0 now generates **standardized** SEMs with controlled effect size, and audits varsortability | Kummerfeld et al. (2023): uncontrolled effect sizes make SHD uninterpretable. Reisach et al. (2021): standard generators are varsortable, flattering the learner |
| 22 | Added **SID** alongside SHD; bootstrap edge stability explicitly demoted to standard practice | Peters & Bühlmann (2015): SID "differs significantly" from SHD. Friedman et al. (1999): bootstrap stability is 25-year-old practice explicitly designed for low data — it cannot rescue a small sample |
| 23 | Novelty claim rewritten **again**, around the error *object* rather than the propagation | Blom et al. (UAI 2018) already propagate measurement-error bounds into constraint-based discovery. Only the i.i.d.-noise assumption distinguishes this work |
