"""
Control experiment: can a two-phase solver crack a KNOWN logosyllabic
cipher of real Rapa Nui text?

Phase A: pure syllabic simulated annealing (all symbols treated as
syllabograms), long schedule.
Phase B: syllable key frozen; deterministic sweep over symbols x lexicon
words, converting a symbol to a logogram whenever the segmentation-score
gain exceeds an MDL penalty.

Both phases are the shared implementations in common.py, run with the
SAME constraints as solver_logosyllabic.py (top-LOGO_MIN_RANK symbols
ineligible as logograms, one-word-per-symbol uniqueness, line sampling,
shuffled sweep order, 2 rounds) — so this control calibrates exactly
the attack applied to the tablets.

SPLIT_SEED controls the train/test partition (default 42, the published
split); vary it to test robustness to the data partition.

Usage: python control_logosyllabic.py SEED [ITERS] [MIN_LOGO_SYL] [SPLIT_SEED]
"""
import random, sys
import numpy as np
from collections import Counter
from common import (load_language, build_lm, syllabify, build_word_lp,
                    make_seg_scorer, make_line_seg, make_line_logp,
                    phase_A, phase_B)

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 150000
MIN_LOGO_SYL = int(sys.argv[3]) if len(sys.argv) > 3 else 2
SPLIT_SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 42
K_LOGO = 8
LOGO_PENALTY = 8.0
UNK_COST = -6.0        # per-syllable cost of unparseable material
MAX_WLEN = 6
LOGO_MIN_RANK = 8      # same rank rule as solver_logosyllabic.py
LOGO_LINE_SAMPLE = 12  # same line sampling as solver_logosyllabic.py
ROUNDS = 2

rng = random.Random(SEED)

syll_lines, verses = load_language()
idx = list(range(len(verses)))
random.Random(SPLIT_SEED).shuffle(idx)
split = int(len(idx) * 0.6)
train_v = [verses[i] for i in idx[:split]]
test_v = [verses[i] for i in idx[split:]]
train_s = [[x for w in v for x in syllabify(w)] for v in train_v]
train_s = [l for l in train_s if l]

LOGP, vocab, sid, BOS, uni = build_lm(train_s)
S = len(vocab)

# ---- synthetic logosyllabic cipher ----
wfreq = Counter(w for v in test_v for w in v if len(syllabify(w)) >= MIN_LOGO_SYL)
logo_words = [w for w, _ in wfreq.most_common(K_LOGO)]
logo_sym = {w: S + 1 + i for i, w in enumerate(logo_words)}
secret = list(range(S)); rng.shuffle(secret)
cipher_lines, oov = [], 0
for v in test_v:
    line = []
    for w in v:
        if w in logo_sym:
            line.append(logo_sym[w])
        else:
            for s in syllabify(w):
                if s in sid:
                    line.append(secret[sid[s]])
                else:
                    oov += 1
    if len(line) >= 3:
        cipher_lines.append(line)
N = S + 1 + K_LOGO
n_tok = sum(len(l) for l in cipher_lines)
print(f"cipher: {len(cipher_lines)} lines, {n_tok} tokens "
      f"({oov} OOV test tokens dropped); hidden logograms: {logo_words}")

# ---- logogram candidate lexicon (train half; same size rule as solver) ----
twf = Counter(w for v in train_v for w in v)
cand = [w for w, _ in twf.most_common(100) if len(syllabify(w)) >= 2]
LEXW = [w for w in cand if all(s in sid for s in syllabify(w))]
LEX = [[sid[s] for s in syllabify(w)] for w in LEXW]
L = len(LEX)
print(f"lexicon {L} words; {sum(1 for w in logo_words if w in LEXW)}/{K_LOGO} "
      f"true words in lexicon")

# ---- word-level segmentation scorer (train-half word unigrams) ----
WORD_LP = build_word_lp(twf, sid, MAX_WLEN)
seg_score = make_seg_scorer(WORD_LP, UNK_COST, MAX_WLEN)

cfreq = np.zeros(N)
for l in cipher_lines:
    for x in l:
        cfreq[x] += 1
lines_with = [set() for _ in range(N)]
for li, l in enumerate(cipher_lines):
    for g in l:
        lines_with[g].add(li)
lines_with = [sorted(x) for x in lines_with]
present = [c for c in range(N) if cfreq[c] > 0]

role = [-1] * N
order_c = list(np.argsort(-cfreq))
sbf = list(np.argsort(-uni[:S]))
sylval = [0] * N
for rank, c in enumerate(order_c):
    sylval[c] = sbf[rank % S]

# Phase B eligibility: same rank rule as the solver — the LOGO_MIN_RANK
# most frequent symbols are assumed syllabograms
eligible = [c for rank, c in enumerate(order_c)
            if rank >= LOGO_MIN_RANK and cfreq[c] > 0]
n_hidden_eligible = sum(1 for s in logo_sym.values() if s in eligible)
print(f"{n_hidden_eligible}/{K_LOGO} hidden logogram symbols rank >= "
      f"{LOGO_MIN_RANK} (eligible for detection)")

line_seg = make_line_seg(cipher_lines, role, sylval, LEX, seg_score)
line_logp = make_line_logp(cipher_lines, role, sylval, LEX, LOGP, BOS)

def total_logp():
    return sum(line_logp(li) for li in range(len(cipher_lines)))

for r in range(ROUNDS):
    print(f"Round {r+1}:")
    phase_A(cipher_lines, role, sylval, LEX, LOGP, BOS, S,
            ITERS if r == 0 else ITERS // 4, rng,
            pool=[c for c in present if role[c] == -1])
    print(f"  Phase A: logp/token = {total_logp()/n_tok:.3f}")
    order = list(eligible)
    rng.shuffle(order)
    changes = phase_B(order, lines_with, line_seg, role, L, LOGO_PENALTY, rng,
                      line_sample=LOGO_LINE_SAMPLE)
    print(f"  Phase B: {changes} role changes")

# ---- evaluation ----
inv = {secret[p]: p for p in range(S)}
syl_ok = tok_ok = tok_tot = syl_tot = 0
for c in range(S):
    if cfreq[c] == 0:
        continue
    syl_tot += 1; tok_tot += cfreq[c]
    if role[c] == -1 and sylval[c] == inv.get(c, -99):
        syl_ok += 1; tok_ok += cfreq[c]
logo_ok = sum(1 for w, s in logo_sym.items() if role[s] >= 0 and LEXW[role[s]] == w)
logo_det = sum(1 for w, s in logo_sym.items() if role[s] >= 0)
false_logo = sum(1 for c in range(S) if cfreq[c] > 0 and role[c] >= 0)
print(f"RESULT seed={SEED} split={SPLIT_SEED}: syllable key {syl_ok}/{syl_tot} "
      f"({100*tok_ok/tok_tot:.1f}% of tokens)")
print(f"RESULT logograms: {logo_ok}/{K_LOGO} exact word; {logo_det}/{K_LOGO} detected "
      f"({n_hidden_eligible}/{K_LOGO} eligible); "
      f"{false_logo} false-positive logograms among true syllable symbols")
print("guesses:", {w: (LEXW[role[s]] if role[s] >= 0 else 'SYLL:' + vocab[sylval[s]])
                   for w, s in logo_sym.items()})
