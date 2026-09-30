# From Extraction Confidence to Causal Reliability

## A Simulation-Calibrated Framework for Uncertainty Propagation in LLM-Based Scientific Knowledge Extraction

**Manuscript draft v0.1 — Methods complete, Results pending**

Every numeric placeholder is written as `[[RQn.metric]]` and maps to a specific function in the
repository. No number in this file is invented. When the corresponding pipeline stage runs, each
placeholder is replaced by that function's output, and the mapping is what makes the substitution
mechanical rather than a rewriting exercise.

---

## Abstract

Large language models now extract quantitative data from scientific literature at high accuracy, and
that accuracy is reported in isolation: precision, recall and F1 against a hand-built gold standard,
with no reference to whether a given extraction error changes any downstream conclusion. Extracted
values are then treated as ground truth. We address both problems together. We introduce **causal
impact of extraction error**, an evaluation criterion defined per record as the Structural Hamming
Distance induced by correcting that record, which converts a single per-corpus quality number into a
per-record quantity that can be correlated with extraction uncertainty. We then ask whether per-value
extraction uncertainty — measured from three independent signals — predicts that causal impact, and
whether propagating the uncertainty changes the recovered structure relative to uniform weighting.
Because a study of this kind is only as credible as its error model, the framework is **calibrated
against synthetic data with a known ground-truth graph and controlled error injection** before being
applied to real literature; the calibration yields the attainable ceiling of any uncertainty metric on
this task, a power analysis that sets the required corpus size, and a price list for the failure mode
the recent literature identifies as most dangerous. Applied across boron-doped diamond electrodes and
halide perovskite photovoltaics — chosen to contrast figure-bound against tabulated extraction, and the
latter validated against an independently curated FAIR database rather than our own annotation — the
framework reports [[RQ2.auc]] ranking performance for extraction uncertainty against verified error,
and [[RQ4.r_impact]] between per-record uncertainty and per-record causal impact. Pre-registered
across all outcomes, including nulls.

---

## 1. Introduction

The growth of the scientific literature has outpaced any individual researcher's capacity to integrate
it. Automated extraction using large language models has emerged as the response, and it works: systems
now recover structured tabular data from materials-science papers at F1 scores approaching 97 %, and
the general shift from rule-based to LLM-based pipelines is essentially complete.

Three limitations persist across this body of work, and they are not independent.

**Extraction quality is evaluated in isolation.** Systems are scored by precision, recall and F1
against a gold-standard subset. This measures the extractor in a vacuum. An error that leaves every
downstream conclusion unchanged is scored identically to an error that reverses a causal conclusion,
even though only one of them matters. The consequence is that reported accuracy figures carry no
information about whether the extracted data can support the analyses it is intended to support.

**Extraction uncertainty is discarded.** Once a value is written to a database it is treated as
ground truth. But extraction is not deterministic: the same value may come back differently under
different prompt formulations, and some values are genuinely more ambiguous in the source text than
others. The reliability of any downstream statistical or causal claim is therefore disconnected from
the reliability of its inputs — and because measurement error is known to produce spurious edges in
structure learning, that disconnection is not hypothetical.

**Narrative prose is largely excluded.** The dominant application domain is structured tables. But
performance values, service lifetimes and failure thresholds are frequently reported inside paragraphs,
and figure-bound values are excluded almost entirely. The knowledge that automated pipelines currently
reach is therefore a biased sample of the knowledge that exists.

This paper addresses all three through a single framework with a fourth element that, we argue, is what
makes the other three credible. The framework is **calibrated against known ground truth before it is
applied to real literature**. Without that step, a study of this kind reports a correlation between two
quantities whose error structure is itself unknown, and no reader can distinguish a real effect from an
artefact of the pipeline.

### Contributions

1. **Causal impact of extraction error**, an evaluation criterion that scores extraction by its effect
   on downstream inference rather than in isolation, defined per record so that it is statistically
   usable — see Section 3.5.
2. **A simulation-calibrated uncertainty-propagation framework**, characterised against known ground
   truth across sample sizes, effect sizes and error regimes, yielding the attainable ceiling of the
   task, a power analysis, and a calibration curve from observed uncertainty to expected structural
   change — Section 3.1.
3. **Multi-signal uncertainty for scientific extraction**, combining paraphrase self-consistency, token
   entropy and a cross-model epistemic term, with an ablation establishing each signal's incremental
   value and a diagnostic for the failure mode that defeats dispersion alone — Sections 3.3 and 3.6.
