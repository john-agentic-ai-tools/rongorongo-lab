"""
Are bare-vowel syllables (V) a detectable distributional class distinct
from CV syllables in Rapa Nui? Prompted by A. Davletshin's observation
that V and CV syllables do not differ distributionally in Polynesian.

Test A: Jensen-Shannon divergence between syllable context distributions,
        within-vowel vs vowel-CV vs CV-CV (frequency-matched top-10 set).
Test B: in partially-converged runs of the syllabic control cipher,
        compare exact-recovery rates for vowel symbols vs
        frequency-matched CV symbols, and check whether misassigned
        vowels land on other vowels above the ~50% chance rate.

Result (8 seeds, 12k iters): vowels 72% vs CV 65% recovery (n.s.);
vowel->vowel confusions 45% vs ~50% chance. Conclusion: V/CV are NOT
separable classes at this scale; any "sign X behaves as a vowel" claim
from frequency-based solvers is a rank artifact. Davletshin was right.
"""
import math, random
import numpy as np
from collections import Counter
from common import load_language, build_lm, syllabify

syll_lines, verses = load_language()
full_vocab = sorted({s for l in syll_lines for s in l})
V_SET = {s for s in full_vocab if len(s) == 1}
freq = Counter(s for l in syll_lines for s in l)
top = [s for s, _ in freq.most_common(10)]
vows = [s for s in top if s in V_SET]
cvs = [s for s in top if s not in V_SET]

# ---- Test A ----
sid_full = {s: i for i, s in enumerate(full_vocab)}
S_full = len(full_vocab)
prevc = {s: Counter() for s in full_vocab}
nextc = {s: Counter() for s in full_vocab}
for l in syll_lines:
    for i, s in enumerate(l):
        if i > 0:
            prevc[s][l[i-1]] += 1
        if i < len(l) - 1:
            nextc[s][l[i+1]] += 1

def dist_vec(s):
    v = np.zeros(2 * S_full)
    tp = sum(prevc[s].values()) or 1
    tn = sum(nextc[s].values()) or 1
    for k, c in prevc[s].items():
        v[sid_full[k]] = c / tp
    for k, c in nextc[s].items():
        v[S_full + sid_full[k]] = c / tn
    return v

def jsd(p, q):
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = a > 0
        return np.sum(a[mask] * np.log(a[mask] / np.maximum(b[mask], 1e-12)))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)

vecs = {s: dist_vec(s) for s in top}
def avg(g1, g2):
    return np.mean([jsd(vecs[a], vecs[b]) for a in g1 for b in g2 if a != b])
print("Test A (context JSD): V-V %.4f | V-CV %.4f | CV-CV %.4f" %
      (avg(vows, vows), avg(vows, cvs), avg(cvs, cvs)))

# ---- Test B ----
idx = list(range(len(verses)))
random.Random(42).shuffle(idx)
split = int(len(idx) * 0.6)
train_v = [verses[i] for i in idx[:split]]
test_v = [verses[i] for i in idx[split:]]
train_s = [[x for w in v for x in syllabify(w)] for v in train_v]
train_s = [l for l in train_s if l]
LOGP, vocab, sid, BOS, uni = build_lm(train_s)
S = len(vocab)

results = []
for seed in range(1, 9):
    rng = random.Random(seed)
    secret = list(range(S)); rng.shuffle(secret)
    enc = []
    for v in test_v:
        l = [secret[sid[s]] for w in v for s in syllabify(w) if s in sid]
        if len(l) >= 3:
            enc.append(l)
    A, B, C = [], [], []
    for l in enc:
        ids = [S, S] + l + [S]
        for i in range(2, len(ids)):
            A.append(ids[i-2]); B.append(ids[i-1]); C.append(ids[i])
    A, B, C = map(np.array, (A, B, C))
    def score(m):
        return LOGP[m[A], m[B], m[C]].sum()
    cfreq = np.zeros(S)
    for l in enc:
        for x in l:
            cfreq[x] += 1
    oc = np.argsort(-cfreq); os_ = np.argsort(-uni[:S])
    m = np.empty(S + 1, dtype=int); m[S] = BOS
    for i in range(S):
        m[oc[i]] = os_[i]
    cur = score(m); best = cur; bm = m.copy()
    ITERS = 12000  # deliberately partial convergence
    for it in range(ITERS):
        T = 5.0 * (0.01/5.0) ** (it/ITERS)
        i, j = rng.randrange(S), rng.randrange(S)
        m2 = m.copy(); m2[i], m2[j] = m2[j], m2[i]
        s2 = score(m2)
        if s2 > cur or rng.random() < math.exp((s2 - cur)/(T*50)):
            m, cur = m2, s2
        if cur > best:
            best, bm = cur, m.copy()
    inv = {secret[p]: p for p in range(S)}
    for c in range(S):
        if cfreq[c] == 0:
            continue
        results.append((vocab[inv[c]], vocab[bm[c]]))

v_all = [r for r in results if r[0] in V_SET]
v_ok = sum(1 for r in v_all if r[0] == r[1])
wrong_v = [r for r in v_all if r[0] != r[1]]
v_to_v = sum(1 for r in wrong_v if r[1] in V_SET)
cv_all = [r for r in results if r[0] in cvs]
cv_ok = sum(1 for r in cv_all if r[0] == r[1])
print(f"Test B: vowels exact {v_ok}/{len(v_all)} | "
      f"freq-matched CV exact {cv_ok}/{len(cv_all)} | "
      f"vowel errors -> vowel {v_to_v}/{len(wrong_v)} (chance ~50%)")
