"""
Control experiment: can a two-phase solver crack a KNOWN logosyllabic
cipher of real Rapa Nui text?

Phase A: pure syllabic simulated annealing (all symbols treated as
syllabograms), long schedule.
Phase B: syllable key frozen; deterministic sweep over symbols x lexicon
words, converting a symbol to a logogram whenever the likelihood gain
exceeds an MDL penalty.

Usage: python control_logosyllabic.py SEED [ITERS] [MIN_LOGO_SYL]
"""
import math, random, sys
import numpy as np
from collections import Counter
from common import load_language, build_lm, syllabify

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 150000
MIN_LOGO_SYL = int(sys.argv[3]) if len(sys.argv) > 3 else 2
K_LOGO = 8
LOGO_PENALTY = 8.0
UNK_COST = -6.0        # per-syllable cost of unparseable material
MAX_WLEN = 6
SWEEPS = 3

rng = random.Random(SEED)

syll_lines, verses = load_language()
idx = list(range(len(verses)))
random.Random(42).shuffle(idx)
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
cipher_lines = []
for v in test_v:
    line = []
    for w in v:
        if w in logo_sym:
            line.append(logo_sym[w])
        else:
            line.extend(secret[sid[s]] for s in syllabify(w) if s in sid)
    if len(line) >= 3:
        cipher_lines.append(line)
N = S + 1 + K_LOGO
n_tok = sum(len(l) for l in cipher_lines)
print(f"cipher: {len(cipher_lines)} lines, {n_tok} tokens; hidden logograms: {logo_words}")

twf = Counter(w for v in train_v for w in v)
cand = [w for w, _ in twf.most_common(150) if len(syllabify(w)) >= 2]
LEX = [[sid[s] for s in syllabify(w)] for w in cand if all(s in sid for s in syllabify(w))]
LEXW = [w for w in cand if all(s in sid for s in syllabify(w))]
L = len(LEX)
print(f"lexicon {L} words; {sum(1 for w in logo_words if w in LEXW)}/{K_LOGO} true words in lexicon")

# ---- word-level segmentation scorer (train-half word unigrams) ----
import math as _m
_wc = Counter(w for v in train_v for w in v)
_tot = sum(_wc.values())
WORD_LP = {}
for w, c in _wc.items():
    ss = tuple(sid[s] for s in syllabify(w) if s in sid)
    if ss and len(ss) <= MAX_WLEN:
        WORD_LP[ss] = max(WORD_LP.get(ss, -1e9), _m.log(c/_tot))

def seg_score(tokens):
    """DP: best segmentation of syllable-id sequence into known words
    (unigram logprob) with per-syllable UNK fallback."""
    n = len(tokens)
    best = [0.0]*(n+1)
    for i in range(1, n+1):
        b = best[i-1] + UNK_COST
        lo = max(0, i-MAX_WLEN)
        for j in range(lo, i-1+1):
            w = tuple(tokens[j:i])
            lp = WORD_LP.get(w)
            if lp is not None:
                v = best[j] + lp
                if v > b: b = v
        best[i] = b
    return best[n]

def line_seg(li):
    ids = []
    for g in cipher_lines[li]: ids.extend(emit(g))
    return seg_score(ids)

cfreq = np.zeros(N)
for l in cipher_lines:
    for x in l: cfreq[x] += 1
lines_with = [set() for _ in range(N)]
for li, l in enumerate(cipher_lines):
    for g in l: lines_with[g].add(li)
lines_with = [sorted(x) for x in lines_with]
present = [c for c in range(N) if cfreq[c] > 0]

# ---- Phase A: pure syllabic annealing over all N symbols ----
role = [-1] * N
sylval = [0] * N
order_c = list(np.argsort(-cfreq))
sbf = list(np.argsort(-uni[:S]))
for rank, c in enumerate(order_c):
    sylval[c] = sbf[rank % S]

def emit(g): return LEX[role[g]] if role[g] >= 0 else [sylval[g]]