4. **A dual-validated corpus**, with a hand-annotated BDD gold standard and a perovskite validation set
   built against an independently curated external database — Section 3.4.

We claim no novelty over the uncertainty signal itself. Paraphrase-induced variance as an uncertainty
measure is prior art, and we say so in Section 2. Our claim begins strictly downstream of the signal.

---

## 2. Related Work

### 2.1 LLM-based extraction from scientific literature

The field moved from rule-based pipelines to LLM-based extraction, and reported accuracies are now
high. MaTableGPT reports F1 near 97 % on structured tables from materials-science literature; Polak &
Morgan's ChatExtract reports roughly 90 % precision and recall; Dagdelen et al. (2024) is the canonical
demonstration of structured extraction at scale. Two facts about this literature matter here. First,
accuracy is measured in isolation — every system above is scored by precision, recall and F1 against a
gold subset, and none asks whether an extraction error changes any downstream conclusion. Second, none
of it quantifies extraction uncertainty at all, which makes the uncertainty question a genuine gap
rather than an unexamined one.

The one place we are not first: Khalighinejad et al. (2024) already apply self-consistency to
full-document extraction in materials and polymer literature. "Self-consistency for scientific
extraction" is therefore prior art and we do not claim it. What that work does not do — and what
remains open — is propagate the resulting uncertainty into a downstream inference and calibrate the
relationship against ground truth.

### 2.2 Uncertainty quantification for extraction

Self-consistency originates as a *decoding* method for accuracy (Wang et al., 2023) and was never
framed there as calibrated uncertainty; the lineage that treats sampling as an uncertainty signal is
semantic entropy (Kuhn, Gal & Farquhar, 2023) and its successor (Farquhar et al., 2024), which
explicitly restrict their target to confabulations. For extraction specifically, Kim et al. (2025) is
the closest published analogue to our work — LLM extraction with an LLM-as-judge verification stage and
conformal prediction over 10 000 clinical visits, describing state-of-the-art models as "notoriously
miscalibrated and overconfident". **It does not use dispersion; it uses conformal prediction.** Xu & Lu
(2025) likewise report that token-entropy measures with split conformal calibration outperform
self-consistency-based uncertainty quantification. We adopt conformal calibration for that reason.

Paraphrase-induced variance is used as an uncertainty measure in an independent line of work (Atalkar,
Sohani & Deogaonkar, 2026; Feng et al., 2025) and analysed favourably per item by Ali (2026). We
therefore make no novelty claim over the signal, and this section exists so that the claim is not
mistaken for one.

### 2.3 What sampling-based uncertainty can and cannot do

Ali (2026) separates two claims that are routinely conflated. Applying a Marchenko–Pastur random-matrix
test across five model families and three benchmarks, it finds that self-consistency gives **accurate
per-question uncertainty but no detectable cross-question structure**: within any single model, at most
one dimension rises above the noise edge, whereas a diverse 24-model ensemble surfaces four. The
distinction maps directly onto our design. We need per-value uncertainty, which this result supports; we
do not need cross-question correlated-error structure, which it shows a single model cannot supply. The
cross-model term is therefore not redundant padding — it is the mechanism the literature identifies as
the only route to ensemble-level structure.

### 2.4 Confident mode collapse

Hamidieh et al. (2026) identify the failure mode that would break a dispersion-only design outright:
self-consistency "collapses when models are overconfident and produce the same incorrect answer across
samples", and cross-model semantic disagreement is higher on incorrect answers precisely when aleatoric
uncertainty is low. For an extraction pipeline this is the error that matters most, because a
confidently wrong value is exactly the error a downstream causal analysis cannot absorb. The mechanism
is documented for aligned models generally by Xiao et al. (2025), who show that pre-trained models are
well calibrated and become poorly calibrated *after* preference alignment — which is the class of model
an extraction pipeline would use. We therefore promote the cross-model term to a primary defence and
make mode collapse its own pre-registered diagnostic (Section 3.6).

### 2.5 Measurement error in causal structure learning

This is prior art, not a gap. Blom et al. (2018) obtain an upper bound for the variance of random
measurement error from the covariance matrix and use it **as a correction for constraint-based causal
discovery** — uncertainty propagated into inference, published in 2018. Liu, Constantinou & Guo (2022)
state the same problem and add a post-hoc correction phase for five learners; Saeed et al. (2020) give a
method-of-moments estimator used with constraint-based discovery; Zhang et al. (2018) give
identifiability conditions. **The measurement-error problem is therefore studied, and any claim to have
discovered it would be false.**

