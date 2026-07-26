# Corpus differences & discoveries log

Running record of (a) how each re-encoding differs from the one the lab started with and
(b) any decipherment-relevant discovery that follows. Quantitative diffs are **generated**
— by `src/compare_corpora.py` (`results/corpus_diff_<a>_vs_<b>.txt` / `.json`) for
transliterations, and by `src/compare_echancree.py`
(`results/echancree_vs_ceipp.txt`) for the one object with 3D ground truth — so they can't
drift from the actual encodings; this file interprets them and tracks provenance.

> **Read `data/README_horley.md` first.** The shipped `horley_map.json` is seeded with
> **illustrative placeholders**, not verified Horley decisions. Nothing below is a claim
> about the script until the corresponding map entry reaches `confidence: published` and
> cites a primary source (Horley 2021 / INSCRIBE). Every affected code is printed with its
> confidence in the difference report.

## How to read the difference report

`python src/compare_corpora.py [SRC_A] [SRC_B]` writes, for any two sources (either may be
qualified with a C.E.I.P.P. reading policy, e.g. `ceipp:variants=strip`):

- sign-inventory size and, when `horley` is one side, net merge/split/ligature counts;
- unigram frequency and rank shifts for the most frequent signs;
- Shannon **unicity distance** recomputed under each inventory (unigram approximation) and
  `tokens/U` — the README's "× unicity distance" figure. Merging signs shrinks the
  alphabet (lowers `H(key)`) but also changes redundancy, so `U` moves in a way that is
  worth watching: it tells you whether a re-tracing makes the corpus *more or less*
  over-determined for a substitution attack.

## Attribution methodology (change vs. noise)

The solvers are stochastic (simulated annealing), so a different mapping under Horley is
**not** by itself evidence of anything. A difference counts as attributable to the
re-tracing only if it exceeds the solver's own run-to-run instability:

1. Run N seeds on each corpus being compared (`run_all.sh` with `RR_CORPUS=barthel`, then
   `ceipp`, then `horley`; each non-default corpus lands in `../results_<corpus>`).
2. Establish the baseline noise floor separately **within each corpus**: cross-chain
   disagreement among its own seeds (on Barthel the lab already reports ~95%
   sign-assignment disagreement — that is the floor there, and `ceipp` needs its own,
   which has not yet been measured).
3. For a sign whose reading changes between corpora, the change is attributable only if
   the sign is **stable within** each corpus (high cross-seed agreement in both) **and
   differs between** them. A change on a sign that is unstable within Barthel is noise.
4. Only signs actually touched by `horley_map.json` (or their immediate LM neighbours) can
   be *directly* caused by the re-tracing; a shift on an untouched, distant sign is a
   second-order LM effect — note it, don't over-read it.
5. Confirm the responsible map entry is `published`/`preliminary`, not `illustrative`,
   before recording a finding.

## The lab's own falsification bar (unchanged)

Any reading must still survive (a) cross-chain agreement, (b) lexical match rate above a
random-bijection baseline, (c) held-out semantic anchors (the Mamari lunar calendar,
Ca6–Ca9). The Horley corpus does not lower this bar — it changes the *input* to it.

## Log

### 2026-07-25 — The baseline corpus was the bigger problem

Not a finding about the script. A finding about the lab's own input, and it bounds every
number the README reports.

`data/tablets_simple.json` (Barthel via rongopy) is a lossy re-encoding. Rebuilding the same
Barthel transliteration from the C.E.I.P.P. extended text (`src/fetch_ceipp.py`; see
[../data/README_ceipp.md](../data/README_ceipp.md)) recovers what it dropped:

| | `barthel` | `ceipp` |
| --- | --- | --- |
| sign inventory | 239 | **1584** |
| tokens | 11,742 | 14,179 |
| allographic suffixes | none | 23.9% of tokens |
| linking / stacking | discarded | preserved |
| tokens / unicity distance | **17.7×** | **2.2×** |

Three specifics worth recording:

1. **The over-determination is largely an artefact.** The README's negative result leans on
   the corpus being many times the Shannon unicity distance — i.e. so over-determined that a
   correct substitution key would be forced. Under a faithful encoding that margin falls by a
   factor of eight, and under a ligature-level reading (`RR_CEIPP_GROUPS=fused`, 3232 signs)
   it reaches **0.5× — below** the unicity distance, where a unique solution is not
   guaranteed to exist at all. The negative result itself is unaffected (failure to recover a
   key is still failure), but *the reason given for it* is corpus-encoding-dependent and the
   README's framing needs qualifying.
