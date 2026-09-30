# Papers needed — a shopping list

Six items. Each is blocked by a paywall or a bot check that automated retrieval cannot pass, and each
is load-bearing somewhere in the paper. **Priority order is deliberate: item 1 changes the corpus plan,
items 2–3 are the nearest competitors to the core contribution, and item 6 gates whether Domain 2 is
viable at all.**

For each, what is needed is stated precisely. A full PDF is welcome, but in several cases one table or
one paragraph is enough.

---

## 1. Kummerfeld, Williams & Ma (2023) — the power table ⭐ highest priority

> Kummerfeld, E., Williams, L. & Ma, S. (2023). Power analysis for causal discovery.
> *International Journal of Data Science and Analytics* 17(3), 289–304.
> DOI **10.1007/s41060-023-00399-4**

**What is needed:** **the numeric power table** (their Table 3), or the URL of the Shiny interface the
paper says it provides for searching it.

**Why it is blocked:** the open manuscript at PMC11581182 truncates at the same point on every fetch
regardless of URL anchor, and `web_fetch` rejects PDFs outright.

**Why it matters:** this is the **first and only published power-analysis method for causal discovery**,
and it is the load-bearing citation for the corpus-size argument. The paper currently rests that
argument on Scheines & Ramsey's floor of n = 100 instead. **Without this table, the corpus target in
Stage 1 is set by a proxy rather than by the primary source.** If the Shiny app is reachable, sending
just its URL is enough — the numbers can be read from it.

---

## 2. JCDL 2024 — uncertainty quantification for scientific tables

> *Scientific Table Data Extraction with Uncertainty Quantification.*
> JCDL 2024. DOI **10.1145/3677389.3702616**

**What is needed:** abstract, method, and — most importantly — **what uncertainty measure they use**.

**Why it is blocked:** ACM Digital Library returned HTTP 403.

**Why it matters:** the title is the closest match to this study's contribution of anything found. If
they quantify table-extraction uncertainty and evaluate it, the novelty statement in Section 2 needs a
fourth revision. If they only estimate it without validating against error, this study is unaffected
and the citation strengthens the gap claim. **This is the single item most likely to change the
paper.**

---

## 3. ICDAR 2025 — uncertainty-aware scientific table extraction

> *Uncertainty-Aware Complex Scientific Table Data Extraction.*
> ICDAR 2025. DOI **10.1007/978-3-032-04624-6_4**

**What is needed:** abstract and method section.

**Why it is blocked:** Springer returned a redirect that automated retrieval does not follow.

**Why it matters:** same role as item 2 — a close competitor by title. Two independent groups working
on "uncertainty-aware scientific table extraction" in consecutive years would mean the field is
converging on this problem, which is worth knowing and worth saying.

---

## 4. CSDA — causal discovery from corrupted data

> Shin, Chung, Hwang & Park. *Discovering causal structures in corrupted data: frugality in anchored
> Gaussian DAG models.* Computational Statistics & Data Analysis.
> DOI **10.1016/j.csda.2025.108267**
> ⚠ Note: Crossref gives the issue date as **January 2026**, not 2025.

**What is needed:** the abstract and the main result.

**Why it is blocked:** ScienceDirect returned HTTP 403. Metadata and DOI are confirmed via Crossref;
**the finding is not**, so the paper currently cites only the existence of this work and makes no claim
about what it shows.

**Why it matters:** it sits directly in the measurement-error-in-causal-discovery strand that
constrains the novelty claim (Section 2.5).

---

## 5. MaTableGPT — is the dataset released?

> Yi, G. H. et al. (2025). MaTableGPT: GPT-based table data extractor from materials science
> literature. *Advanced Science* 12(16). DOI **10.1002/advs.202408221**

**What is needed:** the **data and code availability statement** — specifically whether the extracted
dataset or the pipeline is deposited anywhere (GitHub, Zenodo, HuggingFace).

**Why it is blocked:** Wiley returned HTTP 403, and no deposit was found by searching those
repositories directly.

**Why it matters:** the paper reports F1 near 97 % and is cited as the state of the art for tabular
extraction. If its extracted dataset is public, **it is a ready-made comparison corpus with no
extraction cost** for the tabular arm of Domain 2. If it is not public, that is itself a finding worth
one sentence, since the field's headline extraction result would then be unreproducible.

---

## 6. Perovskite Database — access and linkage check

> Jacobsson, T. J. et al. (2022). An open-access database and analysis tool for perovskite solar cells
> based on the FAIR data principles. *Nature Energy*. https://perovskitedatabase.com/

**What is needed:** answers to four questions, obtainable by visiting the site and downloading one
export.

1. **Is the full database downloadable?** What licence, and in what format?
2. **What fraction of recent records (2018+) carry a DOI?** This is the **go/no-go** for Domain 2.
3. **Is there a stable record identifier** that can be tied to a specific paper and a specific device
   within that paper?
4. **What is the current device count?**

**Why it is blocked:** the site failed to fetch, and Nature redirected to an identity provider.

**Why it matters:** the whole of Domain 2 depends on the database serving as a **per-value** gold
standard. Existence is verified; usability is not. The decision rule is in
`fieldwork/perovskite_matching_checklist.md`: **DOI coverage below ~70 % means the linkage is too weak
and Domain 2 must be re-planned before screening starts.**

---

## Nice to have, lower priority

If any of these are easy to reach, they would upgrade citations currently marked as pending a second
confirmation. None changes the design.

| Item | Identifier | Needed |
|---|---|---|
| Ghosh et al. (2024), *Findings of ACL* | arXiv:2406.05348 | Full title, and **which two materials datasets** were used — this is the proposed vehicle for building our gold standard |
| Kim et al. (2025), AAAI Symposium Series 7(1) 539–546 | DOI 10.1609/aaaiss.v7i1.36929 | The conformal procedure in detail, since we adopt it |
| Polak & Morgan (2024), *Nature Communications* | DOI 10.1038/s41467-024-45914-8 | Confirm the ~90 % precision/recall claim, and whether they report any uncertainty measure |
| Xiao et al. (2025), *ICML* | arXiv:2505.01997 | Confirm the RLHF miscalibration claim in the wording we attribute to them |
| Sinha, Tadepalli & Ramsey (2021), *PLOS ONE* | DOI 10.1371/journal.pone.0245776 | The Sachs ground-truth caveats, quoted precisely |

---

## A note on how to send them

Anything readable is fine — a PDF, a screenshot of the relevant table, or pasted text. If you paste,
**paste the table or paragraph itself rather than a summary**, since the point is the exact numbers and
the exact wording. Anything sent will be recorded in the proposal's Appendix A with its verification
status upgraded from "pending second confirmation" to "verified directly".
