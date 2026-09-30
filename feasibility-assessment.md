# Feasibility Assessment: Automated Dataset Extraction for BDD Electrodes and PVDF/HAp Membranes

**Method note.** All publication counts below come from **OpenAlex** `title_and_abstract.search` queries executed live (URLs given inline). OpenAlex was the only large bibliographic API reachable; Crossref's bibliographic search returned 315,164 results for "boron-doped diamond electrode" (far too fuzzy to use), Semantic Scholar returned HTTP 429, and Scopus/Web of Science were not accessible. Counts are therefore **estimates of indexed English-language literature**, not publisher-authoritative totals. OpenAlex indexes publication years up to and including 2026, which in this environment is the current year.

---

## BDD literature volume and venues

**Verdict: the topic volume is large, but the substrate criterion cuts it hard. BDD most likely supports 100+ records, but with much less margin than the headline count implies.**

| Query | Count | Link |
|---|---|---|
| `"boron-doped diamond"`, type=article, 2015-01-01 → 2026-12-31 | **3,545** | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22boron-doped%20diamond%22,type:article,from_publication_date:2015-01-01,to_publication_date:2026-12-31) |
| same, all work types | 4,677 | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22boron-doped%20diamond%22,from_publication_date:2015-01-01,to_publication_date:2026-12-31) |
| `"boron-doped diamond"` AND `"electrode"`, type=article, 2015+ | **2,372** | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22boron-doped%20diamond%22%20AND%20%22electrode%22,type:article,from_publication_date:2015-01-01) |

