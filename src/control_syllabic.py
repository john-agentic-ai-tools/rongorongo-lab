"""
Control experiment 1: pure syllabic cipher recovery.

Enciphers the held-out 40% of the Rapa Nui chant corpus with a secret
random substitution over its 49 syllables, then attempts recovery via
simulated annealing against a trigram LM trained on the other 60%.

Expected result (calibrated): 100% key recovery from ~3.4k tokens.
This establishes that IF rongorongo were a plain syllabic substitution
of chant-register Rapa Nui, the same pipeline would crack it.

Usage: python control_syllabic.py SEED [ITERS]
"""
import math, random, sys
import numpy as np
from common import load_language, build_lm, syllabify

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 150000

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

secret = list(range(S))
rng.shuffle(secret)
enc = []
for v in test_v:
    l = [secret[sid[s]] for w in v for s in syllabify(w) if s in sid]
    if len(l) >= 3:
        enc.append(l)
n_tok = sum(len(l) for l in enc)
print(f"cipher: {len(enc)} lines, {n_tok} tokens")

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
order_c = np.argsort(-cfreq)
order_s = np.argsort(-uni[:S])
m = np.empty(S + 1, dtype=int)
m[S] = BOS
for i in range(S):
    m[order_c[i]] = order_s[i]

cur = score(m); best = cur; bm = m.copy()
for it in range(ITERS):
    T = 5.0 * (0.01/5.0) ** (it/ITERS)
    i, j = rng.randrange(S), rng.randrange(S)
    m2 = m.copy(); m2[i], m2[j] = m2[j], m2[i]
    s2 = score(m2)
    if s2 > cur or rng.random() < math.exp((s2 - cur)/(T*50)):
        m, cur = m2, s2
        if cur > best:
            best, bm = cur, m.copy()

correct = sum(1 for c in range(S) if bm[c] == secret.index(c))
wcorrect = sum(cfreq[c] for c in range(S) if bm[c] == secret.index(c)) / cfreq.sum()
print(f"RESULT seed={SEED}: key recovered {correct}/{S} symbols "
      f"({100*wcorrect:.1f}% of tokens); logp/token={best/len(A):.3f}")
