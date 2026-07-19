#!/usr/bin/env bash
# Full reproduction: controls first (calibration), then rongorongo solvers.
set -e
echo "=== Control 1: syllabic cipher (expect ~100% recovery) ==="
python3 control_syllabic.py 1
echo "=== Control 1b: syllabic cipher, varied train/test splits ==="
for sp in 7 19 23; do python3 control_syllabic.py 1 150000 $sp; done
echo "=== Control 2: logosyllabic cipher (expect partial recovery) ==="
python3 control_logosyllabic.py 1 80000 2
echo "=== Rongorongo: syllabic hypothesis, 7 seeds ==="
for s in 1 2 3 4 5 6 7; do python3 solver_syllabic.py $s 150000 ../results/syllabic_chain_$s.json; done
echo "=== Rongorongo: logosyllabic hypothesis, 3 seeds ==="
for s in 1 2 3; do python3 solver_logosyllabic.py $s 120000 ../results/ror_logo_$s.json; done
echo "=== Consensus report ==="
python3 consensus.py
echo "Compare mappings across seeds in ../results/ - agreement = identifiability."