What remains open is narrower. Every work above models uncertainty as i.i.d. statistical noise on an
otherwise measured variable — typically additive, zero-mean, homogeneous in variance. The error of an
LLM extraction pipeline is none of those things: it is correlated across records through shared prompts
and shared source papers, heterogeneous in variance across relations, not zero-mean, and reproducible
only under a frozen prompt set. Whether measurement-error theory transfers to that object is an open
empirical question, and it is the question our simulation grid is built to answer.

### 2.6 Robustness of causal discovery and the sample-size floor

The metrics have known limits. Structural Hamming Distance originates with Tsamardinos, Brown &
Aliferis (2006) — note that the `pcalg` reference list misprints the venue, and we do not propagate that
error. Peters & Bühlmann (2015) show that Structural Intervention Distance "differs significantly" from
SHD because it measures closeness in terms of the causal inference statements a graph supports, so
**SHD alone is not evidence that a causal claim is sound**; we report both. Bootstrap edge stability
dates to Friedman, Goldszmidt & Wyner (1999), whose stated motivation was the low-data regime, so it is
standard practice rather than a contribution and cannot rescue a small sample. Colombo & Maathuis
(2014) show PC is order-dependent, so run-to-run SHD variance can be an implementation artefact.

The sample-size evidence is unambiguous and not in our favour. Kummerfeld, Williams & Ma (2023) provide
the first power-analysis method for causal discovery and criticise the prior benchmark literature for
failing to control effect sizes. Scheines & Ramsey (2016) give concrete numbers: their grid begins at
n = 100, and at that size "the accuracy of FGES decays severely" once measurement error reaches roughly
17 %, with the decay slowing only at larger n — so small n and measurement error **compound rather than
substitute**. Every quantitative study we located begins at n = 100. We found no paper validating
structure recovery at n = 15–25 and no numeric minimum n for PC at all.

Real-data benchmarks carry their own caveats: the Sachs data's ground truth is a literature-curated
consensus rather than experimentally verified edges, and its interventions are assumed perfect despite
documented off-target effects (Sinha et al., 2021). CausalBench (Chevalley et al., 2023) finds that
interventional methods do not outperform observational ones on real data, contrary to synthetic
benchmarks — the same lesson the measurement-error literature teaches.

**Two gaps emerge.** No paper quantifies how unstable SHD or edge stability is *as a function of n*,
which is what our Stage 0 measures. And no paper applies information-extraction confidence to causal
structure learning: the measurement-error literature propagates statistical noise; nobody propagates
extraction uncertainty.

---

## 3. Methods

### 3.1 Simulation calibration and power analysis

The framework is characterised against known ground truth before it touches real literature. All
results in this subsection come from `stage0/`, which is reproducible from a fixed seed.

**Design.** Synthetic datasets are generated across a full factorial grid: sample size
*n* ∈ {20, 50, 100, 200, 500}; variables *d* ∈ {5, 6, 8}; graph topology ∈ {Erdős–Rényi, scale-free};
edge density ∈ {0.2, 0.4}; standardized effect size *r* ∈ {0.1, 0.3, 0.5}; extraction-error base rate
*p* ∈ {0, 0.05, 0.10, 0.20, 0.30}; error severity ∈ {0.10, 0.25, 0.50}; error assignment ∈
{ambiguity-correlated, independent, both}; and a confident-wrong rate ∈ {0, 0.05, 0.10, 0.20}.

**Standardized structural equation models.** Random-weight DAG generators are varsortable: marginal
variance increases along the causal order, which lets continuous learners appear to succeed by sorting
variances (Reisach et al., 2021). They also leave effect sizes uncontrolled, which makes any reported
SHD uninterpretable (Kummerfeld et al., 2023). We therefore adopt the standardized construction: every
edge weight is set to the same value and independent noise variances are solved so that every variable
has marginal variance exactly 1, making the edge weight equal to the standardized effect size and
eliminating varsortability by construction. Both properties are computed and asserted at run time
rather than assumed; the self test verifies that the population variances are 1 to within 1e-6 and that
measured varsortability sits at chance.

