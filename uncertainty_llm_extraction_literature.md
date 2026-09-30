# Literature Search: Uncertainty Quantification in LLM Information Extraction from Scientific Text

**Scope:** how LLM uncertainty is estimated, how well those estimates are calibrated, and critiques of
self-consistency / sampling-based uncertainty — with reference to a proposal that measures per-value
extraction uncertainty by running the same extraction N=7–10 times under **paraphrased prompts** and
computing dispersion (CV for numbers, 1 − majority-agreement for categories).

**Verification standard applied:** every entry below was retrieved and read by me. Venue/year/authors come
from the publisher or repository record. Anything I could not read is quarantined in the final section.
Preprints are labelled. Search-date evidence suggests current literature extends through **September 2026**
(ACL Anthology last-built stamp 30 Sep 2026; Zenodo record dated 1 Sep 2026); the newest items cited are 2026.

---

## Headline result (read this first)

The brief assumed that recent literature strongly challenges the assumption that sampling dispersion tracks
extraction error. **That assumption is half right, and the seed paper does not say what the brief claims.**
The accurate picture is:

1. **Sampling dispersion does track per-question uncertainty, fairly well.** The seed paper itself
   (Ali, 2026) concludes *"Self-consistency gives accurate per-question uncertainty"* and reports a
   split-half per-question pass-rate correlation of **r = 0.994**. This **supports** the proposal's design.
2. **The real threat is a different, well-evidenced failure mode: "confident mode collapse."** When a model
   is committed to a wrong answer it produces the *same* wrong answer every time, so dispersion is near zero
   and the uncertainty signal silently inverts. This is documented in the ICLR 2026 paper by Hamidieh et al.,
   in Feng et al. (EMNLP 2025 Findings), and in the Spanda preprint. This is the strongest threat to the
   proposal, and it is *not* the mechanism the brief anticipated.
3. **Paraphrase-only variance is a weak and partly mis-attributed signal.** Żatuchin (2026) decomposes
   response variance into resampling / paraphrase / model / language components and finds paraphrase-to-
   paraphrase variance is *near zero* and that repeats past the fifth buy almost nothing (0.0003 relative-error
   variance). That directly threatens the proposal's operating point (N = 7–10 paraphrased runs).

---

## Self-consistency and its critiques

**Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023).
"Self-Consistency Improves Chain of Thought Reasoning in Language Models." ICLR 2023.**
arXiv:2203.11171 · https://arxiv.org/abs/2203.11171 · (v1 2022, ICLR camera-ready 2023)
The original self-consistency work. Samples a diverse set of reasoning paths and marginalises by majority
vote. Reports GSM8K +17.9%, SVAMP +11.0%, AQuA +12.2%, StrategyQA +6.4%, ARC-challenge +3.9%. Note: this is
posed as a **decoding/accuracy** method — majority voting for a better answer — not as a calibrated
uncertainty estimator. The proposal's lineage should cite it as the origin of the "agreement ⇒ confidence"
intuition, and should be honest that the original paper never framed agreement as calibrated uncertainty.
*Relation to proposal: background / weak support.*

**Kuhn, L., Gal, Y., & Farquhar, S. (2023). "Semantic Uncertainty: Linguistic Invariances for Uncertainty
Estimation in Natural Language Generation." ICLR 2023 (Spotlight).**
arXiv:2302.09664 · https://arxiv.org/abs/2302.09664
Introduces **semantic entropy** — entropy computed over *meanings* rather than token sequences, to handle
semantic equivalence. Unsupervised, single-model, no model modification. Reports via ablation that semantic
entropy is more predictive of model accuracy on QA than comparable baselines. This is the canonical
"sampling + aggregation" uncertainty estimator and the direct methodological ancestor of the proposal's
majority-agreement term. *Relation to proposal: supporting precedent for sampling-based per-item uncertainty.*

