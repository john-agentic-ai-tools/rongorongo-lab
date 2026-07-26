"""
Two-phase logosyllabic solver for rongorongo (final architecture).

Phase A: pure syllabic simulated annealing (trigram LM objective).
Phase B: syllable key frozen; deterministic sweep converting glyphs to
logograms when a word-segmentation score (word unigrams + per-syllable
UNK cost) improves by more than an MDL penalty. Phases alternate.

Both phases are the shared implementations in common.py — the same code
calibrated on control_logosyllabic.py: on a synthetic logosyllabic
cipher of real Rapa Nui (~3.3k tokens) it recovers a majority of the
syllable key and detects most logograms with some confusions/false
positives. Interpret rongorongo output accordingly: PROPOSALS, not
readings.

Note: unlike the control (which holds out 40% of the chants), the LM
and lexicon here use the full chant corpus — there is no ground truth
to hold out for the tablets.

Usage: python solver_logosyllabic.py SEED [ITERS] [OUT.json]
"""
import json, random, sys
import numpy as np
from collections import Counter
from common import (load_language, build_lm, load_tablets, glyph_frequencies,
                    syllabify, build_word_lp, make_seg_scorer, make_line_seg,
                    make_line_logp, phase_A, phase_B, resolve_source)

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 120000
OUT = sys.argv[3] if len(sys.argv) > 3 else f'ror_logo_{SEED}.json'
CORPUS = resolve_source(sys.argv[4] if len(sys.argv) > 4 else None)  # or env RR_CORPUS
N_MAP = 49
LOGO_PENALTY = 8.0
UNK_COST = -6.0
MAX_WLEN = 6
LOGO_MIN_RANK = 8      # top-8 glyphs not eligible as logograms
LOGO_LINE_SAMPLE = 12  # max lines evaluated per glyph in Phase B
ROUNDS = 2

rng = random.Random(SEED)

syll_lines, verses = load_language()
LOGP, vocab, sid, BOS, uni = build_lm(syll_lines)
S = len(vocab)

# logogram candidate lexicon: frequent words + lunar night names
wc = Counter(w for v in verses for w in v)
night = ['kokore', 'maharu', 'ohua', 'otua', 'maure', 'mauri', 'omotohi',
         'orongo', 'tireo', 'hiro', 'oata', 'rakau', 'mahina', 'tapume', 'matua']
cand = [w for w, _ in wc.most_common(100) if len(syllabify(w)) >= 2]
for w in night:
    if w not in cand:
        cand.append(w)
LEXW = [w for w in cand if all(s in sid for s in syllabify(w))]
LEX = [[sid[s] for s in syllabify(w)] for w in LEXW]
L = len(LEX)

# word segmentation model
WORD_LP = build_word_lp(wc, sid, MAX_WLEN)
seg_score = make_seg_scorer(WORD_LP, UNK_COST, MAX_WLEN)

# tablets: mapped glyphs -> [0, N_MAP), everything else -> -1 (unmapped)
lines, names = load_tablets(source=CORPUS)
gfreq = glyph_frequencies(lines)
mapped = [g for g, _ in gfreq.most_common(N_MAP)]
gidx = {g: i for i, g in enumerate(mapped)}
glines = [[gidx.get(g, -1) for g in l] for l in lines]
lines_with = [set() for _ in range(N_MAP)]
for li, l in enumerate(glines):
    for g in l:
        if g >= 0:
            lines_with[g].add(li)
lines_with = [sorted(x) for x in lines_with]
n_tok = sum(len(l) for l in glines)

role = [-1] * N_MAP
sbf = list(np.argsort(-uni[:S]))
sylval = [sbf[i % S] for i in range(N_MAP)]

line_seg = make_line_seg(glines, role, sylval, LEX, seg_score)
line_logp = make_line_logp(glines, role, sylval, LEX, LOGP, BOS)

def total_logp():
    return sum(line_logp(li) for li in range(len(glines)))

for r in range(ROUNDS):
    print(f"Round {r+1}", file=sys.stderr)
    phase_A(glines, role, sylval, LEX, LOGP, BOS, S,
            ITERS if r == 0 else ITERS // 4, rng)
    print(f"  Phase A: logp/token = {total_logp()/n_tok:.3f}", file=sys.stderr)
    order = list(range(LOGO_MIN_RANK, N_MAP))
    rng.shuffle(order)
    changes = phase_B(order, lines_with, line_seg, role, L, LOGO_PENALTY, rng,
                      line_sample=LOGO_LINE_SAMPLE)
    print(f"  Phase B: {changes} role changes", file=sys.stderr)

final_logp = total_logp()
mapping = {}
for g in mapped:
    i = gidx[g]
    if role[i] >= 0:
        mapping[g] = {'type': 'logo', 'value': LEXW[role[i]]}
    else:
        mapping[g] = {'type': 'syll', 'value': vocab[sylval[i]]}
json.dump({'seed': SEED, 'corpus': CORPUS, 'iters': ITERS, 'n_glyph_tokens': n_tok,
           'logp_per_token': float(final_logp / n_tok),
           'n_logograms': sum(1 for x in role if x >= 0),
           'mapping': mapping}, open(OUT, 'w'), indent=1)
print(f"[{CORPUS}] seed {SEED}: logp/token={final_logp/n_tok:.3f}, "
      f"logograms={sum(1 for x in role if x >= 0)}")