**Error model.** A latent ambiguity field *a* ~ Beta(2, 5) is drawn per cell, reproducing the right tail
of genuinely ambiguous values that real extraction corpora exhibit. Errors are then injected through
two channels: an ambiguity-linked channel where the per-cell error probability is proportional to *a*,
and a **confident-wrong channel** where errors are drawn independently of ambiguity. The second channel
models mode collapse, and it is the parameter that lets the simulation put a price on the failure mode
of Section 2.4 rather than merely acknowledging it.

**Outputs.** For each cell and replication we record the attainable ceiling — the correlation between
the true latent ambiguity and the realised error count, which no uncertainty metric can exceed — the
mean per-record causal impact, the ambiguity share of errors, and the varsortability statistic.

**Pipeline-integrity anchors.** Two conditions must hold before any empirical claim is made. At an error
rate of zero the mean causal impact must be exactly zero; otherwise the pipeline manufactures structure
from noise. With errors independent of ambiguity there must be no uncertainty–impact relationship;
otherwise the headline effect is an artefact. The analysis refuses to present results if either
anchor fails, and a third check verifies that the ceiling actually falls as confident-wrong errors are
introduced, so that an inert error axis cannot pass unnoticed.

**Power analysis.** Because real per-record error counts are bounded, skewed and tie-heavy, the
sample-size requirement is computed by Monte-Carlo under a Poisson error model with Spearman's
correlation rather than by the Gaussian Fisher-z formula; both are reported and the empirical figure is
the one that sets the corpus target.

### 3.2 Corpus construction

Search and screening follow PRISMA reporting with a documented flow diagram and screening log, and the
protocol was fixed before any search was run.

**Domain 1 — boron-doped diamond (BDD) electrodes.** Structured search across Scopus and Web of
Science, 2015 to the execution date, combining boron-doped diamond terms with Raman or doping-level
terms and with performance or failure terms. Inclusion requires peer-reviewed articles reporting
(i) Raman-derived doping or sp³/sp² information **and** (ii) at least one quantitative performance or
failure outcome, for a named substrate. The substrate criterion is the binding constraint: the query
mentioning titanium returns 128 articles against 2,372 for boron-doped diamond with "electrode", and
128 is an upper bound. The Domain 1 ceiling is therefore estimated at 60–120 records, and the
conjunction rate was measured by hand before the protocol was frozen.

**Domain 2 — halide perovskite solar cells.** Inclusion requires a device-level power conversion
efficiency with at least two of {Voc, Jsc, FF} and a named absorber composition. Records are matched
against the **Perovskite Database** (Jacobsson et al., 2022), an open FAIR-principled resource.

The domain pair was chosen for a specific contrast: BDD values are substantially prose- and
figure-bound, whereas perovskite performance values are overwhelmingly tabulated. Figure-bound
extraction is the harder and less-benchmarked task, and this is the axis under test. Each value is
tagged by provenance so that the contrast is a measured variable rather than an assertion.

### 3.3 Extraction and uncertainty quantification

**Model configuration.** Extraction uses three instruction-tuned models from independent families, with
frozen weights, reported revision hashes, quantisation, temperature, top-p and token limits. Hosted
models whose version changes mid-study are excluded because they make the result unreproducible. Where a
backend does not expose a seed we say so rather than implying determinism.

**Prompt set.** Paraphrases are constructed in four stages — generation, back-translation filtering, a
field-set audit at temperature 0, and a two-author semantic equivalence check — after which ten are
sampled from the survivors with a recorded seed. The full candidate set and the exclusion log are
released. The set is frozen before any data collection: a later wording change invalidates every
uncertainty value computed before it, so there are no minor edits after extraction begins.

**Signal A — paraphrase self-consistency.** For numeric variables, the coefficient of variation across
attempts after excluding values beyond 3 × MAD from the median (MAD scaled by 1.4826 so that the rule
approximates three sigma). Values whose mean is at or near zero return undefined rather than a large
number, because a large CV on a near-zero mean is an artefact of the denominator. For categorical
variables, `(1 − p_majority) / (1 − 1/k)`, so that variables with different numbers of levels are
comparable. The outlier exclusion rate is reported for every value: a value whose attempts scatter
widely enough to trip the rule is a value the source does not pin down, which is this study's own
evidence for its second research gap.

**Signal B — token entropy.** Mean token entropy over the extracted span, normalised by span length,
since raw entropy grows with length and would otherwise conflate a long answer with an uncertain one.

