"""Shared corpus loading, Rapa Nui trigram LM, and optimizer for rongorongo-lab.

The annealer and the two-phase (syllabic anneal + logogram sweep) helpers
live here so that the control experiments and the rongorongo solvers run
*literally the same* attack code — the calibration claim depends on it.
"""
import json, math, re, os
import numpy as np
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
TAXOGRAMS = {'200', '400', '000'}   # 200/400: suspected taxograms (Guy 2006); 000: lacuna


def syllabify(word):
    """Rapa Nui (C)V syllables; 'g' = /ng/ in this corpus's orthography."""
    return re.findall(r'[ptkmnvrhg]?[aeiou]', word)


def load_language(path=None):
    """Return (syll_lines, verses) from the chant corpus, index-aligned:
    verses that syllabify to nothing are dropped from BOTH lists."""
    path = path or os.path.join(DATA, 'rapanui_chants.txt')
    text = open(path).read().lower()
    raw = [re.findall(r'[a-z]+', l) for l in text.split('\n') if l.strip()]
    syll_lines, verses = [], []
    for v in raw:
        s = [x for w in v for x in syllabify(w)]
        if s:
            syll_lines.append(s)
            verses.append(v)
    return syll_lines, verses


def build_lm(syll_lines, k=0.1, lam=(0.5, 0.35, 0.15)):
    """Interpolated add-k trigram LM. Returns (LOGP, vocab, sid, BOS, uni)."""
    vocab = sorted({s for l in syll_lines for s in l})
    S = len(vocab)
    sid = {s: i for i, s in enumerate(vocab)}
    BOS = S
    V = S + 1
    uni = np.zeros(V); bi = np.zeros((V, V)); tri = np.zeros((V, V, V))
    for l in syll_lines:
        ids = [BOS, BOS] + [sid[s] for s in l] + [BOS]
        for i in range(2, len(ids)):
            uni[ids[i]] += 1
            bi[ids[i-1], ids[i]] += 1
            tri[ids[i-2], ids[i-1], ids[i]] += 1
    p_uni = (uni + k) / (uni.sum() + k*V)
    p_bi = (bi + k) / (bi.sum(1, keepdims=True) + k*V)
    p_tri = (tri + k) / (tri.sum(2, keepdims=True) + k*V)
    P = lam[0]*p_tri + lam[1]*p_bi[None, :, :] + lam[2]*p_uni[None, None, :]
    return np.log(P), vocab, sid, BOS, uni


def load_tablets(path=None, min_len=3):
    """Return (lines, names): glyph sequences with taxograms removed."""
    path = path or os.path.join(DATA, 'tablets_simple.json')
    tablets = json.load(open(path))
    lines, names = [], []
    for tab, tlines in tablets.items():
        for lname, seq in tlines.items():
            gs = [g for g in seq.split('-') if g and g not in TAXOGRAMS]
            if len(gs) >= min_len:
                lines.append(gs)
                names.append(lname)
    return lines, names


def glyph_frequencies(lines):
    return Counter(g for l in lines for g in l)


def anneal(score_fn, m0, pool, iters, rng, t_hi=5.0, t_lo=0.01, scale=50.0):
    """Simulated annealing over swap moves on a mapping array.

    m0: initial mapping (numpy int array); pool: indices eligible for
    swapping. Geometric schedule t_hi -> t_lo; acceptance
    exp(delta / (T*scale)). NOTE: deltas are raw log-likelihood
    differences, which grow with corpus size, so `scale` sets an
    effective temperature that is corpus-size dependent — keep corpora
    of comparable size (controls ~3.4k tokens vs tablets ~12k) in mind
    when comparing runs. Returns (best_score, best_mapping).
    """
    m = np.array(m0, dtype=int)
    cur = score_fn(m)
    best, bm = cur, m.copy()
    n = len(pool)
    for it in range(iters):
        T = t_hi * (t_lo / t_hi) ** (it / iters)
        i, j = pool[rng.randrange(n)], pool[rng.randrange(n)]
        if i == j:
            continue
        m2 = m.copy()
        m2[i], m2[j] = m2[j], m2[i]
        s2 = score_fn(m2)
        if s2 > cur or rng.random() < math.exp((s2 - cur) / (T * scale)):
            m, cur = m2, s2
            if cur > best:
                best, bm = cur, m.copy()
    return best, bm


# ---------------------------------------------------------------------------
# Two-phase logosyllabic machinery, shared by solver_logosyllabic.py and
# control_logosyllabic.py. Symbol lines use ints in [0, n_sym) for mapped
# symbols and -1 for "unmapped" (emitted as a BOS break in the LM view,
# skipped in the segmentation view).
# ---------------------------------------------------------------------------

