# Horley corpus: differences & discoveries log

Running record of (a) how the Horley-informed encoding differs from Barthel and (b) any
decipherment-relevant discovery that follows. Quantitative diffs are **generated** by
`src/compare_corpora.py` (`results/corpus_diff.txt` / `.json`) so they can't drift from
the actual encodings; this file interprets them and tracks provenance.

> **Read `data/README_horley.md` first.** The shipped `horley_map.json` is seeded with
> **illustrative placeholders**, not verified Horley decisions. Nothing below is a claim
> about the script until the corresponding map entry reaches `confidence: published` and
> cites a primary source (Horley 2021 / INSCRIBE). Every affected code is printed with its
> confidence in `corpus_diff.txt`.

## How to read the difference report

`python src/compare_corpora.py` writes, for Barthel vs Horley:
- sign-inventory size and net merge/split/ligature counts;
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

1. Run N seeds on **Barthel** and the **same** N seeds on **Horley** (`run_all.sh` with
   `RR_CORPUS=barthel` then `RR_CORPUS=horley`; Horley lands in `../results_horley`).
2. Establish the Barthel baseline noise floor: cross-chain disagreement among the Barthel
   seeds (the lab already reports ~95% sign-assignment disagreement — that is the floor).
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