**Annual output is stable at roughly 180–235 electrode-relevant articles/year** (2015: 185, 2018: 223, 2020: 233, 2024: 220, 2025: 213), so a 2015–2026 window is not thin at either end — [year-by-year breakdown](https://api.openalex.org/works?filter=title_and_abstract.search:%22boron-doped%20diamond%22%20AND%20%22electrode%22,type:article,from_publication_date:2015-01-01&group_by=publication_year).

### Main venues (2015–2026, `"boron-doped diamond"` articles)

| Rank | Journal | Articles |
|---|---|---|
| 1 | **Diamond and Related Materials** | 200 |
| 2 | **Electrochimica Acta** | 148 |
| 3 | Journal of Electroanalytical Chemistry | 122 |
| 4 | Chemosphere | 112 |
| 5 | Separation and Purification Technology | 86 |
| 6 | Electroanalysis | 76 |
| 7 | Chemical Engineering Journal | 64 |
| 8 | Journal of Environmental Chemical Engineering | 61 |
| 9 | ChemElectroChem | 59 |
| 10 | **Carbon** | 47 |
| 11 | Journal of The Electrochemical Society | 46 |
| 12 | Journal of Hazardous Materials | 42 |
| 13 | Water Research | 40 |
| 14 | Journal of Water Process Engineering | 40 |
| 15 | Environmental Science & Technology | 20 |
| — | **ACS Applied Materials & Interfaces** | 21 |

Source: [OpenAlex venue grouping](https://api.openalex.org/works?filter=title_and_abstract.search:%22boron-doped%20diamond%22,type:article,from_publication_date:2015-01-01&group_by=primary_location.source.id&per-page=50).

The proposal's guessed venue list is **partly right and partly wrong**: Diamond and Related Materials, Electrochimica Acta, and Carbon are confirmed as core venues; ACS Applied Materials & Interfaces is present but minor (21 articles) compared with the environmental-engineering cluster (Chemosphere, Separation and Purification Technology, Chemical Engineering Journal, Water Research). The applied-electrochemistry-for-water-treatment literature dominates BDD, not the materials-characterization literature.

### The substrate criterion is the real bottleneck (measured)

I obtained this count on a late retry, and it materially changes the Domain-1 picture:

| Query | Count | Link |
|---|---|---|
| `"boron-doped diamond"` AND `"titanium"`, type=article, 2015+ | **128** | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22boron-doped%20diamond%22%20AND%20%22titanium%22,type=article,from_publication_date:2015-01-01) |

This is an **upper bound**, not a qualifying count, for two reasons. First, it matches the word "titanium" anywhere in title/abstract, so it includes papers that merely *compare* BDD against a titanium-based anode — the top-ranked hit is exactly that case (Wang et al., *Water Research* 170, 115254, comparing BDD against Magnéli-phase **Ti₄O₇**; [DOI](https://doi.org/10.1016/j.watres.2019.115254)). Those papers are not BDD-on-Ti studies. Second, it captures only papers that mention titanium; the proposal also admits Nb, Ta, and Si substrates, so the true substrate-tagged pool is larger than 128 but unmeasured (I could not run the Nb/Ta/Si variants before hitting rate limits).

**Implication for the inclusion criteria.** The substrate + Raman + performance conjunction is genuinely restrictive. The reported *topic* pool is ~2,372 articles, but the **substrate-specific** pool is on the order of 128–300, and after requiring Raman-derived doping data *and* a quantitative performance/failure outcome, a realistic yield is perhaps **60–120 records** — i.e. the 100 target is plausibly reachable but **not** the comfortable 20× margin the headline volume suggests. The proposal should measure the Nb/Ta/Si variants and the Raman-conjunction rate before assuming Domain 1 is safe. This is the single most important measurement to make next.

---

## PVDF/HAp literature volume and venues

**Verdict: this is the proposal's weak point. The domain is roughly 20–30× smaller than BDD and cannot be stretched to 100+.**

| Query | Count | Link |
|---|---|---|
| `("PVDF" OR "polyvinylidene fluoride")` AND `"hydroxyapatite"`, all types | **122** | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%28%22PVDF%22%20OR%20%22polyvinylidene%20fluoride%22%29%20AND%20%22hydroxyapatite%22) |
| `"PVDF"` AND `"hydroxyapatite"`, type=article only | 90 | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22PVDF%22%20AND%20%22hydroxyapatite%22,type:article) |
| `"polyvinylidene fluoride"` AND `"hydroxyapatite"`, type=article | 64 | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22polyvinylidene%20fluoride%22%20AND%20%22hydroxyapatite%22,type=article) |
| *Comparison:* `"PVDF"` AND `"membrane"`, type=article, 2015+ | **9,372** | [OpenAlex](https://api.openalex.org/works?filter=title_and_abstract.search:%22PVDF%22%20AND%20%22membrane%22,type=article,from_publication_date:2015-01-01) |

Annual output is growing (**2019: 5 → 2020: 2 → 2021: 3 → 2022: 10 → 2023: 17 → 2024: 21 → 2025: 19 → 2026: 22**) — [year breakdown](https://api.openalex.org/works?filter=title_and_abstract.search:%28%22PVDF%22%20OR%20%22polyvinylidene%20fluoride%22%29%20AND%20%22hydroxyapatite%22&group_by=publication_year) — but the *absolute* recent rate is only ~20 papers/year. A 122-paper pool cannot yield 100 records meeting a two-modality **and** one-performance-outcome conjunction. Realistic yield is on the order of **30–60 records**, i.e. close to the proposal's original 15–25 target and nowhere near 100.

### Venue structure (the telling result)

The `PVDF/HAp` intersection is **not concentrated in the venues the proposal names**. The single most common venue has 5 papers:

| Rank | Journal | Articles |
|---|---|---|
| 1 | Journal of Thermoplastic Composite Materials | 5 |
| 2 | SSRN Electronic Journal (preprints) | 4 |
| 3 | Ceramics International | 3 |
| 3 | Nano Energy | 3 |
| 5 | *~18 journals at 2 papers each* (incl. ACS Applied Materials & Interfaces, Molecules, J. Appl. Polym. Sci., Colloids & Surfaces B) | 2 |
| 6 | *~many journals at 1 paper each* | 1 |

Source: [OpenAlex venue grouping](https://api.openalex.org/works?filter=title_and_abstract.search:%28%22PVDF%22%20OR%20%22polyvinylidene%20fluoride%22%29%20AND%20%22hydroxyapatite%22&group_by=primary_location.source.id&per-page=40).

**Journal of Membrane Science, Desalination, and Separation and Purification Technology do not appear at all in the top 40 venues for the PVDF/HAp intersection.** The 122 papers are scattered across polymer-composites, ceramics, biomedical-materials, and piezoelectric-energy journals. The "PVDF/HAp membrane" literature as scoped by the proposal is a genuinely peripheral, low-volume, venue-fragmented research niche — it has no journal home. This has a direct operational consequence: there is no single venue to crawl, no publisher API to query efficiently, and every paper must be found via broad search, which raises cost per record.

---

## Existing databases and benchmarks

**Headline finding: neither domain has an existing extracted dataset. Both must be built from scratch — but there are strong methodological precedents and one highly relevant adjacent resource.**

### General materials databases (verified, but not covering either domain)

| Resource | Size | Relevance to proposal |
|---|---|---|
| **NOMAD** | **19,425,275 uploaded entries**, 4,346,100 represented materials, all CC-BY-4.0, full API | Computational (DFT); contains no Raman/sp3-sp2 electrode data. Useful as a *format/FAIR template*, not as data. [nomad-lab.eu](https://nomad-lab.eu/nomad-lab/index.html) |
| **Materials Project** | ~**150,000+** inorganic compounds; GGA+U/r2SCAN; mp-api | Computational; no BDD electrode or membrane data. [alloybase comparison](https://alloybase.app/blog/posts/materials-project-vs-aflow-vs-oqmd-vs-jarvis-dft) (secondary source — see caveats) |
| **AFLOW** | ~3.93M entries | Same limitation |
| **OQMD** | ~1.4M entries | Same limitation |
| **JARVIS-DFT (NIST)** | ~40,000 bulk + ~1,100 2D | Same limitation |
| **PoLyInfo (NIMS)** | **over half a million data points**, built by **20+ years of continuous manual extraction** and polymer structure lexicography | Polymer properties relevant to PVDF; **manual curation is the precedent** — a direct argument that automated extraction in a niche polymer-composite domain is much harder than the general databases' scale suggests. [NIMS SAMURAI](https://samurai.nims.go.jp/articles/9196dc2d-2b29-497d-9807-30efe9b4b683?locale=en) · [polymer.nims.go.jp](https://polymer.nims.go.jp/) |

### Membrane databases — the closest existing resource

**Open Membrane Database (OMD)** — [openmembranedatabase.org](https://www.openmembranedatabase.org/) — verified in detail from the primary paper:

- **>600 membranes** (as of the 2021/2022 paper), continuously growing.
- Sourced **63% peer-reviewed reports, 29% patents, 8% commercial datasheets**; spans reports from **1975 to present**.
- Records water permeability (A) and salt permeability (B), membrane structure (asymmetric / TFC / TFN / inorganic), selective-layer chemistry, synthesis modifications, contact angle, roughness, filtration mode, and 17 filterable fields; all data exportable.
- Includes a **standardised transport-theory layer** (concentration-polarisation corrections, osmotic-pressure models) and explicit reporting best practices.
- Source: Ritt et al., *Journal of Membrane Science* **641** (2022) 119927, [DOI](https://doi.org/10.1016/j.memsci.2021.119927) · [author PDF mirror](https://wetlab.net.technion.ac.il/files/2021/10/Ritt-etal-OMD_JMS_2022.pdf)

**Critical caveat:** OMD's initial release covers **only reverse-osmosis (RO) membranes** (defined as R_NaCl ≥ 80%), and by chemistry it is dominated by **thin-film polyamide**, not PVDF/HAp. It is therefore **not a substitute dataset** for Domain 2. It is, however, directly usable as (a) a **validation/comparison benchmark for extraction methodology** — it is crowd-sourced from the same literature class and has a documented curation protocol — and (b) a template for the schema the proposal should adopt. The paper itself notes extension to NF/FO/ED/SRNF as planned, implying PVDF-type UF/MF membranes are **out of scope**.

### Literature-extraction datasets and benchmarks (methodological precedents)

The Cole group (Imperial College) has released a whole family of auto-generated, machine-readable materials datasets — the strongest available methodological precedent:

| Dataset | Records | Source |
|---|---|---|
| Curie/Néel temperatures (2025, ChemDataExtractor v2.2.2 + Snowball v2) | **56,037 records** from **108,181 papers**; precision **72%**, recall **61%** | [Sci Data 2025](https://link.springer.com/article/10.1038/s41597-025-06244-6) · [figshare data](https://doi.org/10.6084/m9.figshare.29559686.v2) |
| Curie/Néel temperatures (2018, Snowball v1 + rule parsers) | **39,822 records** / **68,078 papers**; precision 73%, recall 56% | [Sci Data 5, 180111](https://doi.org/10.1038/sdata.2018.111) |
| Snowball 2.0 generic parser | pre-trained on >1,000 sentences | [J Chem Inf Model 63, 7045](https://doi.org/10.1021/acs.jcim.3c01281) |
| Photocatalysis / water-splitting | — | [Sci Data 10, 651](https://doi.org/10.1038/s41597-023-02511-6) |
| Refractive indices & dielectric constants | — | [Sci Data 9, 192](https://doi.org/10.1038/s41597-022-01295-5) |
| Thermoelectrics | — | [Sci Data 9, 648](https://doi.org/10.1038/s41597-022-01752-1) |
| Battery materials | — | [Sci Data 7, 260](https://doi.org/10.1038/s41597-020-00602-2) |
| Semiconductor band gaps | — | [Sci Data 9, 193](https://doi.org/10.1038/s41597-022-01294-6) |
| Stress–strain properties | — | [Sci Data 11, 1273](https://doi.org/10.1038/s41597-024-03979-6) |

**The 72%/61% precision/recall figure is the single most important number for this proposal's planning.** It means an automated extraction pipeline in a comparable materials domain produces roughly **1.6 false positives per true positive at the record level** and misses ~39% of true records. Any target of "100 records" must be read as "100 *verified* records", implying a candidate pool of ~160–250 extracted records plus manual adjudication.

**MatSci-NLP** (Miret, Liu et al., ACL 2023) — 7 NLP tasks: NER 112,191 samples; Relation Classification 25,674; Event Argument Extraction 6,566; Paragraph Classification 1,500; Synthesis Action Retrieval 5,547; Sentence Classification 9,466; Slot Filling 8,253. Code/data: [github.com/BangLab-UdeM-Mila/NLP4MatSci-ACL23](https://github.com/BangLab-UdeM-Mila/NLP4MatSci-ACL23) · [paper](https://aclanthology.org/2023.acl-long.201/). **It contains no BDD and no membrane data** — it spans fuel cells, glasses, inorganic materials, superconductors, and synthesis procedures.

**MaTableGPT** — "GPT-based Table Data Extractor from Materials Science Literature", *Advanced Science*, [DOI 10.1002/advs.202408221](https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202408221). I could **not retrieve the released dataset or its record count**: Wiley served a bot-verification page, and no GitHub/HuggingFace/Zenodo deposit surfaced in searches. Its **dataset release status is unverified** (see final section).

### Bottom line for Q3

- **No existing open dataset covers BDD electrodes.** No BDD electrochemistry database, no Raman-derived doping dataset, no sp3/sp2 extraction corpus exists.
- **No existing dataset covers PVDF/HAp membranes.** OMD is the nearest resource but is polyamide-RO-only.
- **Available to the proposal:** (i) methodological templates and transferable tooling (ChemDataExtractor/Snowball, MatSci-NLP task schemas), (ii) a documented curation-and-validation benchmark in an adjacent domain (OMD), (iii) a scale precedent showing automated extraction covers many domains in the 10³–10⁴ record range — which makes a 100-record target look modest *provided the source pool exists*, and it does for BDD but not for PVDF/HAp.

---

## Assessment of the claimed structural contrast

**The claim is directionally real but overstated and under-specified — and the proposal has it backwards in one important respect.**

**What is defensible.** The two domains genuinely differ in *field maturity and data density*:

- BDD is a **mature, instrument-homogeneous measurement community**. The dominant output is electrochemical oxidation performance in water treatment, reported as degradation efficiency, current efficiency, energy consumption, and increasingly Faradaic efficiency and service life. Measurement conventions (current density, electrolyte, anode area) are standardised enough that numeric values are mutually comparable — the same property the OMD authors identify as the precondition for a useful database ("RO membranes have generally well-defined separation performance that can be readily characterized... These membranes are therefore ideal a pilot database"). BDD sits in that favourable regime.
- PVDF/HAp is a **small, method-heterogeneous composite-fabrication community** spanning piezoelectric sensors, biomedical scaffolds, and filtration. A single paper routinely reports FTIR + XRD + SEM + contact angle + pure-water flux + rejection. The proposal's "multi-technique characterization within single papers" description is accurate.

**Where the claim breaks down.**

1. **The contrast is confounded with domain size.** The observed difference is at least as much "BDD is 20–30× bigger and institutionally mature" as "BDD values are homogeneous and PVDF/HAp values are multi-technique". Because PVDF/HAp has only 122 papers total, its heterogeneity is *partly an artefact of a small, unfocused literature* rather than an intrinsic property of membrane science. A fair cross-domain comparison needs two domains of **comparable size**, otherwise the experiment confounds extraction difficulty with corpus scale.

2. **BDD is not purely homogeneous single-value extraction.** BDD papers also report Raman spectra, sp3/sp2 ratios, boron concentration, film thickness, substrate adhesion, and accelerated-life-test curves — the proposal's own inclusion criteria *require* the Raman-derived modality, which is exactly the multi-technique feature attributed to Domain 2. The Raman sp3/sp2 ratio is frequently reported only in figures or derived via deconvolution with unstated assumptions, so it is arguably *harder* to extract reliably than an FTIR peak list. The claimed "homogeneous numeric values" characterises the *performance* half of BDD, not the *characterization* half.

3. **The genuinely different challenge is figure-bound versus table-bound data, and the proposal does not name it.** The sharpest extraction contrast in these fields is:
   - BDD performance data → mostly **in tables and text** (current density, efficiency, life in hours).
   - BDD characterization data → often **in figures** (Raman deconvolution).
   - PVDF/HAp → a mix, with flux/rejection frequently in tables but morphology and often XRD in figures.
   
   Figure-bound extraction is a materially harder and less benchmarked problem than text/table extraction. If the proposal wants a real structural contrast, **figure-derived numeric extraction is the axis it should be testing**, and that axis is not what the current framing describes.

4. **"Failure outcome" data is the rarest and least reported category in both domains.** Service life, delamination, and accelerated-failure endpoints are typically reported in *separate, dedicated* electrode-durability papers — not co-reported with Raman doping in the same study. This inclusion criterion will be the dominant source of attrition in Domain 1, more than any volume limit. The proposal should pilot-test this specific conjunction before committing to it.

---

## Alternative second domains

If the aim is a **genuinely different extraction challenge** at **comparable scale**, the following are quantitatively supported alternatives (counts from OpenAlex, `type=article`, 2015+):

| Candidate domain | Verified count | Why it is a better contrast to BDD |
|---|---|---|
| **Solid-state electrolytes** (`"solid-state electrolyte"` AND `"ionic conductivity"`) | **3,474** ([link](https://api.openalex.org/works?filter=title_and_abstract.search:%22solid-state%20electrolyte%22%20AND%20%22ionic%20conductivity%22,type=article,from_publication_date:2015-01-01)) | Ionic conductivity is **routinely extracted from Nyquist/EIS plots in figures**, not tables. This is a *genuine, well-defined* figure-mining challenge, and it is same-size as BDD, so the cross-domain comparison is not confounded by corpus scale. Activation energy and stability-window values add multi-value structure. |
| **Halide perovskite solar cells** (`"perovskite solar cell"` AND `"power conversion efficiency"`) | large (not re-queried; see caveats) | Strongest **external validation** option: the **Perovskite Database** already contains **>40,000 devices** curated under FAIR principles ([Chemistry World report](https://www.chemistryworld.com/news/painstakingly-curated-perovskite-database-of-over-40000-devices-set-to-speed-up-solar-research/4014935.article/) · [perovskitedatabase.com](https://perovskitedatabase.com/) · Hansen & Whittaker-Brooks, *Matter* 5, 2461 (2022), [DOI](https://doi.org/10.1016/j.matt.2022.06.001)). The proposal could **extract a defined subset and score it against an existing ground truth**, which is a far stronger methodological claim than extracting two datasets from scratch. |
| **CO₂ electroreduction** (`"CO2 electroreduction"` AND `"Faradaic efficiency"`) | **1,150** ([link](https://api.openalex.org/works?filter=title_and_abstract.search:%22CO2%20electroreduction%22%20AND%20%22Faradaic%20efficiency%22,type=article,from_publication_date:2015-01-01)) | **Attractive because it shares the Faradaic-efficiency vocabulary with BDD** — so if you want controlled contrast you get it; but that same overlap makes it a *weak* contrast if the goal is genuinely different extraction. Also note this is the same measurement family as Domain 1, risking a near-duplicate task. |

**Recommendation.** Do not replace Domain 2 with something *smaller and more similar*. The two defensible moves are:

- **(Recommended) Keep BDD as Domain 1; make halide perovskite solar cells Domain 2**, and frame the contribution as *extraction against an existing gold-standard database* (Perovskite Database, >40,000 devices) rather than a second from-scratch dataset. This converts the proposal's biggest liability (no ground truth) into its main methodological strength.
- **(Alternative) Replace PVDF/HAp with solid-state electrolytes** if the goal is a clean same-scale, genuinely-different extraction challenge (figure-bound EIS data vs. table-bound electrochemical performance).

If the team is attached to PVDF/HAp for application reasons, then **Domain 2 must be explicitly rescoped** — e.g. "PVDF blended with any ceramic filler" or "PVDF ultrafiltration membranes" (the latter is inside the 9,372-paper `PVDF + membrane` pool) — and the two-modality-plus-performance conjunction relaxed. As currently written it cannot reach 100.

---

## Systematic reviews usable as validation

**Finding: there are review articles but essentially no PRISMA-style quantitative meta-analyses in either domain.** No review was found that publishes an extracted numeric table usable directly as a validation set.

### BDD electrodes — reviews identified

| Review | Venue | Notes |
|---|---|---|
| Recent advances in **titanium-based** boron-doped diamond electrodes for enhanced electrochemical oxidation in industrial wastewater treatment | *Separation and Purification Technology* (2024) | Directly relevant to the proposal's Ti-substrate criterion. [ScienceDirect S1383586624039571](https://www.sciencedirect.com/science/article/abs/pii/S1383586624039571) |
| Recent developments and advances in boron-doped diamond electrodes for electrochemical oxidation of organic pollutants | *Separation and Purification Technology* **212**, 802–821 (2018) | **372 citations**; the standard entry review. [DOI](https://doi.org/10.1016/j.seppur.2018.11.056) |
| Recent advances in **modified** boron-doped diamond electrodes: A review | indexed via CAS/Czech Academy | [record](https://asep.lib.cas.cz/arl-cav/en/detail-cav_un_epca-0571322-Recent-advances-in-modified-borondoped-diamond-electrodes-A-review/) |
| Industrial wastewater treatment technology based on boron-doped diamond electrodes: A review | *Huagong Jinzhan* (Chemical Industry and Engineering Progress) 43(1), 501 (2024) | [link](https://hgjz.cip.com.cn/EN/Y2024/V43/I1/501) |

These are **narrative reviews**. They synthesise *degradation performance* qualitatively; they do not publish machine-readable extracted numeric tables, and — importantly — they do **not** focus on the proposal's distinctive outcomes (service life, delamination, sp3/sp2 vs. failure correlation). They are best used as (a) a **recall check** on the automated search strategy — any paper cited by these reviews that the pipeline missed is a false negative — and (b) a source of **domain vocabulary** for query design.

### PVDF/HAp membranes — reviews identified

- No dedicated systematic review or meta-analysis of PVDF/HAp membranes was found.
- The nearest curated resource is the **Open Membrane Database** and its *Journal of Membrane Science* paper ([DOI](https://doi.org/10.1016/j.memsci.2021.119927)), which covers RO/polyamide membranes and is a **methodological** rather than domain-matched validation set.
- A bibliometric-style overview exists for the broader field: "Bibliometric overview of global electrocatalytic water treatment research", *Discover Water* ([link](https://link.springer.com/article/10.1007/s43832-026-00441-z)) — covers the BDD-adjacent water-treatment field, not PVDF/HAp.

**Practical consequence.** Neither domain offers an off-the-shelf validation set. Validation will require the team to **hand-annotate a held-out sample** (the ChemDataExtractor papers used 230 randomly selected papers for recall evaluation and ~200 for precision — a useful, achievable precedent) and to report precision/recall explicitly, as the Cole-group datasets do.

---

## Unverified / could not confirm

Items I attempted but could **not** verify. Do not treat these as findings.

1. **MaTableGPT's released dataset and record count** — unconfirmed. The paper exists ([Advanced Science, DOI 10.1002/advs.202408221](https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202408221)), but Wiley served a bot-verification challenge and no GitHub/HuggingFace/Zenodo deposit was found. **Whether MaTableGPT's extracted dataset was ever publicly released is unresolved.**
2. **Exact current Materials Project compound count.** The "150,000+ inorganic compounds" figure comes from a **secondary blog source** ([alloybase.app](https://alloybase.app/blog/posts/materials-project-vs-aflow-vs-oqmd-vs-jarvis-dft)), because materialsproject.org returned a bot-verification page. Treat as approximate; the blog itself advises checking the site for the current count.
3. **Scopus and Web of Science publication counts.** Not accessible (paywalled/institutional). All volume figures here are OpenAlex-derived and may differ from Scopus by a material margin. A reviewer asking "how many papers are in Scopus?" cannot be answered from this work.
4. **Nb/Ta/Si-substrate BDD counts** — not obtained (rate-limited). I did obtain the **Ti** figure (**128** articles, 2015+, an upper bound — see the BDD section), but the analogous counts for niobium, tantalum, and silicon substrates are unmeasured. Since the proposal admits all four substrates, the total substrate-restricted pool is a key unknown and is very likely the difference between "100 records comfortably" and "100 records with difficulty". **This is the highest-priority measurement to make before committing.**
5. **Perovskite Database exact device count** — "over 40,000 devices" is from [Chemistry World](https://www.chemistryworld.com/news/painstakingly-curated-perovskite-database-of-over-40000-devices-set-to-speed-up-solar-research/4014935.article/), a secondary source. The primary *Nature Energy* paper was not retrievable (I hit an unrelated article at the guessed DOI). The figure is credible but should be re-verified at [perovskitedatabase.com](https://perovskitedatabase.com/).
6. **Perovskite solar cell + PCE OpenAlex count** — not obtained (rate-limited); the domain's scale is asserted qualitatively, not measured here.
7. **Whether any BDD or PVDF/HAp extraction dataset exists in a non-indexed location** (institutional repository, thesis appendix, or unpublished preprint). Absence of evidence in searches is not proof of absence.
8. **Covidence-style screening feasibility and inter-annotator agreement** — not assessed; this is a protocol design question, not a literature question.

---

## Bottom-line feasibility verdict

**Domain 1 (BDD electrodes): 100+ records is probably feasible, but with less margin than it appears — and the risk is concentrated in the substrate criterion.** The 2015–2026 topic pool is ~2,372 electrode-relevant articles at a stable ~200/year across ~50 indexed venues with three clear core journals. However, restricting to a named Ti/Nb/Ta/Si substrate collapses this sharply: the `"boron-doped diamond" AND "titanium"` query returns only **128 articles (2015+)**, and that is an *upper bound* that includes papers merely comparing BDD against titanium-based anodes. Adding Nb/Ta/Si raises the substrate-tagged pool (unmeasured), and the additional requirement of Raman-derived doping data *plus* a quantitative performance/failure outcome will cut it again. My estimate is **60–120 qualifying records — reachable at 100, but not safely**. **Effort estimate: 300–450 person-hours**, higher than a pure-volume estimate would suggest, because the substrate and Raman conjunctures force full-text inspection of a large fraction of ~300 substrate-tagged candidates to discard false hits. Screening ~600–800 titles/abstracts, full-texting ~300–400, extracting and adjudicating ~100–150 records with double-entry on a 20% subset.

**Domain 2 (PVDF/HAp membranes): 100+ records is NOT realistically achievable as currently scoped.** The total intersection is **122 works (90 journal articles)**, with only **~20 papers/year** in recent years, distributed across dozens of venues none of which holds more than 5 papers — and with **no presence in Journal of Membrane Science, Desalination, or Separation and Purification Technology**. After applying "≥2 characterization modalities AND ≥1 quantitative performance outcome", the realistic yield is **30–60 records**, i.e. near the proposal's original 15–25 target. Effort to get there is not the problem — **~120–200 person-hours** — the *ceiling* is. Under the current criteria the domain saturates well short of 100, no matter how much effort is applied.

**Therefore, the answer to "can we push both domains to 60–100+?" is: probably yes for BDD (at 100, with real risk), and no for PVDF/HAp.** Concretely:

- **Keep Domain 1, but de-risk it first.** The volume is there, but the substrate criterion is far more restrictive than the headline count suggests (128 articles even *mention* titanium, as an upper bound). **Before writing the proposal, run four OpenAlex queries** — `"boron-doped diamond"` AND each of `"titanium"`, `"niobium"`, `"tantalum"`, `"silicon"` — and hand-sample ~30 hits per substrate to measure what fraction are true BDD-on-that-substrate studies that also report Raman doping data. That one afternoon of work determines whether Domain 1 targets 100 or 60. Also pilot the "failure outcome" conjunction, which I expect to be the largest single source of attrition (service life and delamination are usually studied in dedicated durability papers, not co-reported with Raman doping).
- **Rescope Domain 2 in one of three ways**, in descending order of strength:
  1. **Reframe around an existing gold standard.** Make the second domain halide perovskites and position the contribution as extraction-and-validation against the Perovskite Database (>40,000 devices). This removes the "no ground truth" weakness entirely and is the strongest defensible design.
  2. **Swap to solid-state electrolytes** (3,474 articles) if the goal is a same-scale, genuinely-different extraction challenge — EIS-derived ionic conductivity is figure-bound, the honest contrast the current framing is reaching for.
  3. **Broaden the PVDF scope** (e.g. PVDF + any ceramic filler, or PVDF ultrafiltration membranes within the 9,372-paper pool) and relax the two-modality requirement. This preserves the application story but abandons the "HAp" specificity that currently gives the domain its identity.
- **Report precision/recall explicitly**, following the Cole-group precedent (72% precision / 61% recall at 56,037 records). Budget for **~1.6 false positives per true positive**; a "100-record" target means ~160–250 candidates plus adjudication. Plan a hand-annotated held-out set of ~200–250 randomly selected papers for validation, since neither domain supplies one.
- **Pilot the "failure outcome" criterion before committing.** Service life and delamination are usually studied in dedicated durability papers, not co-reported with Raman doping. This conjunction — not raw volume — is the likeliest cause of Domain-1 attrition.