def build_word_lp(word_counts, sid, max_wlen):
    """Word-unigram log-probs keyed by syllable-id tuples (OOV syllables
    dropped; homographs keep the best log-prob)."""
    tot = sum(word_counts.values())
    wlp = {}
    for w, c in word_counts.items():
        ss = tuple(sid[s] for s in syllabify(w) if s in sid)
        if ss and len(ss) <= max_wlen:
            wlp[ss] = max(wlp.get(ss, -1e9), math.log(c / tot))
    return wlp


def make_seg_scorer(word_lp, unk_cost, max_wlen):
    """DP scorer: best segmentation of a syllable-id sequence into known
    words (unigram logprob) with a per-syllable UNK fallback."""
    def seg_score(tokens):
        n = len(tokens)
        best = [0.0] * (n + 1)
        for i in range(1, n + 1):
            b = best[i-1] + unk_cost
            for j in range(max(0, i - max_wlen), i):
                lp = word_lp.get(tuple(tokens[j:i]))
                if lp is not None and best[j] + lp > b:
                    b = best[j] + lp
            best[i] = b
        return best[n]
    return seg_score


def make_line_seg(lines, role, sylval, LEX, seg_score):
    """Segmentation score of one line under the current role/sylval state
    (closures over the mutable role/sylval lists)."""
    def line_seg(li):
        ids = []
        for g in lines[li]:
            if g >= 0:
                ids.extend(LEX[role[g]] if role[g] >= 0 else [sylval[g]])
        return seg_score(ids)
    return line_seg


def make_line_logp(lines, role, sylval, LEX, LOGP, BOS):
    """Trigram log-prob of one line; unmapped (-1) symbols emit BOS."""
    def line_logp(li):
        ids = [BOS, BOS]
        for g in lines[li]:
            if g < 0:
                ids.append(BOS)
            else:
                ids.extend(LEX[role[g]] if role[g] >= 0 else [sylval[g]])
        ids.append(BOS)
        a = np.array(ids)
        return LOGP[a[:-2], a[1:-1], a[2:]].sum()
    return line_logp


def build_flat(lines, role, LEX, n_sym, S):
    """Flat trigram slot arrays for Phase A. Slots 0..n_sym-1 are mutable
    syllabic symbols; n_sym..n_sym+S-1 constant syllable slots (used by
    logogram emissions); n_sym+S = BOS (also emitted for -1 symbols)."""
    CONST0 = n_sym
    BOSS = CONST0 + S

    def slots_for(g):
        if g < 0:
            return [BOSS]
        if role[g] >= 0:
            return [CONST0 + s for s in LEX[role[g]]]
        return [g]

    A, B, C = [], [], []
    for l in lines:
        ids = [BOSS, BOSS]
        for g in l:
            ids.extend(slots_for(g))
        ids.append(BOSS)
        for i in range(2, len(ids)):
            A.append(ids[i-2]); B.append(ids[i-1]); C.append(ids[i])
    return np.array(A), np.array(B), np.array(C)


def phase_A(lines, role, sylval, LEX, LOGP, BOS, S, iters, rng, pool=None):
    """Anneal syllable values of role==-1 symbols with logogram emissions
    held constant. Mutates sylval in place; returns best score."""
    n_sym = len(role)
    FA, FB, FC = build_flat(lines, role, LEX, n_sym, S)
    m = np.empty(n_sym + S + 1, dtype=int)
    m[:n_sym] = sylval
    m[n_sym:n_sym + S] = np.arange(S)
    m[n_sym + S] = BOS
    if pool is None:
        pool = [g for g in range(n_sym) if role[g] == -1]
    best, bm = anneal(lambda mm: LOGP[mm[FA], mm[FB], mm[FC]].sum(),
                      m, pool, iters, rng)
    for g in pool:
        sylval[g] = int(bm[g])
    return best


def phase_B(order, lines_with, line_seg, role, n_lex, logo_penalty, rng,
            line_sample=None):
    """Deterministic logogram sweep. For each symbol in `order`, try every
    lexicon word (and demotion back to syllabogram), keeping the role that
    maximizes the summed segmentation score of affected lines minus an MDL
    penalty for logogram roles; one-word-per-symbol uniqueness enforced via
    `claimed`. Mutates role in place; returns number of role changes."""
    changes = 0
    claimed = {r for r in role if r >= 0}
    for g in order:
        aff = lines_with[g]
        if line_sample is not None and len(aff) > line_sample:
            aff = rng.sample(aff, line_sample)
        base_role = role[g]
        base = sum(line_seg(li) for li in aff) - (logo_penalty if base_role >= 0 else 0.0)
        best_sc, best_role = base, base_role
        for w in range(-1, n_lex):
            if w == base_role or (w >= 0 and w in claimed):
                continue
            role[g] = w
            sc = sum(line_seg(li) for li in aff) - (logo_penalty if w >= 0 else 0.0)
            if sc > best_sc:
                best_sc, best_role = sc, w
        role[g] = best_role
        if best_role != base_role:
            changes += 1
            claimed.discard(base_role)
            if best_role >= 0:
                claimed.add(best_role)
    return changes