**Signal C — cross-model epistemic term.** Following Hamidieh et al. (2026), the gap between a model's
agreement with itself and its agreement with its peers, computed from the same sequence-similarity
metric for both so that the two terms share a scale. The sign convention is load-bearing: the term must
be large when intra-model agreement is high and inter-model agreement is low, which is the signature of
a model that is confidently and consistently wrong while its peers disagree.

**Composite and calibration.** The composite is a weighted mean over available signals with weights
renormalised to the signals present, and the number of contributing signals is recorded so that a value
resting on one signal is never presented as though it rested on three. Calibration uses **split
conformal prediction** on the gold-standard subset with a finite-sample quantile correction, and
isotonic regression as a comparison; both are cross-fitted so the composite is never scored on the data
that fitted it. Reliability diagrams and empirical coverage at nominal 90 % and 95 % are reported. The
pre-registered response to miscalibration — empirical coverage more than five points below nominal — is
to promote Signal B to primary and report the miscalibration as a result.

### 3.4 Gold standards

**BDD — hand annotation.** 150–200 values, sampled **stratified rather than randomly**: 35 % high
composite uncertainty, 35 % low, 20 % prose-embedded, 10 % range or series values. Stratifying
deliberately oversamples high-uncertainty values, which biases the marginal error rate upward; that is
acceptable because the gold standard estimates the *relationship* between uncertainty and error, not the
marginal rate, and the marginal rate is reported separately from the full corpus. Fixing this in advance
is what prevents the bias from becoming a silent one.

Correctness requires the right value, the right unit after normalisation, the right variable, and — for
ranges — that the range was not silently collapsed. The error taxonomy separates `ambiguous_source`,
where the paper genuinely does not pin the value down, from `hallucinated` and `wrong_value`, where the
paper is clear and the extractor failed. This distinction is what makes the aleatoric-versus-epistemic
result in Section 4 possible; collapsing it to a binary flag would destroy that result.

A second annotator codes a random 25 % of values **blinded to the model's uncertainty and to the other
annotator's decision**, and Cohen's κ is reported separately for the binary decision and the error-type
label, with a target of 0.70 and codebook revision on failure. Blinding is not optional: an annotator
who can see that the metric flagged a value as uncertain will tend to find it ambiguous, manufacturing
the correlation the study is testing.

**Perovskite — external validation.** Records are matched to the Perovskite Database on DOI and
composition, falling back to composition plus reported efficiency, with `match_method`,
`match_confidence` and `candidate_count` recorded for every record and a random sample of 30 matches
hand-verified before the pipeline runs. With an external gold standard the matching step, not the
extraction, is where validation can silently fail, so unmatched and ambiguous rates are reported as
headline numbers. Where a database value disagrees with the source paper, the paper governs and the
disagreement is logged. The database's own curation error rate is unknown and is stated as a floor on
the measured perovskite accuracy.

**The two domains are never pooled into a single accuracy figure.** They are measured against different
procedures, and averaging them would report the mean of two incompatible quantities.

### 3.5 Causal analysis and the causal impact criterion

**Structure learning.** Variables are restricted by domain knowledge to 5–8 per domain, and three
algorithms are run — PC, GES, and a continuous score-based method — so that any conclusion depending on
a single algorithm can be identified. Both SHD and SID are reported.

**Per-record causal impact.** For each record *i*, we correct that record alone, relearn the structure,
and record `CI_i = SHD(G, G_i)`, where *G* is the graph learned from the uncorrected data. This is the
central methodological device: it converts a single per-corpus quality number into *n* observations,
which is what gives the uncertainty–impact hypothesis any statistical power. A single global SHD cannot
be correlated with anything.

**Uncertainty propagation.** Confidence-weighted bootstrap resampling, `w_i = g(U_i)`, with the linear
and rank-based forms tested as a formal sensitivity analysis reported as a table rather than a
paragraph. The decisive comparison is against **uniform weights**: if uncertainty-weighted and
uniform-weighted resampling produce indistinguishable structures, the paper's practical recommendation
inverts, and that is a publishable outcome under our second hypothesis.

**Edge stability.** Bootstrap appearance frequency per edge, with the association between per-record
uncertainty and per-edge stability reported with cluster-bootstrapped confidence intervals. Edge
stability is reported as established practice, not as a contribution.

### 3.6 Null and adversarial tests

Four controls separate a real effect from an artefact.

