"""Shared corpus loading + Rapa Nui trigram LM for rongorongo-lab."""
import json, re, os
import numpy as np
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
TAXOGRAMS = {'200', '400', '000'}   # 200/400: suspected taxograms (Guy 2006); 000: lacuna


def syllabify(word):
    """Rapa Nui (C)V syllables; 'g' = /ng/ in this corpus's orthography."""
    return re.findall(r'[ptkmnvrhg]?[aeiou]', word)


def load_language(path=None):
    """Return list of syllable-sequences (verses) from the chant corpus."""
    path = path or os.path.join(DATA, 'rapanui_chants.txt')
    text = open(path).read().lower()
    verses = [re.findall(r'[a-z]+', l) for l in text.split('\n') if l.strip()]
    out = []
    for v in verses:
        s = [x for w in v for x in syllabify(w)]
        if s:
            out.append(s)
    return out, verses


def build_lm(syll_lines, k=0.1, lam=(0.5, 0.35, 0.15)):
    """Interpolated add-k trigram LM. Returns (LOGP, vocab, sid, BOS)."""
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