**Farquhar, S., Kossen, J., Kuhn, L., & Gal, Y. (2024). "Detecting hallucinations in large language models
using semantic entropy." *Nature* 630(8017), 625–630.**
DOI 10.1038/s41586-024-07421-0 · https://doi.org/10.1038/s41586-024-07421-0
(Record verified at Oxford ORA: https://ora.ox.ac.uk/objects/uuid:0653d09e-9368-4eb1-98bb-50d9dda7d3e5)
Peer-reviewed, version of record. Develops entropy-based uncertainty estimators at the level of meaning to
detect **confabulations** — deliberately a *subset* of hallucinations, namely arbitrary and incorrect
generations. Explicitly claims robustness across datasets/tasks with no task-specific data. Crucially, the
definitional restriction to *arbitrary* (i.e. high-variance) errors is exactly the boundary of the proposal's
assumption: semantic entropy, like the proposal's dispersion, is designed to catch arbitrary errors and is
silent about systematic errors. *Relation to proposal: support for the mechanism, and an implicit limit.*

**Kossen, J., Han, J., Razzak, M., Schut, L., Malik, S., & Gal, Y. (2024). "Semantic Entropy Probes:
Robust and Cheap Hallucination Detection in LLMs."** arXiv:2406.15927 · https://arxiv.org/abs/2406.15927
(preprint; first three authors contributed equally)
Approximates semantic entropy from the hidden states of a *single* generation, removing the 5–10× sampling
overhead. States that SEPs "retain high performance for hallucination detection and generalize better to
out-of-distribution data than previous probing methods." Relevant to the proposal two ways: it is the natural
efficiency baseline the proposal will be compared against, and it demonstrates that most of the signal in
sampling-based entropy is recoverable from a single forward pass — which raises the question of what the
N=7–10 sampling budget is actually buying. *Relation to proposal: threat (efficiency/cost critique).*

**Ali, I. (2026). "Stochastic Sampling is Epistemically Shallow: The Dimensionality Gap Between Temperature
Variation and Model Diversity in LLMs." 2nd Workshop on Epistemic Intelligence in ML (EIML@ICML 2026), Seoul.
** arXiv:2607.20464 (preprint, submitted 18 May 2026) · https://arxiv.org/abs/2607.20464
**This is the first seed source; it exists and verifies. But its actual claim is the opposite of what the
brief assumed.** Setting: 500 MMLU questions, one model sampled K=100 times at τ=1, versus an ensemble of
24 LLMs at τ=0. A Marchenko–Pastur random-matrix test separates signal from sampling noise. Findings:
(i) *within* a single model, at most one dimension rises above the noise edge — the run×question correctness
matrix is statistically indistinguishable from independent Bernoulli draws, across five model families
(Qwen2.5-7B, Mistral-7B-v0.3, SmolLM2-1.7B, Phi-3-mini, Llama-3-8B) and three benchmarks (MMLU, HellaSwag,
GSM8K); (ii) *across* models, four eigenvalues clear the noise edge (matched-difficulty Bernoulli null
produced at most one in 500 draws). Two sentences from the paper matter most for the proposal: the abstract's
*"Self-consistency gives accurate per-question uncertainty but no detectable cross-question structure"*, and
Section 3.4's split-half **r = 0.994** on per-question pass rates, described as "successive samples are
independent draws from a fixed per-question Bernoulli."
*Relation to proposal:* **SUPPORTS** the per-value/per-question part of the design (dispersion is a valid
per-question estimate). **CAVEAT** it cannot be used as a substitute for a diverse ensemble, and it carries no
cross-question correlated-error structure — so you still need a held-out calibration/gold set for any claim
about error rates, and you cannot generalise per-value dispersion into a document- or corpus-level error
budget. The brief should be corrected: this paper is not evidence against dispersion tracking extraction error.

**Hamidieh, K., Thost, V., Gerych, W., Yurochkin, M., & Ghassemi, M. (2026). "Complementing
Self-Consistency with Cross-Model Disagreement for Uncertainty Quantification." ICLR 2026 (poster).**
https://iclr.cc/virtual/2026/poster/10007682 · OpenReview: https://openreview.net/forum?id=lOoRJo8xWy
**This is the single most important threat to the proposal.** The authors state plainly: *"Recent works
routinely rely on self-consistency to estimate aleatoric uncertainty (AU), yet this proxy collapses when
models are overconfident and produce the same incorrect answer across samples."* They show cross-model
semantic disagreement is higher on incorrect answers precisely when AU is low, and introduce an epistemic
uncertainty (EU) term computed as the gap between inter-model and intra-model sequence-semantic similarity,
with total uncertainty TU = AU + EU. Across five 7–9B instruction-tuned models and ten long-form tasks, TU
improves ranking calibration and selective abstention over AU alone, and EU "reliably flags confident failures
where AU is low."
*Relation to proposal:* **THREAT (primary).** It names the exact failure mode the proposal must rule out:
near-zero dispersion on a confidently wrong extraction. It also implies the fix is *model diversity*, not
merely *prompt diversity* — which is a design change the proposal should consider before freezing the method.
Caveat for fairness: their setting is long-form generation, not per-field scientific extraction, so the
magnitude of the effect in the proposal's setting is an open empirical question the proposal could itself answer.

**Feng, Y., Htut, P. M., Qi, Z., Xiao, W., Mager, M., Pappas, N., Halder, K., Li, Y., Benajiba, Y., &
Roth, D. (2025). "Rethinking LLM Uncertainty: A Multi-Agent Approach to Estimating Black-Box Model
Uncertainty." EMNLP 2025 Findings.** arXiv:2412.09572 · https://arxiv.org/abs/2412.09572
States the threat in a form even closer to the proposal's mechanism: *"an LLM may confidently provide an
incorrect answer to a target query, yet give a confident and accurate answer to that same target query when
answering a knowledge-preserving perturbation of the query."* Existing methods that gauge uncertainty through
self-consistency on the target query "can be misleading"; the authors attribute the discrepancy to
suboptimal retrieval of parametric knowledge under contextual bias. Their DiverseAgentEntropy uses multi-agent
interaction across diverse *query variations* and is reported to outperform self-consistency-based techniques
on hallucination detection.
*Relation to proposal:* **THREAT (and also an opportunity).** This is a direct empirical demonstration that
sampling a fixed prompt under-measures true uncertainty. Note the constructive half: it validates
*perturbing the query* as a remedy — i.e. the proposal's own use of paraphrased prompts is directionally
right. The proposal can position itself as the scientific-extraction instance of this idea, provided it tests
whether paraphrase diversity actually recovers the signal in its domain.

**Nayak, B. (2026). "Spanda: Zero-Cost Lexical Entropy Matches Neural Semantic Uncertainty — Until Frontier
Models Break It."** Zenodo preprint, v1, published 1 Sep 2026 · DOI 10.5281/zenodo.22233648 ·
https://zenodo.org/records/22233648 · code: https://github.com/Adarshent/Spnda
**Preprint — not peer-reviewed; treat the numbers as provisional.** Introduces a zero-cost normalised lexical
metric (R_sc) evaluated across models from 1.5B to 120B. Reports that for mid-sized models (7B–27B) R_sc reaches
AUROC 0.889, matching neural semantic entropy without NLI overhead. Then reports the key claim: on frontier
models (120B+), "intense RLHF alignment induces 'Confident Mode Collapse'—the model hallucinates the exact same
incorrect answer across all paths, causing AUROC to invert to 0.091 and bypassing self-consistency assumptions."
*Relation to proposal:* **THREAT, but weak evidence.** The mechanism it names is exactly the fatal case for the
proposal (all N samples agree on the wrong value ⇒ dispersion 0 ⇒ "certain" flag). However this is a single-author
non-peer-reviewed preprint with an extreme reported effect (AUROC 0.889 → 0.091). I would cite it as
*consistent with* the better-established Hamidieh et al. and Feng et al. findings, and explicitly flag it as
an unreviewed preprint, rather than resting an argument on it. Also note "confident mode collapse" is a vivid
label, not an established term in the peer-reviewed literature as far as I could verify.

**Kunitomo-Jacquin, L., Marrese-Taylor, E., Fukuda, K., & Hamasaki, M. (2026). "Evidential Semantic Entropy
for LLM Uncertainty Quantification." EACL 2026 (Long Papers), pp. 7107–7122.**
https://aclanthology.org/2026.eacl-long.334/ · DOI 10.18653/v1/2026.eacl-long.334
Peer-reviewed. A technical critique of the sampling-based semantic-entropy family, not of its concept:
*"these estimation methods fail to account for the effects of the semantics that are possible to be obtained as
answers, but are not observed in the sample. This is a significant oversight, since a heavier tail of
unobserved answer probabilities indicates a higher level of overall uncertainty."* Proposes EVSE, which uses
evidence theory to represent total ignorance from unobserved answers plus partial ignorance from semantic
relationships among observed answers; reports significant improvement in uncertainty quantification.
*Relation to proposal:* **THREAT (methodological).** This is a peer-reviewed, precisely-targeted critique of
exactly the proposal's estimator. Finite-sample dispersion over N=7–10 draws is an estimate of the *observed*
distribution only; it assigns low uncertainty when the model's probability mass sits on answers that never
appear in the sample. With N = 7–10 this concern is materially worse than in the N = 10–20 regimes the
semantic-entropy literature typically uses. The proposal needs to address small-N sample-coverage bias.

**Zatuchin, D. (2026). "Where Does the Noise Come From? A Variance-Components Decomposition of
Non-Determinism in LLM Brand Answers."** arXiv:2607.13304 (preprint, 14 Jul 2026) ·
https://arxiv.org/abs/2607.13304
**Preprint.** A crossed random-effects (generalizability-theory) decomposition partitioning response variance
into four separable sources: within-prompt resampling, prompt paraphrase, model identity, and query language.
Corpus: 12,933 responses, 20 brands, 8 languages, 3 models, with a 1,435-cell stability subset resampled ~5×.
Findings: once a cell term isolates pure resampling, **resampling is 34.8% of variance**, brand-in-context
interaction 29.6%, query language 26.5%, brand-by-language 8.6%, while **brand-by-model and brand-by-prompt are
near zero**. Critically: *"Per unit of query budget, adding languages and models reduces relative-error
variance far more than adding repeats: a repeat past the fifth reduces it by only 0.0003."*
*Relation to proposal:* **THREAT (design/operating point).** Although the domain is brand answers, not
scientific extraction, this is the closest thing I found to a direct empirical audit of the proposal's exact
design choice. It says: (a) **paraphrase (prompt) variance is a near-zero variance component** compared with
resampling and model identity, so paraphrasing may not add the independent information the proposal hopes for;
(b) **~5 repeats is where returns flatten**, so N = 7–10 paraphrased runs is roughly 5 useful resamples plus
wasted budget. The proposal should either justify why scientific extraction differs or reallocate budget to
model/decoding diversity. Domain-transfer caveat applies and should be stated.

---

## Conformal and logit-based methods

**Kim, E., Foty, R., Shrestha, M., & Seyfert-Margolis, V. (2025). "Conformal Prediction and Verification of
Large Language Model Extractions in EHR Data." *Proceedings of the AAAI Symposium Series* 7(1), 539–546.**
DOI 10.1609/aaaiss.v7i1.36929 · https://ojs.aaai.org/index.php/AAAI-SS/article/view/36929
**This is the second seed source; it exists and verifies.** Peer-reviewed symposium proceedings, 2025 AAAI Fall
Symposium Series, SECURE-AI4H track. Framework: (i) LLM extraction of medical entities/concepts from clinical
narratives with LLM-as-a-judge verification; (ii) probabilistic calibration to quantify extraction confidence;
(iii) conformal prediction for finite-sample guarantees on error rates for *accepted* extractions. Evaluated on
10k clinical visits across 898 clinical practices and three EHR systems. States that the approach "can provide
assurances that the future expected proportion of accepted but incorrect extractions remains below a
pre-specified risk level," and that it "illuminates the miscalibrations present in state-of-the-art LLM models."
*Relation to proposal:* **THREAT (by offering a better-grounded alternative) and a template to imitate.**
This is the single closest published analogue to what the proposal wants to do — per-extraction uncertainty in
structured extraction from documents — and it does not use sampling dispersion. It uses conformal prediction,
which yields a *distribution-free finite-sample coverage guarantee*, at the cost of requiring a labelled
calibration set and exchangeability. The proposal's dispersion score, by contrast, has no coverage guarantee.
The strongest available improvement to the proposal is to keep dispersion as a *ranking feature* and wrap it in
split conformal prediction to obtain a risk-controlled acceptance threshold. Also note the paper explicitly
calls SOTA LLMs miscalibrated — supporting the brief's suspicion, though via EHR data rather than scientific text.

**Xu, B., & Lu, Y. (2025). "TECP: Token-Entropy Conformal Prediction for LLMs."**
arXiv:2509.00461 (preprint, v1 30 Aug 2025, v2 5 Sep 2025) · https://arxiv.org/abs/2509.00461
**Preprint.** Introduces Token-Entropy Conformal Prediction: token-level entropy as a "logit-free,
reference-free" uncertainty measure integrated into a split conformal prediction pipeline to build prediction
sets with formal coverage guarantees. Framed for black-box settings where internal signals are inaccessible.
Evaluated across six LLMs and two benchmarks (CoQA, TriviaQA); reports reliable coverage and compact prediction
sets, and — the sentence that matters for the proposal — states the method **"outperform[s] prior
self-consistency-based UQ methods."**
*Relation to proposal:* **THREAT.** An explicit, direct claim that a token-entropy + conformal approach beats
self-consistency-based UQ. It also undercuts one defence the proposal might have: the proposal may argue
sampling-based methods are preferable because they need no logit access, but TECP is explicitly designed to
need no logit access either (token entropy from sampled generations) while adding coverage guarantees.
Caveats: preprint; the benchmarks are open-ended QA, not structured scientific extraction; and "token entropy"
still requires sampling or at least a distribution, so it is not free. The proposal should benchmark against
this, or at minimum argue why CV over paraphrases is preferable to token entropy + CP in its setting.

**Kotte, V. (2026). "PASC: Pipeline-Aware Conformal Prediction with Joint Coverage Guarantees for Multi-Stage
NLP and LLM Pipelines."** arXiv:2605.18812 (preprint, 12 May 2026) · https://arxiv.org/abs/2605.18812
**Preprint, single author.** Reduces multi-stage joint coverage (NER → NED → entity typing; RAG; agent chains)
to a single scalar conformal problem on the joint maximum nonconformity score, giving a finite-sample
distribution-free guarantee that all K stages are simultaneously covered with probability ≥ 1 − α, nearly tight
up to 1/(n+1). On a three-stage NER→NED→entity-typing pipeline over CoNLL-2003: 96.4% end-to-end coverage vs
93.4% (Bonferroni) and 86.5% (independent CP) at identical average prediction-set size (1.083). Under
distribution shift to WNUT-17 and WikiNEuRal, independent CP collapses to 59% while PASC holds target coverage.
*Relation to proposal:* **THREAT (scope/ambition).** If the proposal's scientific-extraction pipeline has
multiple stages (e.g. table detection → cell linking → value normalisation → unit conversion), per-value
dispersion computed stage-locally has no end-to-end guarantee and errors compound. This paper shows the
state of the art now provides joint multi-stage guarantees. The proposal should either scope itself to a
single stage or adopt a pipeline-aware guarantee.

**Supporting context — conformal prediction foundations.** The proposal will need the standard references
(Vovk et al.; Angelopoulos & Bates' gentle introduction; Lei et al. on conformal prediction sets). **I did not
separately verify these primary records in this search**, so I am not listing full citations for them here;
they should be added from a direct retrieval before submission rather than copied from this report.

---

## Calibration evidence

**Kadavath, S., Conerly, T., Askell, A., Henighan, T., Drain, D., Perez, E., Schiefer, N., Hatfield-Dodds, Z.,
DasSarma, N., Tran-Johnson, E., Johnston, S., El-Showk, S., Jones, A., Elhage, N., Hume, T., Chen, A., Bai, Y.,
Bowman, S., Fort, S., Ganguli, D., Hernandez, D., Jacobson, J., Kernion, J., Kravec, S., Lovitt, L.,
Ndousse, K., Olsson, C., Ringer, S., Amodei, D., Brown, T., Clark, J., Joseph, N., Mann, B., McCandlish, S.,
Olah, C., & Kaplan, J. (2022). "Language Models (Mostly) Know What They Know."**
arXiv:2207.05221 (preprint, v1 Jul 2022, v4 Nov 2022) · https://arxiv.org/abs/2207.05221
**Preprint** (widely cited; the brief's "Kadavath et al." line). Findings relevant here: larger models are
well-calibrated on diverse multiple-choice and true/false questions *when provided in the right format*;
"P(True)" self-evaluation — asking the model to judge the probability its own proposed answer is correct —
shows encouraging performance, calibration, and scaling; **performance at self-evaluation further improves when
models are allowed to consider many of their own samples** before predicting the validity of one specific
possibility; and calibration of "P(IK)" (probability that "I know") is weak and struggles to generalise to new
tasks. *Relation to proposal:* **SUPPORT, with an important nuance.** This is the strongest classic evidence
that sampling/self-evaluation carries real uncertainty signal, which supports the proposal's premise. But note
the sampling is used to *inform a learned/elicited judgement*, not as a direct dispersion score — the paper does
not show that raw dispersion is calibrated, only that *access to samples* improves a self-evaluation. The
proposal should not over-claim this citation.

**Xiong, M., Hu, Z., Lu, X., Li, Y., Fu, J., He, J., & Hooi, B. (2024). "Can LLMs Express Their Uncertainty?
An Empirical Evaluation of Confidence Elicitation in LLMs." ICLR 2024.**
arXiv:2306.13063 · https://arxiv.org/abs/2306.13063 · code: https://github.com/MiaoXiong2320/llm-uncertainty
**The most directly useful calibration comparison for the proposal.** Peer-reviewed at ICLR 2024. Defines a
framework of three components — prompting strategies to elicit **verbalized** confidence, **sampling** methods
for multiple responses, and **aggregation**/consistency techniques — and benchmarks them for calibration and
failure prediction across five dataset types (commonsense, arithmetic reasoning, etc.) and five LLMs including
GPT-4 and Llama-2 Chat. Key reported insights: (1) LLMs **verbalizing confidence tend to be overconfident**,
potentially imitating human confidence expression; (2) calibration and failure prediction improve as model
capability scales; (3) human-inspired prompts, multi-response consistency, and better aggregation mitigate
overconfidence; (4) **white-box methods (log-probability based) perform better than black-box, but the gap is
narrow — 0.522 to 0.605 in AUROC**; and (5) **no technique consistently outperforms the others**, and all
methods struggle on tasks requiring professional knowledge.
*Relation to proposal:* **MIXED — supports sampling-based UQ, and is a direct warning about the proposal's target
domain.** Point (3) supports "sampling + aggregation" as a legitimate calibrated-confidence route; point (4)
says the sampling/black-box route is only narrowly worse than log-probability, which is a good defence for a
method that avoids logit access. But point (5) is a serious caution: the proposal's setting — scientific
extraction — is precisely a "professional knowledge" task, the regime where the paper reports every method
struggles. The proposal should expect weak calibration and should design its evaluation to detect that rather
than assume it away.

**Xiao, J., Hou, B., Wang, Z., Jin, R., Long, Q., Su, W. J., & Shen, L. (2025). "Restoring Calibration for
Aligned Large Language Models: A Calibration-Aware Fine-Tuning Approach." ICML 2025.**
arXiv:2505.01997 · https://arxiv.org/abs/2505.01997 · DOI 10.48550/arXiv.2505.01997
Peer-reviewed (ICML 2025). **This is the "RLHF makes models miscalibrated" line the brief asked for.**
States directly: *"while the pre-trained models are typically well-calibrated, LLMs tend to become poorly
calibrated after alignment with human preferences."* Traces the cause to a "preference collapse" issue in
alignment that generalises to the calibration scenario, causing overconfidence and poor calibration. Splits
models into "calibratable" and "non-calibratable" regimes by ECE bounds, and proposes (a) calibration-aware
fine-tuning in the calibratable regime and (b) an EM-algorithm-based ECE regularisation in the non-calibratable
regime. *Relation to proposal:* **THREAT to the reliability of any uncertainty estimate from an aligned
model — and therefore to the proposal's core assumption.** The proposal will use instruction-tuned, RLHF'd
models (that is the only realistic choice). If alignment collapses diversity *and* inflates confidence, then
dispersion is systematically deflated and the proposal's "high dispersion ⇒ likely error" mapping is
mis-specified in the direction that matters most (false confidence). This is the theoretical mechanism behind
the empirical "confident mode collapse" reports above, and citing it gives the proposal a principled reason to
include an alignment-aware calibration step or an explicit low-dispersion sanity check.

**Kim, H., & Kang, P. (2026). "Same Answer, Different Confidence: Protocol Sensitivity in LLM Confidence
Calibration."** arXiv:2605.27752 (preprint; v1 26 May 2026, v3 7 Aug 2026) · https://arxiv.org/abs/2605.27752
**Preprint** — note the earlier search hit indexed a variant title ("Asking Is Not Enough: Protocol Sensitivity
in LLM Confidence Calibration"); the arXiv record as fetched carries the title above. Poses the question
"is verbalized confidence better calibrated than token likelihood?" and answers: *it depends on how the token
likelihood is measured.* Audits twelve published comparisons and finds **five never state the choice**. Holding
the prediction event fixed (the model's own answer plus its correctness label) and scoring that same answer
both as a plain query and inside the confidence prompt, they find the ranking of signals flips in **4 of 12
settings under ECE and 9 of 12 under AUROC** across four QA datasets and three 7–8B Instruct models. They note
the AUROC flip cannot be rescaling, since AUROC is invariant to common order-preserving transformations — the
items are *ordered differently*. Two further protocol choices behave the same way (substituting the reference
string for the model's own answer; reading the first answer token instead of the answer span). Crossing three
answer slots, two scored strings, and two readouts yields twelve operational variants that leave the *sign* of
the ECE comparison undetermined in 6 of 12 settings. Verbalized confidence is also sensitive to answer
formulation: replacing an accepted TriviaQA alias with the canonical reference raises confidence by 0.072
although both answers are correct. Conclusion: comparing signals "requires an explicit answer, context, and
evaluation protocol."
*Relation to proposal:* **THREAT (methodological / reproducibility).** This is the strongest evidence I found
that published claims about which confidence signal is best calibrated are **not robust to protocol choices**.
Two direct implications: (i) the proposal cannot safely assert from the literature that sampling-based
dispersion beats or loses to log-probability or verbalized confidence — it must measure it under its own fixed
protocol; (ii) because the proposal varies the prompt by design (paraphrases), it is walking straight into the
"answer formulation changes confidence" effect, and must fix and report its scoring protocol explicitly or its
per-value uncertainty scores will be partly an artefact of paraphrase surface form rather than of error risk.

**Gap noted:** I found no paper in this search that directly and peer-reviewed establishes a single winner
among verbalized confidence, token log-probability, and sampling-based dispersion for **structured scientific
extraction**. The evidence above is from QA and reasoning benchmarks. The proposal's claim to be filling a gap
appears defensible on this point.

---

## Prompt sensitivity

**Xie, Q., Liang, Z., Wu, J., Chen, Y., Wang, W., Ma, W., Ming, Z., Yang, H., & Wu, K. (2026). "Beyond Prompt
Engineering: A Systematic Analysis of Prompt Lexical Sensitivity and Its Impacts on Quality." Findings of ACL
2026, pp. 41998–42012.** https://aclanthology.org/2026.findings-acl.2084/ · DOI 10.18653/v1/2026.findings-acl.2084
Peer-reviewed. Large-scale analysis of n-gram token-level mechanisms over a dataset of **132,000 prompt
variants**. Confirms that *"LLMs often exhibit extreme sensitivity to surface-level prompt variations, where
minor lexical perturbations trigger disproportionate performance fluctuations."* Proposes and supports a
"Scaling Law of Prompt Performance Stability": **higher average performance is inherently associated with lower
variance and greater stability.** Identifies two stabilising linguistic pillars — Domain-Specific Terminology
(anchors semantic boundaries) and Explicit Action Directives (formalises reasoning trajectories) — that "lock"
the generation process. Operationalises this into a Prompt-Refining Agent, reporting a 40.7% reduction in
performance variance for code generation.
*Relation to proposal:* **MIXED — a threat and a resource.** Threat: it is direct, large-scale, peer-reviewed
confirmation that prompt wording materially changes outputs, which is the premise the proposal relies on for
its paraphrases to carry signal. Resource: the "Scaling Law of Prompt Performance Stability" means **low
performance variance is associated with high average performance** — so dispersion and error are, at the
population level, *positively* related, which is directionally what the proposal needs. But this cuts against
naive use: a prompt family that is uniformly bad and uniformly confident-looking would show *low* variance and
*high* error. The proposal's per-value use within a document is a different granularity from this paper's
prompt-family-level analysis, and that gap should be acknowledged rather than elided.

**Zatuchin, D. (2026).** See full entry under "Self-consistency and its critiques." This is the one paper I
found that treats **prompt paraphrase as an explicit variance component** and estimates its size relative to
resampling and model identity. Its finding that the brand-by-prompt component is near zero while resampling
dominates is the most direct empirical challenge to the proposal's decision to vary *prompts* rather than
*decoding* or *models*. *Relation to proposal:* **THREAT.**

**Gap / caution:** I did **not** find a peer-reviewed paper that successfully uses paraphrase variance *as a
validated uncertainty signal for structured scientific extraction*. The closest positives are Feng et al.
(EMNLP 2025 Findings), which uses query-variation diversity as part of a multi-agent uncertainty estimator and
reports it beats self-consistency, and the "Hallucinations Live in Variance" preprint below — but the latter is
a very-low-citation preprint with no venue. See "Unverified / could not confirm" for the paraphrase-variance
paper I could not read.

**Chadwick, S. P., & Flouro, A. R. (2026). "Hallucinations Live in Variance."**
arXiv:2601.07058 (preprint, 11 Jan 2026) · https://arxiv.org/abs/2601.07058
**Preprint; I verified the arXiv record and abstract only — I flag it as low-confidence, single-version,
with no venue listed and an unusual author ordering.** Proposes semantic equivalence as the source of
hallucination: *"they arise when semantically equivalent prompts activate inconsistent internal pathways,
producing divergent outputs."* Defines Semantic Stability (SS) via Paraphrase Consistency PC@k — generate k
paraphrases, greedy decode each, compute mode agreement — and explicitly frames SS as "a diagnostic for
variance-driven unreliability, not a method for improving correctness." Reports that a dense Qwen3-0.6B model
"agrees with itself only 23.8% of the time; at 32% sparsity, agreement jumps to 55.9%." It also makes a
distinction that is directly useful to the proposal's framing: *"Consistent but incorrect outputs reflect bias
or missing knowledge; confident guessing reflects calibration failure. Neither constitutes hallucination under
this definition."*
*Relation to proposal:* **SUPPORTS the specific mechanism (paraphrase-variance-as-signal) more than any other
paper I found**, and its "consistent but incorrect ⇒ not a variance problem" carve-out is precisely the
proposal's known blind spot stated by an independent author. **Recommend citing it only as supporting
motivation from a preprint**, never as evidence of validity — no venue, no peer review, and the reported
agreement numbers come from a 0.6B model, which does not transfer to the frontier models the proposal will use.

---

## Scientific extraction systems and datasets

**Yi, G. H., Choi, J., Song, H., Miano, O., Choi, J., Bang, K., Lee, B., Sohn, S. S., Buttler, D.,
Hiszpanski, A., Han, S. S., & Kim, D. (2025). "MaTableGPT: GPT-Based Table Data Extractor from Materials
Science Literature." *Advanced Science* 12(16).** DOI 10.1002/advs.202408221 ·
https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202408221
(Publisher page returned HTTP 403 to my fetch; **full metadata, abstract and author list verified via the
OSTI record**: https://www.osti.gov/biblio/2506940)
Peer-reviewed. One of the brief's seed sources; **exists and verifies.** A GPT-based table data extractor for
materials science literature with two key strategies: table data representation and table splitting for better
GPT comprehension, and **filtering hallucinated information through follow-up questions.** Applied to a large
volume of water splitting catalysis literature, achieving extraction accuracy (total F1) up to **96.8%**.
Compares zero-shot, few-shot, and fine-tuning on a Pareto front across GPT usage cost, labelling cost, and
accuracy; few-shot is the most balanced (total F1 > 95%, GPT usage cost $5.97, labelling cost 10 I/O paired
examples).
*Relation to proposal:* **SUPPORT for feasibility, THREAT for the necessity of the proposal's method.** The
headline 96.8% F1 is the number the proposal must contend with: at that accuracy level there is little error
left for an uncertainty estimator to flag, and it suggests that careful prompt engineering plus follow-up
verification questions (rather than sampling dispersion) may be the more effective route. Note the overlap:
MaTableGPT's "filter hallucinated information through follow-up questions" is a verification strategy, and
Kim et al.'s conformal framework similarly uses LLM-as-a-judge verification. The proposal should position its
dispersion score as complementary to — or benchmarked against — follow-up-question verification at matched cost.
Also note MaTableGPT targets *table* data from *water splitting catalysis*, the same broad domain as the
proposal, and its accuracy figures come from a particular schema; the proposal should not assume they transfer.

**Polak, M. P., & Morgan, D. (2024). "Extracting accurate materials data from research papers with
conversational language models and prompt engineering." *Nature Communications* 15:1569.**
DOI 10.1038/s41467-024-45914-8 · https://doi.org/10.1038/s41467-024-45914-8
(preprint: arXiv:2303.05352, https://arxiv.org/abs/2303.05352)
Peer-reviewed. The ChatExtract method: engineered prompts applied to a conversational LLM that identify
sentences with data, extract the data, and **assure the data's correctness through a series of follow-up
questions**. Reports precision and recall both close to 90% from the best conversational LLMs (ChatGPT-4) on
materials data. States the exceptional performance is enabled by information retention in a conversational
model combined with **"purposeful redundancy and introducing uncertainty through follow-up prompts."** Builds
databases of critical cooling rates of metallic glasses and yield strengths of high-entropy alloys.
*Relation to proposal:* **SUPPORT (for the uncertainty framing) and a competing method.** This paper
independently converges on "introducing uncertainty through follow-up prompts" as a performance mechanism —
evidence that interrogating the model, rather than resampling a paraphrase, is an established and effective
route. Like MaTableGPT it reports ~90% precision/recall, again limiting headroom for an uncertainty estimator.

**Ghosh, S., Brodnik, N. R., Frey, C., Holgate, C., Pollock, T. M., Daly, S., & Carton, S. (2024).
"Toward Reliable Ad-hoc Scientific Information Extraction: A Case Study on Two Materials Datasets."
Findings of ACL 2024.** DOI 10.18653/v1/2024.findings-acl.897 · arXiv:2406.05348 ·
https://arxiv.org/abs/2406.05348
Peer-reviewed (Findings of ACL 2024). Assesses whether GPT-4, with a basic prompting approach, can replicate
two existing materials-science datasets given the manuscripts from which they were originally manually
extracted. Uses **materials scientists to perform detailed manual error analysis** to determine where the model
struggles to faithfully extract the desired information, and uses their insights to propose research directions.
*Relation to proposal:* **SUPPORT as the error-analysis template and the closest existing gold-standard setup.**
This is effectively an existing gold-standard dataset plus expert error taxonomy for LLM-based materials
extraction — directly relevant to requirement (6). Its method (manual expert error analysis) is the ground
truth the proposal needs in order to validate that dispersion tracks error, and the two material datasets it
uses are candidate calibration sets. Note it is a *case study on two datasets*, not a benchmark with
uncertainty annotations, so it does not by itself supply labelled uncertainty.

**Dagdelen, J., Dunn, A., Lee, S., Walker, N., Rosen, A. S., Ceder, G., Persson, K. A., & Jain, A. (2024).
"Structured information extraction from scientific text with large language models." *Nature Communications*
15:1418.** DOI 10.1038/s41467-024-45563-x · https://doi.org/10.1038/s41467-024-45563-x
(Author list and abstract verified via the Princeton research-output record:
https://collaborate.princeton.edu/en/publications/structured-information-extraction-from-scientific-text-with-large/)
Peer-reviewed. Presents a simple approach to **joint named entity recognition and relation extraction**,
fine-tuning pretrained LLMs (GPT-3, Llama-2) to extract records of complex scientific knowledge. Tests three
representative materials-chemistry tasks: linking dopants and host materials, cataloguing metal-organic
frameworks, and general composition/phase/morphology/application extraction. Extraction from single sentences
or entire paragraphs, output as plain-English sentences or structured JSON.
*Relation to proposal:* **SUPPORT (methodological neighbour).** This is the canonical structured-scientific-
extraction-with-LLMs paper and a natural baseline for the proposal's extraction component. Important for the
proposal's framing: it fine-tunes models rather than relying on a frozen model with paraphrase sampling, so it
sits on the other side of the accuracy/uncertainty trade-off. Notably it does **not** address uncertainty
quantification — which supports the proposal's gap claim.

**Khalighinejad, G., Circi, D., Brinson, L., & Dhingra, B. (2024). "Extracting Polymer Nanocomposite Samples
from Full-Length Documents." Findings of ACL 2024, pp. 13163–13175.**
https://aclanthology.org/2024.findings-acl.779/ · DOI 10.18653/v1/2024.findings-acl.779
Peer-reviewed. Investigates LLMs for extracting sample lists of polymer nanocomposites (PNCs) from full-length
materials-science research papers, where PNC samples have numerous attributes scattered throughout the text.
Introduces **a new benchmark and an evaluation technique** for this task and explores zero-shot prompting
strategies; **incorporates self-consistency to improve performance.** Reports that "even advanced LLMs struggle
to extract all of the samples from an article," and categorises errors into three main challenges.
*Relation to proposal:* **SUPPORT (strongest single support for the domain + method combination).** This is
peer-reviewed, in the exact domain family (materials/polymers), on full-length scientific documents, and it
already uses self-consistency — so it establishes precedent for the proposal's sampling approach in scientific
extraction. Its candid finding that advanced LLMs still miss whole samples also establishes that there *is*
error for an uncertainty estimator to be useful against, which partly offsets MaTableGPT's 96.8% F1 (different
task: sample-list completeness in long documents is much harder than table value extraction).

**Swain, M. C., & Cole, J. M. (2016). "ChemDataExtractor: A Toolkit for Automated Extraction of Chemical
Information from the Scientific Literature." *Journal of Chemical Information and Modeling* 56(10), 1894–1904.**
DOI 10.1021/acs.jcim.6b00207 · https://pubs.acs.org/doi/10.1021/acs.jcim.6b00207
**Metadata verified via the reference list of the OSTI MaTableGPT record; the ACS abstract page itself I could
not read (publisher blocked).** Peer-reviewed. The pre-LLM rule-based baseline toolkit for automated extraction
of chemical information from scientific literature. *Relation to proposal:* **background / baseline.** Should be
cited as the rule-based tradition that LLM extraction is contrasted against; note it is deterministic, so it has
no uncertainty estimate at all, which is one honest framing of the proposal's motivation. Also worth noting the
successor **Mavračić, J., Court, C. J., Isazawa, T., et al. (2021). "ChemDataExtractor 2.0: Autopopulated
Ontologies for Materials Science." *J. Chem. Inf. Model.* 61(9)** — DOI 10.1021/acs.jcim.1c00446 — metadata
likewise verified only via the OSTI reference list, not read directly.

**On PolyBERT — see "Unverified / could not confirm."** I could establish only that a record exists at
https://europepmc.org/article/MED/37433807 and that the paper is associated with DOI 10.1038/s41467-023-39868-6
and Nature Communications; I could not retrieve the title, abstract, or author list, so **I am not citing it.**
Note that PolyBERT is a polymer *property-prediction* chemical language model, not an extraction system, so it is
a tangent to the proposal's topic even once verified.

---

## Existing benchmarks / gold-standard datasets for uncertainty in LLM scientific extraction

**Direct answer to requirement (6): I could not find one.** No benchmark or gold-standard dataset specifically
annotated for *uncertainty in LLM-based scientific information extraction* surfaced in this search. What exists
is adjacent and should be assembled rather than assumed:

- **Ghosh et al. (2024), Findings of ACL 2024** (https://arxiv.org/abs/2406.05348) — two materials datasets
  with expert manual error analysis. Closest thing to a gold standard for LLM materials extraction; no
  uncertainty labels. **Best available starting point for building a calibration set.**
- **Khalighinejad et al. (2024), Findings of ACL 2024** (https://aclanthology.org/2024.findings-acl.779/) — a
  new benchmark plus evaluation technique for polymer nanocomposite sample extraction from full-length papers.
  Strong on *extraction* benchmarking, silent on uncertainty.
- **MaTableGPT's water-splitting catalysis database** (DOI 10.1002/advs.202408221) — a large extracted corpus
  with reported F1 up to 96.8%; usable as a scale reference, not an uncertainty benchmark.
- **Dagdelen et al. (2024), Nature Communications** (DOI 10.1038/s41467-024-45563-x) — three materials-chemistry
  extraction tasks with structured JSON output; natural baseline tasks, no uncertainty annotation.
- Adjacent non-materials example worth knowing about: a benchmark dataset for greenhouse-gas emission
  extraction, *Scientific Data* — https://www.nature.com/articles/s41597-025-05664-8 — surfaced in search but
  **I did not read it** (Nature blocked my fetch), so I make no claim about its contents or suitability.

**Implication for the proposal:** the absence of an uncertainty benchmark is a genuine, defensible gap that the
proposal can claim. It is also a burden — the proposal will have to construct its own gold-standard
per-value error labels from an expert-annotated dataset (Ghosh et al. is the obvious vehicle) in order to
demonstrate that dispersion tracks error. That construction step should be an explicit, costed aim, not an
assumption.

---

## Threats to the proposal

Ranked by how much they should change the design.

1. **Confident mode collapse / dispersion is blind to systematic error — Hamidieh et al., ICLR 2026**
   (https://iclr.cc/virtual/2026/poster/10007682). Peer-reviewed, top venue, names the exact failure:
   "this proxy collapses when models are overconfident and produce the same incorrect answer across samples,"
   and shows an epistemic-uncertainty term is needed where self-consistency is low. **This is the single
   strongest threat.** Recommended response: add a cross-*model* disagreement term, or at minimum construct a
   diagnostic experiment that deliberately targets confidently-wrong extractions and reports the dispersion
   distribution on them (expected: mass at zero). If dispersion is flat-zero on that subset, the core
   assumption is falsified in the way that matters.
2. **The variance is in the wrong place — Zatuchin (2026)** (https://arxiv.org/abs/2607.13304). Preprint, but
   the only paper I found that audited the *decomposition* the proposal depends on: paraphrase (prompt)
   variance is near zero, resampling dominates at 34.8%, and repeats past the fifth buy 0.0003 relative-error
   variance. Threatens both the choice of perturbation axis (paraphrase) and the N = 7–10 budget. Domain is
   brand answers, so the proposal can rebut by measuring the decomposition in its own domain — which is arguably
   a publishable contribution in itself.
3. **Validation-free scores vs. finite-sample guarantees — Kim et al. (2025), AAAI-SS**
   (https://ojs.aaai.org/index.php/AAAI-SS/article/view/36929) and **Kotte (2026)**
   (https://arxiv.org/abs/2605.18812). The state of the art in LLM extraction UQ now delivers *formal coverage
   guarantees* (split conformal; pipeline-aware joint coverage), whereas dispersion delivers a heuristic score
   with no guarantee. A reviewer will ask why the proposal does not use conformal prediction. Best response:
   keep dispersion as the ranking/scoring feature and **wrap it in split conformal prediction** on a held-out
   calibration set to convert it into a risk-controlled decision rule.
4. **Small-N sample-coverage bias — Kunitomo-Jacquin et al., EACL 2026**
   (https://aclanthology.org/2026.eacl-long.334/). Peer-reviewed critique *precisely* of dispersion-over-
   observed-samples: it ignores the probability mass on unobserved answers. At N = 7–10 this is materially worse
   than at the N = 10–20 typical of the semantic-entropy literature. Needs either a larger N, a smoothed/
   evidential estimator, or an explicit bias analysis.
5. **Token-entropy + conformal beats self-consistency — Xu & Lu (2025)** (https://arxiv.org/abs/2509.00461).
   Preprint, but a direct competitive claim, and it closes the "we have no logit access" escape route by being
   logit-free. Requires a baseline comparison.
6. **Protocol sensitivity undermines published calibration comparisons — Kim & Kang (2026)**
   (https://arxiv.org/abs/2605.27752). Preprint, but a rigorous twelve-study audit: the winner flips in 9/12
   settings under AUROC and the *sign* of the ECE comparison is undetermined in 6/12 settings across twelve
   operational variants. Consequence: the proposal cannot cite the literature to settle "which confidence
   signal is best calibrated" — it must measure under a fixed, explicitly reported protocol. This also means
   freedom-from-artefact is a real risk when the prompt is varied by design.
7. **RLHF-induced miscalibration — Xiao et al., ICML 2025** (https://arxiv.org/abs/2505.01997). Peer-reviewed
   mechanism explaining *why* confident mode collapse occurs: preference alignment causes overconfidence and
   poor calibration where pretrained models were well-calibrated. Implies the proposal's dispersion scores on
   aligned models are systematically deflated.
8. **Self-consistency under-measures uncertainty vs. query perturbations — Feng et al., EMNLP 2025 Findings**
   (https://arxiv.org/abs/2412.09572). Peer-reviewed demonstration that a confident wrong answer to the target
   query coexists with a confident right answer to a knowledge-preserving perturbation. Note this one is
   *partly* a defence, since the proposal's paraphrasing is a query-perturbation strategy.
9. **High baseline accuracy leaves little error to detect — MaTableGPT**
   (https://www.osti.gov/biblio/2506940) and **Polak & Morgan** (DOI 10.1038/s41467-024-45914-8) report ~96.8%
   F1 and ~90% precision/recall respectively on materials extraction, achieved by prompt engineering plus
   follow-up verification questions. Threatens the proposal's *necessity* argument, not its validity: if
   careful prompting already gets you to ~90–97%, the value of an uncertainty score is confined to the residual,
   and the proposal must show the residual is where dispersion actually discriminates.
10. **Semantic entropy is definitionally scoped to arbitrary errors — Farquhar et al., Nature 2024**
    (https://doi.org/10.1038/s41586-024-07421-0). The Nature paper explicitly targets *confabulations*
    ("arbitrary and incorrect generations"), i.e. exactly the variance-dominated subset. This is the cleanest
    peer-reviewed statement that sampling-based uncertainty does not cover systematic error, and it applies
    verbatim to the proposal's dispersion score.
11. **Professional-knowledge tasks defeat all confidence methods — Xiong et al., ICLR 2024**
    (https://arxiv.org/abs/2306.13063). Reports that *all* investigated methods struggle on tasks requiring
    professional knowledge, with no technique consistently best. Scientific extraction is such a task.

## What supports the proposal

1. **Ali (2026), the seed paper** (https://arxiv.org/abs/2607.20464) — contrary to the brief's premise, it
   concludes *"Self-consistency gives accurate per-question uncertainty,"* with split-half **r = 0.994**.
   Direct evidence that repeated sampling yields a stable per-question estimate. Cite it as support, and cite
   its cross-question limitation as a scoping caveat (not as a refutation).
2. **Wang et al. (2023), ICLR** (https://arxiv.org/abs/2203.11171) — the self-consistency paradigm is
   well-established and effective; legitimacy of the sampling-and-aggregate approach.
3. **Kuhn et al. (2023), ICLR Spotlight** (https://arxiv.org/abs/2302.09664) and **Farquhar et al. (2024),
   Nature** (https://doi.org/10.1038/s41586-024-07421-0) — the canonical, peer-reviewed, high-impact precedent
   that sampling-based uncertainty over *meanings* predicts accuracy. The proposal's 1 − majority-agreement
   term is a coarse semantic-entropy surrogate; this lineage is its strongest legitimacy claim.
4. **Kadavath et al. (2022)** (https://arxiv.org/abs/2207.05221) — larger models are well-calibrated in the
   right format, and self-evaluation improves when the model considers **many of its own samples**. Directly
   supports sampling as a source of genuine uncertainty signal. (Caveat: samples inform an elicited judgement,
   not a raw dispersion score — do not over-claim.)
5. **Xiong et al. (2024), ICLR** (https://arxiv.org/abs/2306.13063) — "sampling + aggregation" is a validated
   component of a confidence-elicitation framework, and black-box methods are only narrowly behind white-box
   (AUROC 0.522 vs 0.605). Justifies a logit-free design.
6. **Feng et al. (2025), EMNLP Findings** (https://arxiv.org/abs/2412.09572) — the constructive half: query
   perturbations carry real uncertainty information and outperform plain self-consistency. Validates the
   proposal's instinct to vary the prompt, even while it indicts fixed-prompt resampling.
7. **Khalighinejad et al. (2024), Findings of ACL 2024** (https://aclanthology.org/2024.findings-acl.779/) —
   peer-reviewed precedent for using self-consistency in full-document scientific (materials/polymer)
   extraction, and evidence that real extraction error remains in exactly this setting.
8. **Xie et al. (2026), Findings of ACL 2026** (https://aclanthology.org/2026.findings-acl.2084/) —
   the "Scaling Law of Prompt Performance Stability": **higher average performance is associated with lower
   variance.** At the population level, low dispersion and high accuracy co-occur, which is directionally the
   relation the proposal needs.
9. **Chadwick & Flouro (2026)** (https://arxiv.org/abs/2601.07058) — **preprint only.** Posits exactly the
   proposal's mechanism (semantically equivalent prompts → divergent outputs → variance as a hallucination
   diagnostic via paraphrase mode-agreement). Support at the level of motivation, not evidence.
10. **No competing uncertainty benchmark exists for scientific extraction.** Supports the proposal's novelty
    claim (and imposes the burden of constructing the gold standard).

## Current best practice for quantifying uncertainty in LLM extraction (as of the newest literature found)

Synthesising the verified sources above, the state of the art has moved in a clear direction:

1. **Do not report a raw heuristic dispersion score as "uncertainty."** The 2025–2026 norm is to convert any
   score into a **risk-controlled decision rule with a coverage guarantee**. The reference implementations for
   *extraction specifically* are Kim et al., AAAI-SS 2025 (https://ojs.aaai.org/index.php/AAAI-SS/article/view/36929),
   which calibrates extraction confidence and applies conformal prediction for finite-sample guarantees on
   accepted extractions across 10k visits; and Kotte 2026
   (https://arxiv.org/abs/2605.18812) for multi-stage pipelines, where independent per-stage conformal
   prediction collapses to 59% coverage under distribution shift (vs. PASC holding target coverage). Practical
   implication: **calibrate on a held-out labelled set, report coverage, and report it under shift.**
2. **Combine aleatoric and epistemic components; do not rely on within-prompt sampling alone.**
   Hamidieh et al., ICLR 2026 (https://iclr.cc/virtual/2026/poster/10007682) is the clearest statement:
   AU from self-consistency + EU from cross-model disagreement = TU, with EU flagging confident failures where
   AU is low. Where cost permits, small **scale-matched model ensembles** are the emerging recommendation over
   extra repeats of one model — consistent with Ali 2026's finding that only a diverse ensemble surfaces
   multi-dimensional error structure, and with Zatuchin 2026's budget result that repeats past five are nearly
   worthless while adding models/languages is efficient.
3. **Prefer logit/token-level signals where available, but black-box sampling is competitive.** Xiong et al.,
   ICLR 2024 (https://arxiv.org/abs/2306.13063) reports white-box ahead of black-box by only 0.522 → 0.605
   AUROC; TECP (https://arxiv.org/abs/2509.00461) shows token entropy plus conformal prediction can be
   logit-free and still beat self-consistency baselines. Practical implication: **report both**, and be explicit
   about the protocol, because Kim & Kang 2026 (https://arxiv.org/abs/2605.27752) shows the ranking is not
   robust to unstated protocol choices.
4. **Treat semantic/decompositional aggregation as the baseline, not the frontier.** Semantic entropy
   (Kuhn et al. 2023; Farquhar et al. 2024) is now the *baseline*. The active critiques are that it ignores
   unobserved-answer mass (EVSE, EACL 2026 — https://aclanthology.org/2026.eacl-long.334/) and that it is
   expensive relative to single-pass probes (SEP, https://arxiv.org/abs/2406.15927). Practical implication for
   the proposal: **benchmark against semantic entropy and against a single-pass probe**, not only against
   majority agreement.
5. **Verification prompts are a co-equal practice, not a fallback.** Both leading materials-extraction systems
   in this review get their accuracy from follow-up verification questions — MaTableGPT "filtering hallucinated
   information through follow-up questions" (https://www.osti.gov/biblio/2506940) and ChatExtract's
   "introducing uncertainty through follow-up prompts" (DOI 10.1038/s41467-024-45914-8) — and Kim et al.'s
   conformal framework uses LLM-as-a-judge verification. Practical implication: the proposal's uncertainty
   budget should be compared at matched cost against simply asking the model to verify its own extraction.
6. **Report the variance decomposition of your own design.** The single most useful methodological move
   available to the proposal, given Zatuchin 2026 (https://arxiv.org/abs/2607.13304), is to report how much of
   its per-value dispersion is attributable to prompt paraphrase vs. decoding stochasticity vs. model identity
   in its own scientific-extraction setting. That both defends the design choice and, if the components differ
   from the brand-answer domain, is itself a contribution.
7. **Fix and publish the scoring protocol.** Per Kim & Kang 2026, state which answer is scored, under which
   prompt, and which readout is used. Because the proposal varies prompts by design, this is not optional
   hygiene — it is required to show the dispersion score is not an artefact of paraphrase surface form.

---

## Unverified / could not confirm

Listed so nothing here is mistaken for a verified citation. **None of these should appear in the proposal's
bibliography until independently retrieved.**

1. **"Uncertainty Aware Multi-Agent RAG Using Paraphrase-Induced Epistemic Variance Analysis."** IEEE record at
   https://ieeexplore.ieee.org/document/11663703 returned **HTTP 202 with no content** to my fetch, and I could
   not obtain authors, year, venue, or abstract from any other source. **Potentially the single most topically
   relevant hit in the entire search** — the title proposes paraphrasing to induce epistemic variance, which is
   almost exactly the proposal's method — so **this is the highest-priority item for the parent to resolve
   manually** (institutional IEEE access, or an author preprint). I am deliberately not citing it.

2. **"Scientific Table Data Extraction with Uncertainty Quantification."** ACM DL record at
   https://dl.acm.org/doi/10.1145/3677389.3702616 returned **HTTP 403**; the proceedings TOC confirms it belongs
   to the **24th ACM/IEEE Joint Conference on Digital Libraries (JCDL 2024)**, and the DOI resolves. I could not
   read the abstract or author list. **Relevant** (uncertainty quantification + scientific table extraction) and
   should be resolved manually. Not cited.

3. **"Uncertainty-Aware Complex Scientific Table Data Extraction."** *Document Analysis and Recognition –
   ICDAR 2025*, DOI 10.1007/978-3-032-04624-6_4 (https://acm-stag.literatumonline.com/doi/abs/10.1007/978-3-032-04624-6_4).
   Title, venue and DOI verified from search indexing; **abstract, authors, and year-in-proceedings not read.**
   Relevant to requirements (2) and (5). Not cited as a finding.

4. **PolyBERT.** I could NOT verify the title, abstract, or author list. What I can state: a record exists at
   https://europepmc.org/article/MED/37433807 (PMID 37433807), the paper is associated with DOI
   **10.1038/s41467-023-39868-6** in Nature Communications, and search indexing links it to polymer informatics
   ("polyBERT: a chemical language model to enable fully machine-driven ultrafast polymer informatics"). The
   frequently-cited author **Kuenneth** appeared in a Europe PMC author search, but I did **not** confirm the
   full author list, and I did not retrieve the abstract. **Not cited.** Note also that PolyBERT is a polymer
   *property-prediction* model, not an extraction system, so it is peripheral to the proposal's topic.

5. **"Assessing the Reliability of Large Language Models for Scientific Information Extraction"** (ASEE
   conference paper, https://nemo.asee.org/public/conferences/374/papers/52646/download). Returned
   "unsupported content type application/pdf". Title suggests relevance to requirements (5) and (6);
   **authors, year, venue and abstract unverified.** Not cited.

6. **Greenhouse-gas emission extraction benchmark dataset**, *Scientific Data*,
   https://www.nature.com/articles/s41597-025-05664-8. Nature redirected to an identity provider and I could not
   read it. Title from search indexing ("Addressing data gaps in sustainability reporting: A benchmark dataset
   for greenhouse gas emission extraction"). **Not verified, not cited.** Potentially relevant as a
   document-level extraction benchmark with gold labels.

7. **"Real-Time Trustworthiness Scoring for LLM Structured Outputs and Data Extraction."** Semantic Scholar
   record at https://www.semanticscholar.org/paper/550e42489ce4f6dea05c0aa4360ebe276ed8bce7 returned HTTP 202
   with no content. Authors appeared in the URL slug as **Goh, Mueller** et al.; venue, year, and content
   **unverified**. Topically relevant to per-value reliability scoring. Not cited.

8. **ChemDataExtractor (2016) and ChemDataExtractor 2.0 (2021).** Authors, journal, volume, issue, pages and
   DOIs were verified **only** from the reference list embedded in the OSTI record for MaTableGPT
   (https://www.osti.gov/biblio/2506940), not from the publisher's own pages (ACS blocked my fetch). The
   bibliographic details are almost certainly correct, but flagging the second-hand provenance per the brief's
   instruction. **Swain & Cole 2016** (DOI 10.1021/acs.jcim.6b00207) and **Mavračić et al. 2021**
   (DOI 10.1021/acs.jcim.1c00446) should be re-verified at source before submission.

9. **Conformal prediction foundations** (Vovk et al.; Angelopoulos & Bates; Lei et al.) were **not** retrieved in
   this search. The proposal needs them; they must be added from direct retrieval, not from this report.

10. **Software/artifact note:** the **Spanda** code is at https://github.com/Adarshent/Spnda. The GitHub
    organisation is not an established research group as far as I could determine, and the associated Zenodo
    preprint is single-author and non-peer-reviewed. Treat that paper's headline result with suspicion pending
    replication. The **semantic-entropy-probes** code is at https://github.com/OATML/semantic-entropy-probes
    (OATML, University of Oxford) — this is the legitimate artifact for Kossen et al. 2024.

**One further caveat on my own method.** I verified every citation above by fetching its record and reading the
abstract. For four items (ChemDataExtractor and successor, PolyBERT, and the two blocked table-extraction
papers) I could not reach an authoritative page. Two seed URLs supplied in the brief (the export.arxiv.org PDF
and the AAAI PDF download link) could not be fetched directly because this tool rejects PDF content types, so
I verified them via their landing pages instead — both were confirmed, with full author lists and abstracts.
