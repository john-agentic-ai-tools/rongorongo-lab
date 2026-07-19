"""
Control experiment 1: pure syllabic cipher recovery.

Enciphers the held-out 40% of the Rapa Nui chant corpus with a secret
random substitution over its 49 syllables, then attempts recovery via
simulated annealing against a trigram LM trained on the other 60%.

Expected result (calibrated): 100% key recovery from ~3.4k tokens.
This establishes that IF rongorongo were a plain syllabic substitution
of chant-register Rapa Nui, the same pipeline would crack it.

SPLIT_SEED controls the train/test partition (default 42, the published
split); vary it to test robustness to the data partition, not just to
the key and optimizer randomness.

Usage: python control_syllabic.py SEED [ITERS] [SPLIT_SEED]
"""
import random, sys
import numpy as np
from common import load_language, build_lm, syllabify, anneal

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 150000
SPLIT_SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 42

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

secret = list(range(S))
rng.shuffle(secret)
enc, oov = [], 0
for v in test_v:
    l = []
    for w in v:
        for s in syllabify(w):
            if s in sid:
                l.append(secret[sid[s]])
            else:
                oov += 1
    if len(l) >= 3:
        enc.append(l)
n_tok = sum(len(l) for l in enc)
print(f"cipher: {len(enc)} lines, {n_tok} tokens "
      f"({oov} OOV test tokens dropped, absent from train vocab)")

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

# evaluate over symbols actually present in the ciphertext: absent
# symbols are unconstrained by the objective and say nothing about it
inv = {secret[p]: p for p in range(S)}
present = [c for c in range(S) if cfreq[c] > 0]

def recovery(mm):
    ok = sum(1 for c in present if mm[c] == inv[c])
    wok = sum(cfreq[c] for c in present if mm[c] == inv[c]) / cfreq.sum()
    return ok, wok

init_ok, init_wok = recovery(m)
print(f"warm start (frequency ranks alone): {init_ok}/{len(present)} symbols "
      f"({100*init_wok:.1f}% of tokens)")

best, bm = anneal(score, m, list(range(S)), ITERS, rng)

correct, wcorrect = recovery(bm)
print(f"RESULT seed={SEED} split={SPLIT_SEED}: key recovered "
      f"{correct}/{len(present)} present symbols ({100*wcorrect:.1f}% of tokens; "
      f"{S - len(present)} absent); logp/token={best/len(A):.3f}")
