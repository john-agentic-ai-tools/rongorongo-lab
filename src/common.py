"""Shared corpus loading, Rapa Nui trigram LM, and optimizer for rongorongo-lab.

The annealer and the two-phase (syllabic anneal + logogram sweep) helpers
live here so that the control experiments and the rongorongo solvers run
*literally the same* attack code — the calibration claim depends on it.
"""
import json, math, re, os
import numpy as np
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
# 200/400: suspected taxograms (Guy 2006); 000: lacuna.
# NOTE: under 'barthel' (rongopy) these three codes are 21.2% of all tokens, because that
# re-encoding collapses much of the 200-/400- series onto the bare codes 200 and 400. Under
# 'ceipp' the series are intact (208, 225, 290, 380, ...) and only the genuine 200/400 are
# stripped -- a far smaller share. The set is deliberately unchanged; see
# results/corpus_diff_barthel_vs_ceipp.txt for the measured difference.
TAXOGRAMS = {'200', '400', '000'}

# Transliteration sources.
#   'barthel' -- the historical default (Barthel 1958 via rongopy), left untouched so every
#                published result stays reproducible;
#   'ceipp'   -- the Commission Rongorongo / C.E.I.P.P. extended-Barthel text, which keeps
#                the allographic suffixes and sign-combination punctuation rongopy dropped.
#                Built locally by src/fetch_ceipp.py; see data/README_ceipp.md;
#   'horley'  -- a re-tracing-informed corpus: a standalone data/tablets_horley.json if one
#                exists, otherwise derived by applying data/horley_map.json over the best
#                available base (ceipp when built, else barthel).
# See docs/HORLEY_ACQUISITION.md and data/README_horley.md.
CORPORA = {
    'barthel': 'tablets_simple.json',
    'ceipp': 'tablets_ceipp.json',
    'horley': 'tablets_horley.json',   # optional standalone re-encoding; see load_tablets
}

# How the C.E.I.P.P. encoding is resolved into signs. Both default to the faithful reading;
# flipping them IS the sign-merging sensitivity experiment (see docs/HORLEY_ACQUISITION.md).
#   RR_CEIPP_VARIANTS  keep  -- 074f, 074 and 074x are distinct signs (Barthel's own
#                              allographic distinctions preserved)
#                      strip -- fold every allographic suffix onto the base code
#   RR_CEIPP_GROUPS    atomic -- a linked/stacked group is several signs
#                      fused  -- a linked/stacked group is ONE sign (Barthel's own ligature
#                               reading honoured), spelled e.g. '050.010.037'
CEIPP_POLICIES = {'variants': ('keep', 'strip'), 'groups': ('atomic', 'fused')}


def resolve_source(source=None):
    """Corpus selection: explicit arg > env RR_CORPUS > 'barthel'."""
    src = (source or os.environ.get('RR_CORPUS') or 'barthel').lower()
    if src not in CORPORA:
        raise ValueError(f"unknown corpus {src!r}; choose from {sorted(CORPORA)}")
    return src


def ceipp_policy(variants=None, groups=None):
    """Resolve the two C.E.I.P.P. reading policies: explicit arg > env > faithful default."""
    out = {}
    for name, value in (('variants', variants), ('groups', groups)):
        v = (value or os.environ.get('RR_CEIPP_' + name.upper())
             or CEIPP_POLICIES[name][0]).lower()
        if v not in CEIPP_POLICIES[name]:
            raise ValueError(f"unknown RR_CEIPP_{name.upper()}={v!r}; "
                             f"choose from {list(CEIPP_POLICIES[name])}")
        out[name] = v
    return out


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


_CEIPP_SEP = re.compile(r'[.:;]')       # linking / separate stacking / linked stacking
_CEIPP_BASE = re.compile(r'^(\d{1,3})')  # numeric part of an atomic sign


def corpus_stamp(source=None, variants=None, groups=None):
    """Provenance for a result file: which corpus, and under which reading policies.

    Anything derived from 'ceipp' depends on the variants/groups policies as much as on the
    source name, so both go into every result JSON -- otherwise a run cannot be interpreted
    after the fact. Non-C.E.I.P.P. sources stamp the name alone.
    """
    src = resolve_source(source)
    stamp = {'corpus': src}
    derived_from_ceipp = src == 'ceipp' or (
        src == 'horley'
        and not os.path.exists(os.path.join(DATA, CORPORA['horley']))
        and os.path.exists(os.path.join(DATA, CORPORA['ceipp'])))
    if derived_from_ceipp:
        stamp['ceipp_policy'] = ceipp_policy(variants, groups)
    return stamp