2. **21.2% of `barthel` tokens are `200`/`400`/`000`,** which `common.TAXOGRAMS` then strips.
   Under `ceipp` the 200–/400– series are intact (`208`, `225`, `290`, `380`, `606`, `670`…),
   so that share is a rongopy collapse being discarded as if it were Guy's taxograms. The
   `TAXOGRAMS` set is deliberately left unchanged pending evidence, but any conclusion drawn
   from `barthel` about sign 200 or 400 is suspect.
3. **`barthel` contains codes that are not Barthel's.** `901` and `6` appear in
   `tablets_simple.json`; the C.E.I.P.P. catalogue states there are no signs beyond 791.

Sensitivity, now measurable directly (`compare_corpora.py ceipp ceipp:variants=strip` etc.):
merging every allograph onto its base code takes 1584 → 629 signs and 2.2× → 5.9×. That is
the size of the effect the Horley experiment is trying to detect — and it is large enough
that no cross-corpus solver comparison should be read before the noise floor in
"Attribution methodology" above has been established on `ceipp` itself.

**Not yet done:** `horley_map.json` still holds `illustrative` placeholders keyed on
rongopy-style bare codes, so over a `keep` corpus they barely fire (1584 → 1582). No Horley
claim is made or implied.

### 2026-07-25 — Échancrée (item D): first 3D ground-truth comparison

`src/compare_echancree.py`, from the CC BY-NC transcription in Ferrara et al. 2022 §4.1.1–2
(`data/tablets_echancree.json`) against C.E.I.P.P. item D. Output:
`results/echancree_vs_ceipp.txt`.

- **7 of 14 lines** have matching graphic-element counts and are comparable position by
  position; on those, **61 agree, 42 differ**. The other 7 lines disagree on how the incisions
  are segmented at all — which is itself the sign-merging problem, observed directly.
- Element totals: INSCRIBE 208 (as parsed from their own printed transcription; they report
  **212**, so the two want reconciling by hand), C.E.I.P.P. 211.
- Sorting the 42 disagreements by kind: **4 RECOVERED** (C.E.I.P.P. reads only a lacuna where
  the 3D model reads signs), **23 CODE** (different sign numbers), **4 ORDER** (same codes,
  different sequence — the stacking convention), **11 SUFFIX** (same codes, different
  allographs).

The four RECOVERED positions are the candidate discoveries:

| position | INSCRIBE 3D | C.E.I.P.P. |
| --- | --- | --- |
| Da2.11 | `445.107.1` | `000!` |
| Da4.10 | `(6x.)206s` | `000!` |
| Db5.13 | `445` | `000!` |
| Db5.14 | `445` | `000!` |

Da2.11 is independently corroborated: Ferrara et al. §4.2.2 discuss exactly this position as
"a unique ligature with three components, which Barthel left untranscribed", and use a
cross-section of the 3D model to show the attaching line is deliberately incised. That is a
real sign recovered from a real lacuna — the first entry in this log that is a fact about the
object rather than about an encoding.

**Bounds on all of the above.** The article marks doubtful readings by underlining, which
survives neither the publisher HTML nor PDF text extraction, so no element in
`tablets_echancree.json` can be assumed firm; alternatives (`381/741`) are scored as
agreement if either reading matches; and the 7 non-comparable lines are excluded, so 42 is a
floor. 

**Not yet chased:** whether any recovered incision falls inside a parallel passage (H/P/Q
share content) — item D has no known parallel, so this needs another 3D-transcribed object.

### 2026-07-23 — Infrastructure + illustrative baseline (NOT findings)
- Pluggable `source='horley'` seam, transform layer, and `compare_corpora.py` landed.
- With the **illustrative** seed map, `compare_corpora.py` reports: inventory 239 → 238
  (−1); `tokens/U` 17.7× → 18.3×; signs removed vs. Barthel: `074, 075, 280, 660`; signs
  added: `H006a, H074, H660`; sign `010` jumps rank 4 → 2 (the 280→[200,010] ligature
  emits `010`). **These demonstrate the mechanism only** — every affected code is flagged
  `illustrative`. No decipherment inference is drawn.

### Candidate discoveries to chase (once primary sources are encoded)
- **INSCRIBE Échancrée:** 212 graphic elements vs. prior estimates — encode directly and
  list every element Barthel's rubbing missed; each is a candidate incision-level
  discovery. Cross-check whether any missed incision falls inside the calendar or a
  parallel passage (H/P/Q share content).
- **Merged/over-split signs:** for each verified Horley merge, check whether it collapses
  two signs the syllabic solver had assigned *different* stable readings — a collision
  there is a direct, testable consequence of the re-tracing.
- **Unicity movement:** record whether the verified Horley inventory raises or lowers
  `tokens/U`; a large drop would weaken, a rise would strengthen, the README's negative
  result about plain syllabic substitution.

_Append new entries here with date, the map entry (code + confidence + source) responsible,
the generated diff numbers, and the attribution test result._
