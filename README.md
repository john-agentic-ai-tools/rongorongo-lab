# rongorongo-lab

Computational tests of the syllabary and logosyllabary hypotheses for
rongorongo, the undeciphered script of Rapa Nui (Easter Island) — with
control experiments that let you know when the method is fooling you.

**This is not a decipherment claim.** It is the opposite: a falsifiable
pipeline whose headline result is a *negative* one, plus the calibration
experiments that make the negative result meaningful.

## Findings (summary)

1. **A trigram-LM annealing attack cracks a genuine 49-symbol syllabic
   substitution cipher of Rapa Nui** — 100% key recovery from ~3.4k
   tokens on the published train/test split, 98.5–100% of tokens across
   varied splits, LM trained on held-out text (`control_syllabic.py`).
   The frequency-rank warm start alone recovers only ~13–39% of tokens:
   the annealer, not the frequency prior, does the work.
2. **The identical attack fails on the rongorongo corpus** (~12k sign
   tokens): scores beat random mappings (z ≈ +10), but independent
   chains disagree on ~95% of sign assignments and decoded text
   contains real Rapa Nui words at chance rate. **Conclusion:
   rongorongo is not a plain syllabic substitution of chant-register
   Rapa Nui.** This is quantitative support for logosyllabic/mixed-system
   hypotheses (e.g., Davletshin 2022).
   *Caveat added 2026-07-25:* the "many times the unicity distance"
   argument that used to accompany this result is **encoding-dependent**
   and has been withdrawn as stated. It held only for the lossy rongopy
   corpus (17.7× by the unigram approximation). On a faithful
   transliteration the margin is 2.2×, and under a ligature-level
   reading 0.5× — below the unicity distance, where a unique key is not
   guaranteed to exist. The failure to recover a key stands; the claim
   that the corpus is far more than sufficient to force one does not.
   See [docs/HORLEY_FINDINGS.md](docs/HORLEY_FINDINGS.md).
3. **Naive maximum-likelihood logosyllabic decipherment is structurally
   broken by a compression bias**: total log-likelihood always prefers
   readings that emit fewer symbols, so true logograms score *worse*
   than wrong single-syllable readings (oracle test: all 8 planted
   logograms inverted). Scalar length-debiasing overcorrects into a
   different degenerate attractor. Word-segmentation scoring with a
   one-word-per-sign constraint partially fixes this
   (`control_logosyllabic.py`), but recovery on *known* logosyllabic
   ciphers remains partial — a calibrated warning for anyone attempting
   likelihood-based logosyllabic decipherment.
4. On the real corpus, only a small phonetic core is stable across
   independent runs (signs 003→i, 010→u, 002→ka, 730→tu). Treat these
   as weak statistical observations, not readings. (A prior claim that
   signs 001/006 "behave as vowels" was withdrawn after a control test
   showed V and CV syllables are not distributionally separable in
   Rapa Nui — vowel recovery does not significantly exceed
   frequency-matched CV recovery (permutation test p ≈ 0.14), and
   vowel→vowel confusions occur at the chance rate.)

## Layout

```
src/
  common.py                shared corpus loading + trigram LM
  solver_syllabic.py       bijective sign->syllable annealing on rongorongo
  solver_logosyllabic.py   two-phase (anneal + logogram sweep) solver
  control_syllabic.py      cracks a KNOWN syllabic cipher (calibration)
  control_logosyllabic.py  attempts a KNOWN logosyllabic cipher (calibration)
  fetch_ceipp.py           builds the C.E.I.P.P. corpus from rongorongo.org
  compare_corpora.py       difference/discoveries report for any two sources
  compare_echancree.py     item D vs the INSCRIBE 3D transcription (ground truth)
data/
  tablets_simple.json      Barthel transliteration, 13 tablets (via rongopy)
  tablets_ceipp.json       C.E.I.P.P. extended Barthel, all 26 objects (NOT committed;
                           run fetch_ceipp.py -- see README_ceipp.md)
  tablets_echancree.json   INSCRIBE 3D transcription of item D (Ferrara et al. 2022)
  horley_map.json          Horley (2021) sign-taxonomy transform over Barthel codes
  rapanui_chants.txt       archaic Rapa Nui chant corpus (via rongopy)
results/                   chain outputs + consensus report + corpus/tablet diffs
docs/
  HORLEY_ACQUISITION.md    acquisition roadmap + status log
  HORLEY_FINDINGS.md       differences + discoveries log, with attribution method
```

## Selecting the transliteration

The transliteration embeds contestable sign-merging decisions — which incisions are one
sign, which shapes are allographs, which are ligatures — and every statistic inherits them.
The pipeline reads the corpus through one seam, `common.load_tablets`, so the source is
switchable:

