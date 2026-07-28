#!/usr/bin/env bash
# Full reproduction: controls first (calibration), then rongorongo solvers.
#
# Transliteration is selectable:  RR_CORPUS=barthel (default) | ceipp | horley
#   barthel  Barthel 1958 via rongopy -- lossy: no allographic suffixes, no ligatures
#   ceipp    the C.E.I.P.P. extended-Barthel text; build it first with fetch_ceipp.py.
#            Reading policies: RR_CEIPP_VARIANTS=keep|strip, RR_CEIPP_GROUPS=atomic|fused
#   horley   horley_map.json applied over ceipp (or barthel, if ceipp is not built)
# Non-default corpora write to ../results_<corpus> so runs can be compared side by side.
# Run several, then read the ../results/corpus_diff_*.txt reports.
set -e
CORPUS="${RR_CORPUS:-barthel}"
if [ "$CORPUS" = "barthel" ]; then RESULTS=../results; else RESULTS="../results_${CORPUS}"; fi
mkdir -p "$RESULTS"
echo "### corpus = $CORPUS  ->  $RESULTS"

echo "=== Control 1: syllabic cipher (expect ~100% recovery) ==="
python3 control_syllabic.py 1
echo "=== Control 1b: syllabic cipher, varied train/test splits ==="
for sp in 7 19 23; do python3 control_syllabic.py 1 150000 $sp; done
echo "=== Control 2: logosyllabic cipher (expect partial recovery) ==="
python3 control_logosyllabic.py 1 80000 2
echo "=== Rongorongo: syllabic hypothesis, 7 seeds ==="
for s in 1 2 3 4 5 6 7; do python3 solver_syllabic.py $s 150000 "$RESULTS/syllabic_chain_$s.json" "$CORPUS"; done
echo "=== Rongorongo: logosyllabic hypothesis, 3 seeds ==="
for s in 1 2 3; do python3 solver_logosyllabic.py $s 120000 "$RESULTS/ror_logo_$s.json" "$CORPUS"; done
echo "=== Consensus report ==="
python3 consensus.py "$RESULTS" "$CORPUS"
echo "=== Corpus difference reports ==="
python3 compare_corpora.py barthel horley
if [ -f ../data/tablets_ceipp.json ]; then
  python3 compare_corpora.py barthel ceipp                  # what the rongopy re-encoding lost
  python3 compare_corpora.py ceipp horley                   # the map's effect, isolated
  python3 compare_corpora.py ceipp ceipp:variants=strip     # allograph-merging sensitivity
  python3 compare_corpora.py ceipp ceipp:groups=fused       # ligature-reading sensitivity
  python3 compare_echancree.py                              # item D vs the 3D ground truth
else
  echo "(skipping ceipp comparisons - run 'python3 fetch_ceipp.py' to build that corpus)"
fi
echo "Compare mappings across seeds in $RESULTS/ - agreement = identifiability."
echo "To contrast encodings: rerun with RR_CORPUS=ceipp and RR_CORPUS=horley."
