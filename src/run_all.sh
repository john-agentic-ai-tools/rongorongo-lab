#!/usr/bin/env bash
# Full reproduction: controls first (calibration), then rongorongo solvers.
#
# Transliteration is selectable:  RR_CORPUS=barthel (default) or RR_CORPUS=horley
# Horley results go to ../results_horley so a Barthel run and a Horley run can be
# compared side by side.  Run both, then read ../results/corpus_diff.txt.
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
echo "=== Corpus difference report (barthel vs horley) ==="
python3 compare_corpora.py
echo "Compare mappings across seeds in $RESULTS/ - agreement = identifiability."
echo "To contrast encodings: run once with RR_CORPUS=barthel and once with RR_CORPUS=horley."
