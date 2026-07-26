# Acquisition plan: Horley re-tracings & INSCRIBE 3D data

## Why

Every statistic in this lab is computed over the Barthel (1958) transliteration
(`data/tablets_simple.json`, via rongopy). Barthel's transliteration embeds contestable
**sign-merging decisions** — which incisions are one sign, which are allographs, which
are ligatures — and the solvers inherit them. Two later bodies of work are higher
resolution and re-open exactly those decisions. Re-running the pipeline on a
Horley-encoded corpus is, per the README's own "ways to falsify" list, one of the
highest-value experiments available.

**Current blocker:** no machine-readable Horley encoding exists. Horley's re-tracings are
drawings in a printed book; the INSCRIBE 3D work covers only a few tablets. The lab now
has a working transform layer (`data/horley_map.json` → `source='horley'`) so the
experiment can proceed incrementally as data is acquired. This document is the acquisition
roadmap.

## Sources, in priority order

### 1. Horley (2021), *Rongorongo: Inscribed Objects from Rapa Nui* — PRIMARY
- Rapanui Press (Editorial Rapanui Press), Viña del Mar, 2021. English, softcover,
  xx + 637 pp. ISBN **978-956-9337-58-1**. Listed ~52,000 CLP.
- Contains revised tracings of the whole corpus plus iconographic and carving analysis.
- **Acquire:** order from Rapanui Press (`rapanuipress.com`); it also circulates via
  academic booksellers. Record purchase provenance in this file when done.
- **Use:** it is the authoritative source for the merge/split/ligature decisions that
  populate `horley_map.json`, and for full per-tablet re-encoding into
  `data/tablets_horley.json` for high-value tablets (start with Mamari — the lunar
  calendar Ca6–Ca9 is the lab's semantic anchor — and any tablet where Horley's tracing
  visibly departs from Barthel).

### 2. INSCRIBE project (S. Ferrara et al., U. Bologna, ERC) — 3D GROUND TRUTH
- Photogrammetry + structured-light 3D models at sub-mm precision; distinguishes
  deliberate incisions from post-depositional scratches better than rubbings or photos.
- **Échancrée tablet**: new transcription with **212 graphic elements**, exceeding prior
  estimates and resolving ambiguities — Ferrara, S. et al. (2022), "Modelling the
  Rongorongo tablets: a new transcription of the Échancrée tablet and the foundation for
  decipherment attempts," *Digital Scholarship in the Humanities* 37(2): 497–518 (open
  PDF on the INSCRIBE site / academia.edu / the Bologna CRIS repository).
- **Mamari tablet 3D** (ISPRS Archives XLII-2/W18, 2019): acquisition + processing.
- **Four Rome tablets**: sub-mm 3D models; interactive web viewer.
- **Acquire:** models/outputs at `site.unibo.it/inscribe/en/output/3d-models`; web viewer
  linked from the project site. **Check each asset's license before ingesting** — 3D
  models and transcriptions may carry their own terms distinct from this repo's GPL-3.0.
- **Use:** ground-truth spot-check. Where INSCRIBE gives a full transcription
  (Échancrée), encode that tablet directly into `data/tablets_horley.json`; treat
  disagreements with Barthel as candidate discoveries (log them in `HORLEY_FINDINGS.md`).

### 3. Direct contact — MACHINE-READABLE DATA
- Ask Paul Horley and the INSCRIBE team whether a machine-readable sign catalogue or
  transcription table exists (a code-level allograph/ligature table would let us populate
  `horley_map.json` verbatim instead of by hand). This is the single biggest effort saver
  if it exists.

### 4. Supporting open literature — populate the map now
- Horley, P. (2005), "Allographic Variations and Statistical Analysis of the Rongorongo
  Script," *Rapa Nui Journal* 19(2): 107–116 — directly on allographs.
- Pozdniakov, K. & Pozdniakov, I. (2007), "Rapanui Writing and the Rapanui Language,"
  *Forum for Anthropology and Culture* 3: 3–36 — argues ~52 basic signs; a method for
  reducing Barthel codes to allographs/ligatures.
- Guy, J.B.M. on taxograms (Barthel 200/400) — already handled as `TAXOGRAMS` in
  `common.py`.

## Encoding strategy (layered — decided with maintainer)

1. **Transform layer (runnable now).** `data/horley_map.json` encodes sign-taxonomy
   decisions as merges/splits/ligatures over Barthel codes. Seed from open literature
   (§4), each entry cited with a `confidence`. This targets the exact concern (sign
   merging) at a fraction of the cost of re-transcription.
2. **Book-driven extension.** With Horley 2021 in hand, extend the map and fully
   re-encode high-value tablets into `data/tablets_horley.json` (supersedes the transform
   per-tablet).
3. **INSCRIBE validation.** Fold 3D-verified transcriptions in as ground truth; encode
   Échancrée directly; log Barthel-vs-3D disagreements as discoveries.

All three feed the one seam: `common.load_tablets(source='horley')`.

## Licensing / attribution

- This repo is GPL-3.0; the corpus derives from rongopy (GPL-3.0) on Barthel (1958).
- **Do not reproduce Horley's drawings or INSCRIBE's models/images in this repo.** What we
  store is a derived *catalogue of sign-taxonomy facts* (which Barthel codes are
  allographs/ligatures/splits) with citations — analysis, not reproduction. Keep it that
  way, and keep `source` on every map entry.
- Verify INSCRIBE asset licenses before committing any derived transcription; record the
  license and a link here for anything ingested.

## Status log

- 2026-07-23 — Transform layer + `source='horley'` switch + `compare_corpora.py` landed;
  `horley_map.json` seeded with **illustrative placeholders only** (not yet verified
  against any primary source). Next: acquire Horley 2021 and INSCRIBE Échancrée; replace
  placeholders with cited, verified entries.
