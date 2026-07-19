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
   tokens ≈ 120× the Shannon unicity distance): scores beat random
   mappings (z ≈ +10), but independent chains disagree on ~95% of sign
   assignments and decoded text contains real Rapa Nui words at chance
   rate. **Conclusion: rongorongo is not a plain syllabic substitution
   of chant-register Rapa Nui.** This is quantitative support for
   logosyllabic/mixed-system hypotheses (e.g., Davletshin 2022).
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
data/
  tablets_simple.json      Barthel transliteration, 13 tablets (via rongopy)
  rapanui_chants.txt       archaic Rapa Nui chant corpus (via rongopy)
results/                   chain outputs + consensus report
```

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
- Swap the transliteration: Horley (2021) tracings instead of Barthel;
  the sign-merging rules materially change the statistics.
- Add parallel-passage constraints (texts H/P/Q share content) as hard
  alignment constraints in the annealer.
- Replace the trigram LM with a small neural LM; rerun both controls
  first, because a stronger LM also strengthens degenerate attractors.

## Data attribution

Corpus files derive from Jonas Gregorio de Souza's
[rongopy](https://github.com/jgregoriods/rongopy) (GPL-3.0), building on
Barthel's (1958) transliteration. This repository is GPL-3.0 accordingly.