def flatten_ceipp(line, variants='keep', groups='atomic'):
    """Resolve one C.E.I.P.P. line ('001-009-755-050.010.037-...') into a list of signs.

    The stored encoding takes no taxonomy decisions, so this is where they are taken --
    explicitly, reversibly, and recorded in every result file:

      groups='atomic'  a linked/stacked group contributes each of its members separately;
      groups='fused'   the whole group is one sign, keeping its punctuation in the label,
                       so '050.010.037' is a single ligature-level symbol;
      variants='keep'  allographic suffixes are significant ('074f' != '074');
      variants='strip' suffixes are folded onto the base code (both become '074').

    Per-sign status markers ('?' doubtful, '!' illegible) are always dropped -- they qualify
    the reading, not the sign identity -- so an illegible sign surfaces as the lacuna 000
    and is then removed by the TAXOGRAMS filter, exactly as under 'barthel'.
    """
    out = []
    for group in line.split('-'):
        if not group:
            continue
        # Split into (sign, separator-that-follows) pairs so a fused label can be rebuilt
        # with the right punctuation even if some component drops out below.
        pieces = _CEIPP_SEP.split(group)
        seps = _CEIPP_SEP.findall(group) + ['']
        kept = [(s.strip('?!'), sep) for s, sep in zip(pieces, seps) if s.strip('?!')]
        if not kept:
            continue
        if variants == 'strip':
            kept = [(_CEIPP_BASE.match(s).group(1).zfill(3) if _CEIPP_BASE.match(s) else s,
                     sep) for s, sep in kept]
        if groups == 'fused' and len(kept) > 1:
            # Keep the original separators so the fused label stays readable and unique;
            # the last component never carries a trailing one.
            out.append(''.join(s + (sep if i < len(kept) - 1 else '')
                               for i, (s, sep) in enumerate(kept)))
        else:
            out.extend(s for s, _ in kept)
    return out


def load_horley_map(path=None):
    """Load data/horley_map.json: Horley's (2021) sign-taxonomy decisions expressed as a
    transform over Barthel codes. Returns a dict with 'merges'/'splits'/'ligatures'
    lists; a missing file yields an empty (identity) map."""
    path = path or os.path.join(DATA, 'horley_map.json')
    if not os.path.exists(path):
        return {'merges': [], 'splits': [], 'ligatures': []}
    hmap = json.load(open(path, encoding='utf-8'))
    for key in ('merges', 'splits', 'ligatures'):
        hmap.setdefault(key, [])
    return hmap


def apply_horley(seq, hmap):
    """Apply the Horley transform to one raw Barthel code sequence (list of code
    strings, taxograms still present) and return the transformed sequence.

    Three op kinds, mutually exclusive per code, checked in this precedence:
      - ligatures: one Barthel code -> several Horley signs (Barthel fused what Horley
        reads as distinct signs);
      - splits:    one Barthel code -> a context-dependent Horley sign (Barthel merged
        what Horley distinguishes), resolved against the *original* neighbours;
      - merges:    several Barthel codes -> one Horley sign (Barthel over-split
        allographs Horley reads as one).
    Codes named by no op pass through unchanged, so unaffected signs keep identical
    labels and stay comparable across corpora.
    """
    merge_of = {}
    for e in hmap.get('merges', []):
        for code in e['barthel']:
            merge_of[code] = e['horley']
    ligature_of = {e['barthel']: list(e['horley']) for e in hmap.get('ligatures', [])}
    split_of = {e['barthel']: e for e in hmap.get('splits', [])}

    out = []
    for i, code in enumerate(seq):
        if code in ligature_of:
            out.extend(ligature_of[code])
        elif code in split_of:
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            out.append(_resolve_split(split_of[code], prev, nxt))
        elif code in merge_of:
            out.append(merge_of[code])
        else:
            out.append(code)
    return out


def _resolve_split(entry, prev, nxt):
    """Pick a Horley sign for a split code from its ordered 'cases' (first match wins),
    falling back to 'default'. A case may condition on 'prev_in' and/or 'next_in'."""
    for case in entry.get('cases', []):
        if 'prev_in' in case and prev not in case['prev_in']:
            continue
        if 'next_in' in case and nxt not in case['next_in']:
            continue
        return case['horley']
    return entry['default']


def load_tablets(path=None, min_len=3, source=None, variants=None, groups=None):
    """Return (lines, names): sign sequences with taxograms removed.

    source selects the transliteration (see resolve_source / CORPORA):
      'barthel' -- the exact historical behaviour, byte for byte;
      'ceipp'   -- the C.E.I.P.P. extended-Barthel text, resolved into signs by
                   flatten_ceipp under the variants/groups policies (see ceipp_policy);
      'horley'  -- a standalone data/tablets_horley.json if present, otherwise the corpus
                   derived by applying data/horley_map.json over the best available base:
                   'ceipp' once it has been built, else 'barthel'.

    An explicit `path` overrides source selection (used by tests/tools); pass `variants` /
    `groups` to override the C.E.I.P.P. policies for one call.
    """
    src = resolve_source(source)
    hmap = None
    is_ceipp = src == 'ceipp'
    if path is None:
        path = os.path.join(DATA, CORPORA[src])
        if src == 'horley' and not os.path.exists(path):
            hmap = load_horley_map()                       # derive from a base + the map
            base = os.path.join(DATA, CORPORA['ceipp'])
            if os.path.exists(base):
                path, is_ceipp = base, True
            else:
                path = os.path.join(DATA, CORPORA['barthel'])
        if is_ceipp and not os.path.exists(path):
            raise FileNotFoundError(
                f'{path} not found -- build it first with: python fetch_ceipp.py')
    tablets = json.load(open(path, encoding='utf-8'))
    pol = ceipp_policy(variants, groups) if is_ceipp else None
    lines, names = [], []
    for tab, tlines in tablets.items():
        if tab.startswith('_'):                            # skip the _meta block
            continue
        for lname, seq in tlines.items():
            codes = (flatten_ceipp(seq, **pol) if is_ceipp
                     else [g for g in seq.split('-') if g])
            if hmap is not None:
                codes = apply_horley(codes, hmap)
            gs = [g for g in codes if g not in TAXOGRAMS]
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
