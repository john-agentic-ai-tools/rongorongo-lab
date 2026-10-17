"""
Pure syllabic solver for rongorongo (bijective substitution hypothesis).

Simulated annealing over injective glyph->syllable mappings for the top
49 glyphs (taxograms 200/400 removed), scored by a trigram LM trained on
archaic Rapa Nui chants. Run multiple seeds and compare mappings:
cross-chain agreement measures identifiability.

Note: unlike the controls (which hold out 40% of the chants), the LM
here is trained on the full chant corpus — there is no ground truth to
hold out for the tablets.

Usage: python solver_syllabic.py SEED [ITERS] [OUT.json]
"""
import json, random, sys
import numpy as np
from common import (load_language, build_lm, load_tablets, glyph_frequencies,
                    anneal, resolve_source, corpus_stamp)

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 0
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 150000
OUT = sys.argv[3] if len(sys.argv) > 3 else f'syllabic_chain_{SEED}.json'
CORPUS = resolve_source(sys.argv[4] if len(sys.argv) > 4 else None)  # or env RR_CORPUS

rng = random.Random(SEED)

syll_lines, _ = load_language()
LOGP, vocab, sid, BOS, uni = build_lm(syll_lines)
S = len(vocab)

lines, names = load_tablets(source=CORPUS)
gfreq = glyph_frequencies(lines)
N_MAP = min(S, 49)
mapped = [g for g, _ in gfreq.most_common(N_MAP)]
gidx = {g: i for i, g in enumerate(mapped)}
UNM = N_MAP

A, B, C = [], [], []
for l in lines:
    ids = [UNM, UNM] + [gidx.get(g, UNM) for g in l] + [UNM]
    for i in range(2, len(ids)):
        A.append(ids[i-2]); B.append(ids[i-1]); C.append(ids[i])
A, B, C = map(np.array, (A, B, C))

def score(m):
    return LOGP[m[A], m[B], m[C]].sum()

sbf = list(np.argsort(-uni[:S]))
m = np.empty(N_MAP + 1, dtype=int)
m[UNM] = BOS
for i in range(N_MAP):
    m[i] = sbf[i % S]

best, bm = anneal(score, m, list(range(N_MAP)), ITERS, rng)

mapping = {g: vocab[bm[gidx[g]]] for g in mapped}
json.dump({'seed': SEED, **corpus_stamp(CORPUS), 'score': float(best),
           'n_positions': int(len(A)), 'mapping': mapping}, open(OUT, 'w'), indent=1)
print(f"[{CORPUS}] seed {SEED}: logp/sign = {best/len(A):.3f}")
