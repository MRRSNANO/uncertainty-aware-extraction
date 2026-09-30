# Fieldwork 1 — BDD substrate conjunction sampling

**Purpose.** Determine whether Domain 1 can supply the record count the power analysis will demand.
The whole corpus plan hinges on one unmeasured number, and it can be measured by hand in an afternoon.

## The problem this measures

`"boron-doped diamond"` returns 3,545 articles (2015–2026). `"boron-doped diamond" AND "titanium"`
returns **128**. That collapse is the entire feasibility question for Domain 1 — and 128 is an
*upper bound*, because the query matches any paper that merely mentions titanium anywhere, including
studies that compare BDD against Ti₄O₇ anodes without ever depositing BDD on titanium.

Inclusion requires the **conjunction** of four conditions:

1. BDD grown or characterised on a **named substrate** (Ti, Nb, Ta, Si, W, Mo);
2. **Raman-derived** doping or sp³/sp² information;
3. at least one **quantitative performance or failure outcome**;
4. peer-reviewed journal article.

Nobody knows the rate at which all four co-occur. This task measures it.

---

## Step 1 — run the four queries

Execute each in Scopus and Web of Science separately, 2015-01-01 to the search date, document type =
Article or Review, language = English. **Record the exact hit count and the execution date**, because
a PRISMA count without a date is not reproducible.

```
A = ("boron-doped diamond" OR "boron doped diamond" OR "BDD electrode" OR "BDD anode")
B = (Raman OR "sp3/sp2" OR "sp2/sp3" OR "doping level" OR "boron concentration")
C = ("critical current density" OR "Faradaic efficiency" OR "service life" OR
     "electrode lifetime" OR delamination OR "current efficiency" OR "cell voltage")

Query = A AND B AND C AND <substrate>
```

Substitute `<substrate>` in turn with each of:

| # | Substrate term |
|---|---|
| 1 | `(titanium OR Ti)` |
| 2 | `(niobium OR Nb)` |
| 3 | `(tantalum OR Ta)` |
| 4 | `(silicon OR Si)` |

Optional fifth: `("tungsten" OR "molybdenum" OR W OR Mo)`, expected to be small.

### Recording table

| Substrate | Database | Hits | Date run |
|---|---|---|---|
| Ti | Scopus | | |
| Ti | WoS | | |
| Nb | Scopus | | |
| Nb | WoS | | |
| Ta | Scopus | | |
| Ta | WoS | | |
| Si | Scopus | | |
| Si | WoS | | |

---

## Step 2 — hand-sample 30 hits per substrate

Take the **first 30 hits by relevance** for each substrate in Scopus. Do not cherry-pick; if you are
tempted to skip a paper because it looks unlikely, that is precisely the paper to score, because the
temptation is the bias this exercise exists to avoid.

For each, open the abstract (and the full text only when the abstract is ambiguous) and score **four
binary flags**. Do not score quality, novelty, or importance — only presence or absence.

| Column | Meaning |
|---|---|
| `paper_id` | DOI or first author + year |
| `substrate` | Ti / Nb / Ta / Si |
| `s1_named_substrate` | Does it name the substrate on which the BDD was grown or used? |
| `s2_raman` | Does it report Raman-derived doping or sp³/sp² information? |
| `s3_outcome` | Does it report a quantitative performance or failure value? |
| `s4_journal_article` | Peer-reviewed journal article, not a conference paper or review? |
| `all_four` | 1 only if s1–s4 are all 1 |
| `notes` | One line. Especially: is the value in a table, in prose, or only in a figure? |

### Recording template (paste into a spreadsheet)

```csv
paper_id,substrate,s1_named_substrate,s2_raman,s3_outcome,s4_journal_article,all_four,value_location,notes
```

**The `value_location` column is not optional.** It records whether the outcome value was
table-bound, prose-bound, or figure-only. That single column is what tests the study's actual
cross-domain contrast, and it costs nothing to record now and is impossible to reconstruct later.

---

## Step 3 — compute the conjunction rate and the implied yield

```
conjunction_rate    = mean(all_four)                      over the 30 sampled per substrate
implied_hits        = hits(substrate) * conjunction_rate
usable_records      = implied_hits * records_per_paper     (use 1.2 unless you observe otherwise)
```

Sum `usable_records` across the four substrates. That is the Domain 1 ceiling.

### Decision rule — fix this now, before looking at the numbers

| Domain 1 ceiling | Action |
|---|---|
| ≥ 100 records | Proceed as planned. Power target is reachable. |
| 60–99 records | Proceed, and **report n as a constraint** in the paper rather than a design choice. Plan B applies if the power analysis demands more. |
| 30–59 records | Reframe as a single-domain calibrated methodological study with Domain 2 as a reduced-scope transfer test. |
| < 30 records | The empirical half is not viable at this scope. Reframe around the simulation contribution. |

**Do not widen the inclusion criteria after this measurement to reach a target.** Widening after
seeing the number is exactly the practice the PRISMA protocol was written to prevent. If the ceiling
is too low, change the *study*, not the criteria.

---

## What this task costs

Four queries and 120 abstract-level scores. Realistically **one working day**, most of it reading.
It produces the single number that determines whether Domain 1 targets 100 records or 60, and that
number is an input to the power analysis rather than an output of it.

## What it does not establish

It measures *conjunction* among indexed, retrievable articles. It does not measure whether the values
inside those articles are actually extractable — that is what the gold-standard annotation measures
later, and attrition between "paper qualifies" and "value successfully extracted" is expected to be
substantial. Record the gap when you reach it; it belongs in the PRISMA flow.