1. **Label shuffling.** Uncertainty values are permuted across records and the pipeline re-run. A
   correlation of similar magnitude to the observed one indicates the effect is a property of the
   pipeline, not of the uncertainty.
2. **High-versus-low correction contrast.** Correcting high-uncertainty records must change the graph
   more than correcting low-uncertainty records. This is the strongest single piece of evidence
   available, because it depends on no model of how uncertainty is generated.
3. **Cross-domain weight transfer.** Weights estimated in one domain are applied to the other's data; a
   neutral result indicates the weighting scheme carries no domain-specific information.
4. **Mode-collapse diagnostic.** Among gold-standard-incorrect values we report the share produced with
   dispersion at or near zero, and whether the cross-model term flagged them. This is the most direct
   available check on the measurement assumption itself. The pre-registered reading: above 30 %
   collapsed means dispersion alone is not a sufficient instrument for extraction; below 10 %, with the
   cross-model term catching most cases, supports the multi-signal design.

### 3.7 Statistical analysis

Effect sizes are reported with 95 % confidence intervals. **All confidence intervals resample papers,
not values**: values within a paper share a document, a prompt set and often a single table, so their
errors are correlated, and resampling values would produce intervals that are too narrow. The
implementation refuses to return an interval from fewer than three papers rather than fabricating one.
Multiplicity across the hypothesis family is controlled by Holm–Benjamini–Hochberg. Minimum detectable
effect and minimum viable corpus size are fixed by the power analysis before any literature is screened,
and any deviation is reported as such.

---

## 4. Results

**Pending.** Each subsection below names the artifact that will populate it. Results are reported in
this order because each depends on the previous one being sound: if the calibration fails, the
empirical numbers are not interpretable, and the paper says so rather than reporting them anyway.

### 4.1 Pipeline integrity
`stage0/analysis.py` integrity anchors. Both must pass before Section 4.3 is reported.

### 4.2 Attainable ceiling and the cost of mode collapse
`stage0/analysis.py` → `attainable_ceiling`, `mode_collapse_section`.
The ceiling as a function of sample size and error rate; the fall in ceiling as confident-wrong errors
are introduced; the measured ambiguity share of errors.

### 4.3 Ground-truth causal impact curve
`stage0/analysis.py` → `impact_curve`. Mean per-record SHD against injected error rate, by effect size.

### 4.4 Power analysis and the corpus decision
`stage0/analysis.py` → `power_section`. Minimum n per effect size, and the resulting corpus target.

### 4.5 Corpus and extraction quality
`analysis/empirical.py` → `flatten_records`, `exclusion_rate_report`, plus the PRISMA flow.
Includes the Domain 1 conjunction rate, the perovskite matching and ambiguous rates, and κ for the dual
annotation.

### 4.6 Validity of the uncertainty metric (RQ2)
`analysis/empirical.py` → `rq2_uncertainty_vs_error`. AUC with cluster-bootstrapped CI; correlation with
error; and the aleatoric-versus-epistemic separation, which is where the substantive finding about what
the metric measures will appear.

### 4.7 Conformal calibration
`extraction/uncertainty.py` → `SplitConformalCalibrator.evaluate`, `reliability_bins`.
Empirical coverage against nominal, and the reliability diagram.

### 4.8 Mode collapse in real data (RQ8)
`analysis/empirical.py` → `rq8_mode_collapse`. Collapsed share, restricted to epistemic errors, and the
cross-model catch rate.

### 4.9 Causal impact and propagation (RQ4, RQ5)
`stage0/impact.py` joined to real records. Per-record impact against uncertainty; weighted versus
uniform resampling; edge stability.

### 4.10 Null and adversarial tests
`stage0/impact.py` → `placebo_test`, `high_low_contrast`; plus the cross-domain weight transfer.

### 4.11 Cross-domain comparison (RQ6)
`analysis/empirical.py` → `cross_domain_comparison`. The two domains side by side, never pooled, plus the
value-location contrast.

---

## 5. Discussion

**Pending results.** The discussion is structured around the pre-registered hypotheses rather than
around whatever the numbers turn out to be, so that the interpretation cannot be written after the fact.

Under the first hypothesis — high-uncertainty records associate with unstable edges and elevated causal
impact — the conclusion is that uncertainty propagation is a necessary rather than optional component of
causal inference on automatically extracted data, and the practical recommendation is a specific
weighting scheme with a measured effect size.

