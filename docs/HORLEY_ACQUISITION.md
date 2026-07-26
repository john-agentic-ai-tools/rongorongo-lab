# Acquisition plan: re-tracings, 3D data, and a faithful transliteration

## Why

Every statistic in this lab is computed over a transliteration, and the transliteration
embeds contestable **sign-merging decisions** — which incisions are one sign, which shapes
are allographs, which are ligatures. The solvers inherit them. Re-running the pipeline on a
better-resolved encoding is, per the README's own "ways to falsify" list, one of the
highest-value experiments available.

**The 2026-07-23 version of this document had the priority wrong.** It treated Horley 2021 as
the unblocking purchase and described the situation as "no machine-readable Horley encoding
exists". That is true of Horley specifically, but it obscured a larger and cheaper problem:
the *baseline* corpus, `data/tablets_simple.json` (Barthel via rongopy), is itself a heavily
lossy re-encoding, and the C.E.I.P.P. extended-Barthel text that repairs it has been free and
online for twenty years. Fixing the baseline turned out to matter more than any of the
sources below, and cost nothing (§1).

## Sources, in priority order

### 1. C.E.I.P.P. extended-Barthel transliteration — ACQUIRED, FREE, MACHINE-READABLE

- All 26 inscribed objects at `http://kohaumotu.org/rongorongo_org/translit/{a,b,mamari,d..z}.html`,
  published by the Commission Rongorongo of the Cercle d'Études sur l'Île de Pâques et la
  Polynésie, who hold Barthel's bequeathed materials and corrected the corpus against his
  original rubbings.
- Preserves what rongopy discarded: allographic suffixes (`600V`, `385y`, `074f`, `052x`,
  `030a`) and the full sign-combination punctuation (`.` linked, `:` stacked, `;` linked
  stack), plus per-sign doubtful/illegible markers.
- **Terms:** *"There are no restrictions on copying and distributing the contents of this site
  as long as the sources are acknowledged and the distribution is non-profit."*
  (`/copy.html`). Non-profit-only does not sit comfortably inside a GPL-3.0 tree, so the built
  corpus is **not committed** — `src/fetch_ceipp.py` rebuilds it locally and it is gitignored.
- **Status: done.** `RR_CORPUS=ceipp`; see [../data/README_ceipp.md](../data/README_ceipp.md).
- Also available and not yet used: `concord/concord1.zip` + `concord2.zip`, a full
  sign-by-sign concordance of the corpus in ASCII (legacy *implode* compression — Python's
  `zipfile` cannot read it; use 7-Zip or `unzip`).

### 2. INSCRIBE project (S. Ferrara et al., U. Bologna, ERC) — 3D GROUND TRUTH

- Photogrammetry + structured-light 3D at sub-mm precision, which distinguishes deliberate
  incisions from post-depositional scratches far better than rubbings or photographs.
- **Échancrée (item D): acquired.** Ferrara, S. et al. (2022), "Modelling the Rongorongo
  tablets: a new transcription of the Échancrée tablet and the foundation for decipherment
  attempts," *Digital Scholarship in the Humanities* 37(2): 497–518, doi:10.1093/llc/fqab070.
  **CC BY-NC open access**; the 212-element transcription is printed line by line in §4.1.1–2.
  Transcribed into [../data/tablets_echancree.json](../data/tablets_echancree.json) and
  compared by `src/compare_echancree.py`. Open PDF mirror: `cris.unibo.it`.
  *Known gap:* the article marks doubtful readings by **underlining**, which survives neither
  the publisher HTML nor PDF text extraction — see the outreach draft in §3.
- **Correction to the previous version of this document:** `site.unibo.it/inscribe/en/output/3d-models`
  does **not** offer downloadable models. It offers rendered YouTube video of items B
  (Aruku Kurenga) and C (Mamari), with the request *"if you use or repost these models,
  acknowledge that they were produced by the ERC INSCRIBE Project, based at the University of
  Bologna."* No licence is stated. There is presently nothing there to ingest.
- **Mamari 3D** (ISPRS Archives XLII-2/W18, 2019): acquisition + processing method, no data.
- **Four Rome tablets**: sub-mm models, viewable in the INSCRIBE 3D Interactive Web Viewer.

### 3. Direct contact — the biggest remaining effort saver

TODO

### 4. Horley (2021), *Rongorongo: Inscribed Objects from Rapa Nui* — the refinement layer

- Rapanui Press, Viña del Mar, 2021. English, softcover, xx + 637 pp.
  ISBN **978-956-9337-58-1**.
