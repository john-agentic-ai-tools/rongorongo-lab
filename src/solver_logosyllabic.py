"""
Two-phase logosyllabic solver for rongorongo (final architecture).

Phase A: pure syllabic simulated annealing (trigram LM objective).
Phase B: syllable key frozen; deterministic sweep converting glyphs to
logograms when a word-segmentation score (word unigrams + per-syllable
UNK cost) improves by more than an MDL penalty. Phases alternate.

Calibrated on control_logosyllabic.py: on a synthetic logosyllabic
cipher of real Rapa Nui (~3.3k tokens) this recovers a majority of the
syllable key and detects most logograms with some confusions/false
positives. Interpret rongorongo output accordingly: PROPOSALS, not
readings.

Usage: python solver_logosyllabic2.py SEED [ITERS] [OUT.json]
"""
import json, math, random, sys
import numpy as np
from collections import Counter
from common import load_language, build_lm, load_tablets, glyph_frequencies, syllabify

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 120000
OUT = sys.argv[3] if len(sys.argv) > 3 else f'ror_logo_{SEED}.json'
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
tot = sum(wc.values())
WORD_LP = {}
for w, c in wc.items():
    ss = tuple(sid[s] for s in syllabify(w) if s in sid)
    if ss and len(ss) <= MAX_WLEN:
        WORD_LP[ss] = max(WORD_LP.get(ss, -1e9), math.log(c / tot))

def seg_score(tokens):
    n = len(tokens)
    best = [0.0] * (n + 1)
    for i in range(1, n + 1):
        b = best[i-1] + UNK_COST
        for j in range(max(0, i - MAX_WLEN), i):
            lp = WORD_LP.get(tuple(tokens[j:i]))
            if lp is not None and best[j] + lp > b:
                b = best[j] + lp
        best[i] = b
    return best[n]

# tablets
lines, names = load_tablets()
gfreq = glyph_frequencies(lines)
mapped = [g for g, _ in gfreq.most_common(N_MAP)]
gidx = {g: i for i, g in enumerate(mapped)}
UNM = N_MAP
glines = [[gidx.get(g, UNM) for g in l] for l in lines]
lines_with = [set() for _ in range(N_MAP)]
for li, l in enumerate(glines):
    for g in l:
        if g < N_MAP:
            lines_with[g].add(li)
lines_with = [sorted(x) for x in lines_with]
n_tok = sum(len(l) for l in glines)

role = [-1] * N_MAP
sbf = list(np.argsort(-uni[:S]))
sylval = [sbf[i % S] for i in range(N_MAP)]

def emit(g):
    if g == UNM:
        return [BOS]
    return LEX[role[g]] if role[g] >= 0 else [sylval[g]]

def line_logp(li):
    ids = [BOS, BOS]
    for g in glines[li]:
        ids.extend(emit(g))
    ids.append(BOS)
    a = np.array(ids)
    return LOGP[a[:-2], a[1:-1], a[2:]].sum()

def line_seg(li):
    ids = []
    for g in glines[li]:
        if g != UNM:
            ids.extend(emit(g))
    return seg_score(ids)

cache = np.array([line_logp(li) for li in range(len(glines))])

def build_flat():
    """Flat trigram slot arrays. Slots 0..N_MAP-1 mutable (syllabic
    glyphs); N_MAP..N_MAP+S = constant syllable slots; last = BOS."""
    CONST0 = N_MAP
    def slots_for(g):
        if g == UNM:
            return [CONST0 + S]           # BOS constant
        if role[g] >= 0:
            return [CONST0 + s for s in LEX[role[g]]]
        return [g]
    A, B, C = [], [], []
    for l in glines:
        ids = [CONST0 + S] * 2
        for g in l:
            ids.extend(slots_for(g))
        ids.append(CONST0 + S)
        for i in range(2, len(ids)):
            A.append(ids[i-2]); B.append(ids[i-1]); C.append(ids[i])
    return np.array(A), np.array(B), np.array(C)

def phase_A(iters):
    global sylval
    FA, FB, FC = build_flat()
    m = np.empty(N_MAP + S + 1, dtype=int)
    for g in range(N_MAP):
        m[g] = sylval[g]
    for s in range(S):
        m[N_MAP + s] = s
    m[N_MAP + S] = BOS
    def sc(mm):
        return LOGP[mm[FA], mm[FB], mm[FC]].sum()
    cur = sc(m); best = cur; bm = m.copy()
    syls = [g for g in range(N_MAP) if role[g] == -1]
    for it in range(iters):
        T = 5.0 * (0.01/5.0) ** (it/iters)
        i, j = rng.choice(syls), rng.choice(syls)
        if i == j:
            continue
        m2 = m.copy()
        m2[i], m2[j] = m2[j], m2[i]
        s2 = sc(m2)
        if s2 > cur or rng.random() < math.exp((s2 - cur)/(T*50)):
            m, cur = m2, s2
            if cur > best:
                best, bm = cur, m.copy()
    for g in range(N_MAP):
        if role[g] == -1:
            sylval[g] = int(bm[g])
    for li in range(len(glines)):
        cache[li] = line_logp(li)
    print(f"  Phase A: logp/token = {cache.sum()/n_tok:.3f}", file=sys.stderr)

def phase_B():
    changes = 0
    claimed = {role[g] for g in range(N_MAP) if role[g] >= 0}
    order = list(range(LOGO_MIN_RANK, N_MAP))
    rng.shuffle(order)
    for g in order:
        aff = lines_with[g]
        if len(aff) > LOGO_LINE_SAMPLE:
            aff = rng.sample(aff, LOGO_LINE_SAMPLE)
        base_role = role[g]
        base = sum(line_seg(li) for li in aff) - (LOGO_PENALTY if base_role >= 0 else 0)
        best_sc, best_role = base, base_role
        for w in range(-1, L):
            if w == base_role:
                continue
            if w >= 0 and w in claimed and w != base_role:
                continue
            role[g] = w
            sc = sum(line_seg(li) for li in aff) - (LOGO_PENALTY if w >= 0 else 0)
            if sc > best_sc:
                best_sc, best_role = sc, w
        role[g] = best_role
        if best_role != base_role:
            changes += 1
            claimed.discard(base_role)
            if best_role >= 0:
                claimed.add(best_role)
            for li in lines_with[g]:
                cache[li] = line_logp(li)
    print(f"  Phase B: {changes} role changes", file=sys.stderr)
    return changes

for r in range(ROUNDS):
    print(f"Round {r+1}", file=sys.stderr)
    phase_A(ITERS if r == 0 else ITERS // 4)
    phase_B()

mapping = {}
for g in mapped:
    i = gidx[g]
    if role[i] >= 0:
        mapping[g] = {'type': 'logo', 'value': LEXW[role[i]]}
    else:
        mapping[g] = {'type': 'syll', 'value': vocab[sylval[i]]}
json.dump({'seed': SEED, 'iters': ITERS, 'n_glyph_tokens': n_tok,
           'logp_per_token': float(cache.sum()/n_tok),
           'n_logograms': sum(1 for x in role if x >= 0),
           'mapping': mapping}, open(OUT, 'w'), indent=1)
print(f"seed {SEED}: logp/token={cache.sum()/n_tok:.3f}, "
      f"logograms={sum(1 for x in role if x >= 0)}")