Under the second — no significant association — the conclusion is the opposite and equally useful:
causal inference on this class of extracted data is robust to extraction noise within the observed
range. This is a reassurance result, not a failure, and it requires the confidence interval to exclude
the substantial-effect threshold for the absence to be statistically supported.

Under the third — a domain-dependent relationship — the contribution is a diagnostic criterion
identifying when propagation is required, expressed in terms of measurable structural properties of the
data rather than of the domain's name.

A fourth outcome deserves separate treatment because it is the one most likely to occur and least likely
to be reported: if the uncertainty metric tracks source ambiguity but not hallucination, then
dispersion-based uncertainty is a measure of *text clarity* rather than of *extraction reliability*, and
the field's growing reliance on it should be qualified accordingly. Our taxonomy is designed to make
this outcome visible, and Section 4.6 reports it whether or not it flatters the framework.

---

## 6. Limitations

The full list is in the proposal; the four that a reader should weigh most heavily:

**The sample-size floor is real and we are below it by design.** Every quantitative study in the
causal-discovery robustness literature begins at n = 100. Our corpus is bounded by the literature at
60–120 records in Domain 1. Where n falls below the power analysis's requirement, the study is a
**stress test at the infeasible extreme**, and we report it as such rather than as an adequate design.

**The external gold standard introduces a failure mode that is invisible from our side.** A wrong
paper-to-record link is scored as an extraction error against the pipeline. We control it with recorded
matching confidence and hand verification of a 30-match sample, but a residual rate below the sampling
resolution cannot be excluded.

**Simulation calibration makes the simulation fair, not representative.** Standardized effect sizes and
varsortability control remove two documented artefacts; they cannot establish that our injected error
model resembles real extraction errors.

**Two gold standards, two procedures.** BDD accuracy is measured against hand annotation, perovskite
accuracy against a community-curated database with an unknown curation error rate. The two figures are
reported side by side and never averaged.

---

## 7. Conclusion

**Pending results.** The conclusion will state which of the three pre-registered outcomes obtained, what
the measured cost of confident mode collapse was, and what the calibrated recommendation is for
practitioners deciding whether to propagate extraction uncertainty. It will also state what the study
cannot conclude: the sample sizes here cannot identify true causal structure, and no result in this
paper should be read as a claim about the underlying science of either domain.

---

## Data and code availability

Pipeline code, the frozen prompt sets, extracted records, gold-standard annotations with annotator
identity masked, simulation configurations and a container definition will be released on publication.
Raw extraction attempts are released in full: without them the dispersion cannot be recomputed by a
reader, and an unverifiable uncertainty measurement is worth little.

---

## Figure and table plan

| # | Type | Content | Source |
|---|---|---|---|
| Fig. 1 | Schematic | The pipeline: extraction → three signals → calibration → weighted causal learning → per-record impact | — |
| Fig. 2 | Line | Attainable ceiling against error rate, by sample size | `attainable_ceiling` |
| Fig. 3 | Line | Ceiling against confident-wrong rate — the price of mode collapse | `mode_collapse_section` |
| Fig. 4 | Line | Ground-truth causal impact curve against injected error rate, by effect size | `impact_curve` |
| Fig. 5 | Curve | Power against n per effect size, with the corpus target marked | `power_section` |
| Fig. 6 | Reliability diagram | Predicted uncertainty against observed error rate, with conformal coverage | `reliability_bins` |
| Fig. 7 | Scatter | Per-record uncertainty against per-record causal impact | `impact_vs_uncertainty` |
| Fig. 8 | Bar | Collapsed versus diffuse error share, by error class | `rq8_mode_collapse` |
| Fig. 9 | Bar | Cross-domain comparison, side by side and never pooled | `cross_domain_comparison` |
| Tab. 1 | Table | Simulation design grid | `run_stage0.py` |
| Tab. 2 | Table | PRISMA flow counts | `prisma_search.md` |
| Tab. 3 | Table | Extraction configuration: models, revisions, decoding | `prompts_and_uncertainty.md` |
| Tab. 4 | Table | κ for the dual annotation, binary and taxonomy | `annotation_codebook.md` |
| Tab. 5 | Table | Signal ablation: each signal alone and in combination | `uncertainty.py` |
| Tab. 6 | Table | Weighting sensitivity: linear, rank, exponential, uniform | `run_stage0.py` |
| Tab. 7 | Table | Null and adversarial test results | `impact.py` |