- **Price correction:** listed at **85,000 CLP** on `rapanuipress.com`, and *"precio no
  incluye envío"* — shipping is extra and no international destinations are stated. The
  ~52,000 CLP in the previous version of this document came from the 2023 *Cryptologia*
  review and is out of date. Also stocked by Feria Chilena del Libro (Chile) and
  bookdelivery.com (Italy, ships internationally). Record purchase provenance here when done.
- **Use:** the authoritative source for the merge/split/ligature decisions that populate
  `horley_map.json`, and for full per-tablet re-encoding into `data/tablets_horley.json` for
  high-value tablets — start with Mamari (the lunar calendar Ca6–Ca9 is the lab's semantic
  anchor) and any tablet where Horley's tracing visibly departs from Barthel.
- It is a **refinement over §1, not a substitute for it.** Horley revises Barthel's taxonomy;
  the C.E.I.P.P. text is what Barthel's taxonomy actually says. Both are needed, in that order.

### 5. Supporting open literature

- Horley, P. (2005), "Allographic Variations and Statistical Analysis of the Rongorongo
  Script," *Rapa Nui Journal* 19(2): 107–116 — directly on allographs. Open at
  `kahualike.manoa.hawaii.edu/rnj/vol19/iss2/6/`.
- Pozdniakov, K. & Pozdniakov, I. (2007), "Rapanui Writing and the Rapanui Language,"
  *Forum for Anthropology and Culture* 3: 3–36 — argues ~52 basic signs; a method for
  reducing Barthel codes to allographs/ligatures. Open access on HAL: `hal-01389639`.
- Guy, J.B.M. on taxograms (Barthel 200/400) — handled as `TAXOGRAMS` in `common.py`.

## Encoding strategy (layered)

1. **Faithful baseline (done).** `ceipp` restores Barthel's own allographic and ligature
   distinctions. The two reading policies `RR_CEIPP_VARIANTS` and `RR_CEIPP_GROUPS` express
   the sign-merging question directly, as a load-time decision recorded in every result file,
   rather than as hand-written map entries.
2. **Transform layer.** `data/horley_map.json` encodes *Horley's* revisions as merges, splits
   and ligatures over Barthel codes, each cited with a `confidence`. It now applies over
   `ceipp` — but its shipped placeholder entries are keyed on rongopy-style bare codes and
   therefore barely fire; they must be rewritten against extended codes.
3. **Book-driven extension.** With Horley 2021 in hand, extend the map and fully re-encode
   high-value tablets into `data/tablets_horley.json` (supersedes the transform per tablet).
4. **3D validation.** Fold 3D-verified transcriptions in as ground truth; the Échancrée is
   done, and its disagreements are logged in [HORLEY_FINDINGS.md](HORLEY_FINDINGS.md).

All of it feeds one seam: `common.load_tablets(source=...)`.

## Licensing / attribution

- This repo is GPL-3.0; `tablets_simple.json` derives from rongopy (GPL-3.0) on Barthel (1958).
- **C.E.I.P.P.:** attribution + non-profit. Not committed; `fetch_ceipp.py` rebuilds it.
- **INSCRIBE / Ferrara 2022:** CC BY-NC. What is stored is the transcription — a cited
  catalogue of readings — not the article's drawings, figures, or models.
- **Do not reproduce Horley's drawings or INSCRIBE's models/images in this repo.** What we
  store is a derived *catalogue of sign-taxonomy facts* with citations: analysis, not
  reproduction. Keep it that way, and keep `source` on every map entry.
- Verify the licence of anything new before committing it, and record it here.

## Status log

- **2026-07-25 — C.E.I.P.P. baseline + Échancrée ground truth acquired.**
  `fetch_ceipp.py` builds all 26 objects (301 lines, 11,507 juxtaposition groups, 15,370
  atomic signs). Inventory `barthel` 239 → `ceipp` 1584; tokens/U 17.7× → 2.2×; under
  `variants=strip` 629 signs and 5.9×; under `groups=fused` 3232 signs and 0.5×. The
  Échancrée transcription is encoded and diffed against C.E.I.P.P. item D. `barthel` output
  is unchanged and remains the default. Findings in
  [HORLEY_FINDINGS.md](HORLEY_FINDINGS.md); outreach drafted, unsent. **Next: buy Horley
  2021 (85,000 CLP + shipping), then rewrite `horley_map.json` against extended codes.**
- 2026-07-23 — Transform layer + `source='horley'` switch + `compare_corpora.py` landed;
  `horley_map.json` seeded with **illustrative placeholders only** (not verified against any
  primary source).