```bash
python solver_syllabic.py 1                    # barthel (default)
python fetch_ceipp.py                          # build the faithful corpus, once
RR_CORPUS=ceipp  python solver_syllabic.py 1   # C.E.I.P.P. extended Barthel
RR_CORPUS=horley python solver_syllabic.py 1   # Horley-informed corpus
python compare_corpora.py barthel ceipp        # -> results/corpus_diff_barthel_vs_ceipp.txt
python compare_echancree.py                    # -> results/echancree_vs_ceipp.txt
```

- **`barthel`** — `tablets_simple.json` (Barthel 1958 via rongopy). The historical default,
  unchanged. It is a **lossy** re-encoding: 239 signs, no allographic suffixes, no ligature
  structure, and 21% of its tokens are the collapsed codes `200`/`400`/`000`.
- **`ceipp`** — the same Barthel transliteration as published by the Commission Rongorongo,
  with the allographic suffixes and linking/stacking punctuation intact: **1584 signs**. Two
  policies, `RR_CEIPP_VARIANTS=keep|strip` and `RR_CEIPP_GROUPS=atomic|fused`, decide whether
  `074f` differs from `074` and whether `050.010.037` is one sign or three — which is the
  sign-merging question, made measurable. Not committed for licensing reasons; see
  [data/README_ceipp.md](data/README_ceipp.md).
- **`horley`** — a standalone `data/tablets_horley.json` if present, otherwise derived by
  applying `data/horley_map.json` over the best available base. **The shipped map is seeded
  with *illustrative placeholders*, not verified Horley decisions**, and they are keyed on
  bare rongopy-style codes so they barely fire over `ceipp` — see
  [data/README_horley.md](data/README_horley.md) and
  [docs/HORLEY_ACQUISITION.md](docs/HORLEY_ACQUISITION.md).

Every result JSON records which `corpus` and which `ceipp_policy` produced it.

## Reproduce

```bash
pip install numpy
cd src
python control_syllabic.py 1            # expect ~100% key recovery
python control_syllabic.py 1 150000 7   # same, different train/test split
python control_logosyllabic.py 1 80000 2  # expect partial recovery
python solver_syllabic.py 1             # rongorongo, syllabic hypothesis
python solver_logosyllabic.py 1         # rongorongo, logosyllabic hypothesis
```

Methodology notes: the annealer and the two-phase (anneal + logogram
sweep) code are shared (`common.py`), so the controls run literally the
same attack as the rongorongo solvers. The controls train the LM on a
60% split of the chants and encipher the held-out 40% (the third CLI
argument of `control_syllabic.py` varies the split); the rongorongo
solvers train on the full chant corpus, since there is no ground truth
to hold out for the tablets.

Run solvers with several seeds and diff the mappings; the fraction of
signs receiving identical values across chains is the identifiability
signal. Any decipherment claim from this method must survive:
(a) cross-chain agreement, (b) lexical match rate above a
random-bijection baseline, (c) held-out semantic anchors (e.g., the
Mamari lunar calendar, lines Ca6–Ca9).

## Ways to falsify / extend

- Swap the language model: an Old Rapa Nui reconstruction, or
  Proto-Eastern-Polynesian, in place of the 19th-century chant corpus.
- Swap the transliteration: the sign-merging rules materially change the
  statistics — measurably so. **Implemented** as `RR_CORPUS=ceipp|horley`
  (see "Selecting the transliteration" above). The C.E.I.P.P. corpus is
  acquired and the effect is large; the Horley map is still seeded with
  illustrative placeholders pending the book
  (`docs/HORLEY_ACQUISITION.md`).
- Re-establish the cross-chain noise floor on `ceipp`. The ~95%
  disagreement figure was measured on `barthel` only, and no
  cross-corpus comparison means anything until the faithful corpus has
  its own floor.
- Add parallel-passage constraints (texts H/P/Q share content) as hard
  alignment constraints in the annealer.
- Replace the trigram LM with a small neural LM; rerun both controls
  first, because a stronger LM also strengthens degenerate attractors.

## Data attribution

`tablets_simple.json` and `rapanui_chants.txt` derive from Jonas Gregorio
de Souza's [rongopy](https://github.com/jgregoriods/rongopy) (GPL-3.0),
building on Barthel's (1958) transliteration. This repository is GPL-3.0
accordingly.

Two further sources are used but **not redistributed here**:

- the numerical transliteration of the corpus by the Commission
  Rongorongo of the Cercle d'Études sur l'Île de Pâques et la Polynésie
  (C.E.I.P.P.), who hold Barthel's bequeathed materials, published at
  [rongorongo.org](http://kohaumotu.org/rongorongo_org/) under
  attribution + non-profit terms. `fetch_ceipp.py` retrieves it; the
  built file is gitignored;
- the Échancrée transcription of Lastilla, Ravanelli, Valério & Ferrara
  (2022), *DSH* 37(2): 497–518 (CC BY-NC). `tablets_echancree.json`
  stores the cited transcription only — no figures, drawings, or 3D
  models are reproduced.