def line_logp(li):
    ids = [BOS, BOS]
    for g in cipher_lines[li]: ids.extend(emit(g))
    ids.append(BOS)
    a = np.array(ids)
    return LOGP[a[:-2], a[1:-1], a[2:]].sum()

def line_score(li):
    """Length-debiased: logp + BETA per emitted token (neutralizes
    the compression bias that otherwise makes shorter readings win)."""
    ids = [BOS, BOS]
    for g in cipher_lines[li]: ids.extend(emit(g))
    ids.append(BOS)
    a = np.array(ids)
    return LOGP[a[:-2], a[1:-1], a[2:]].sum() + BETA * (len(a) - 3)

cache = np.array([line_logp(li) for li in range(len(cipher_lines))])

def phase_A(iters):
    global cache, sylval
    cur = cache.sum(); best = cur
    best_syl = list(sylval)
    syl_syms = [c for c in present if role[c] == -1]
    for it in range(iters):
        T = 5.0 * (0.01/5.0) ** (it/iters)
        i, j = rng.choice(syl_syms), rng.choice(syl_syms)
        if i == j: continue
        sylval[i], sylval[j] = sylval[j], sylval[i]
        aff = sorted(set(lines_with[i]) | set(lines_with[j]))
        old = cache[aff].copy()
        for li in aff: cache[li] = line_logp(li)
        new = cache.sum()
        if new > cur or rng.random() < math.exp((new - cur)/(T*50)):
            cur = new
            if cur > best: best, best_syl = cur, list(sylval)
        else:
            cache[aff] = old
            sylval[i], sylval[j] = sylval[j], sylval[i]
    sylval[:] = best_syl
    for li in range(len(cipher_lines)): cache[li] = line_logp(li)
    print(f"  Phase A: logp/token = {cache.sum()/n_tok:.3f}")

def phase_B():
    changes_total = 0
    eligible = [c for c in present if cfreq[c] >= 3]
    for g in eligible:
        base_role = role[g]
        aff = lines_with[g]
        base_sc = sum(line_seg(li) for li in aff) - (LOGO_PENALTY if base_role >= 0 else 0)
        best_sc, best_role = base_sc, base_role
        for w in range(-1, L):
            if w == base_role: continue
            role[g] = w
            sc = sum(line_seg(li) for li in aff) - (LOGO_PENALTY if w >= 0 else 0)
            if sc > best_sc: best_sc, best_role = sc, w
        role[g] = best_role
        if best_role != base_role:
            changes_total += 1
            for li in aff: cache[li] = line_logp(li)
    print(f"  Phase B: {changes_total} role changes")
    return changes_total

for rnd_i in range(2):
    print(f"Round {rnd_i+1}:")
    phase_A(ITERS if rnd_i == 0 else ITERS//4)
    if phase_B() == 0 and rnd_i > 0:
        break

# ---- evaluation ----
inv = {secret[p]: p for p in range(S)}
syl_ok = tok_ok = tok_tot = syl_tot = 0
for c in range(S):
    if cfreq[c] == 0: continue
    syl_tot += 1; tok_tot += cfreq[c]
    if role[c] == -1 and sylval[c] == inv.get(c, -99):
        syl_ok += 1; tok_ok += cfreq[c]
logo_ok = sum(1 for w, s in logo_sym.items() if role[s] >= 0 and LEXW[role[s]] == w)
logo_det = sum(1 for w, s in logo_sym.items() if role[s] >= 0)
false_logo = sum(1 for c in range(S) if cfreq[c] > 0 and role[c] >= 0)
print(f"RESULT seed={SEED}: syllable key {syl_ok}/{syl_tot} ({100*tok_ok/tok_tot:.1f}% of tokens)")
print(f"RESULT logograms: {logo_ok}/{K_LOGO} exact word; {logo_det}/{K_LOGO} detected; "
      f"{false_logo} false-positive logograms among true syllable symbols")
print("guesses:", {w: (LEXW[role[s]] if role[s] >= 0 else 'SYLL:'+vocab[sylval[s]])
                   for w, s in logo_sym.items()})
