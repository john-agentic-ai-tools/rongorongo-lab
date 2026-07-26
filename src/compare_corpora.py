"""Document, in detail, how two transliterations of the corpus differ.

Loads both through the same `common.load_tablets` seam and writes
`results/corpus_diff_<a>_vs_<b>.txt` (human) and `.json` (machine). This is the
"differences and new discoveries" deliverable: it is *generated*, so it can never drift
from the actual encodings, and it stamps the source/confidence of every affected code so
preliminary map entries can never be mistaken for findings.

Usage: python compare_corpora.py [SRC_A [SRC_B]] [RESULTS_DIR]
       python compare_corpora.py                 # barthel vs horley (historical default)
       python compare_corpora.py barthel ceipp   # what the rongopy re-encoding discarded

Either source may be qualified with C.E.I.P.P. reading policies as
`ceipp:variants=strip`, `ceipp:groups=fused`, or both comma-separated -- so
`compare_corpora.py ceipp ceipp:variants=strip` measures the allograph-merging decision on
its own, holding everything else fixed.

Reported quantities
-------------------
* sign-inventory size under each encoding, and the map's merge/split/ligature counts;
* per-tablet token-count deltas;
* unigram frequency + rank shifts for the most frequent signs;
* Shannon unicity distance recomputed under each inventory (unigram approximation -- see
  note in output; the solver pipeline's trigram LM implies a *shorter* unicity distance,
  so this is a conservative upper bound), and corpus_length / unicity as the "x unicity
  distance" figure the README cites.
"""
import json, math, os, sys
from collections import Counter
from common import load_tablets, glyph_frequencies, load_horley_map, CORPORA, DATA


def parse_spec(spec):
    """'ceipp:variants=strip,groups=fused' -> ('ceipp', {'variants': ..., 'groups': ...})."""
    name, _, opts = spec.partition(':')
    kw = {}
    for opt in filter(None, opts.split(',')):
        key, _, val = opt.partition('=')
        kw[key.strip()] = val.strip()
    return name.strip().lower(), kw


def label(name, kw):
    """Short, filename-safe label distinguishing two runs of the same source."""
    return name + ''.join(f'-{v}' for _, v in sorted(kw.items()))


args = sys.argv[1:]
specs = [a for a in args if parse_spec(a)[0] in CORPORA]
dirs = [a for a in args if parse_spec(a)[0] not in CORPORA]
if len(specs) == 1:
    raise SystemExit(__doc__.split('Usage:')[1].strip())
SPEC_A, SPEC_B = specs[:2] if specs else ('barthel', 'horley')
RES = dirs[0] if dirs else os.path.join(os.path.dirname(__file__), '..', 'results')


def unigram_entropy_bits(freq):
    """Shannon entropy (bits/sign) of a sign-unigram distribution."""
    n = sum(freq.values())
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def unicity(freq):
    """Unicity distance (in signs) for a bijective sign->syllable substitution, unigram
    approximation. H(K)=log2(n!); redundancy D = log2(n) - H1; U = H(K)/D. Returns
    (n, H_key_bits, H1_bits, D_bits_per_sign, U_signs, tokens, tokens_over_U)."""
    n = len(freq)
    tokens = sum(freq.values())
    h_key = math.lgamma(n + 1) / math.log(2)          # log2(n!)
    h1 = unigram_entropy_bits(freq)
    d = math.log2(n) - h1                              # per-sign redundancy
    u = h_key / d if d > 0 else float('inf')
    return n, h_key, h1, d, u, tokens, (tokens / u if u else float('inf'))


def affected_codes(hmap):
    """Flatten the map into (code, op, horley, source, confidence, note) rows."""
    rows = []
    for e in hmap.get('merges', []):
        for c in e['barthel']:
            rows.append((c, 'merge', e['horley'], e.get('source', ''),
                         e.get('confidence', ''), e.get('note', '')))
    for e in hmap.get('splits', []):
        tgt = 'context->' + '/'.join(
            [cs['horley'] for cs in e.get('cases', [])] + [e.get('default', '')])
        rows.append((e['barthel'], 'split', tgt, e.get('source', ''),
                     e.get('confidence', ''), e.get('note', '')))
    for e in hmap.get('ligatures', []):
        rows.append((e['barthel'], 'ligature', '+'.join(e['horley']),
                     e.get('source', ''), e.get('confidence', ''), e.get('note', '')))
    return rows


def per_tablet_tokens(spec):
    name, kw = parse_spec(spec)
    lines, names = load_tablets(source=name, **kw)
    return Counter({nm: len(l) for nm, l in zip(names, lines)}), lines


def main():
    A_NAME, A_KW = parse_spec(SPEC_A)
    B_NAME, B_KW = parse_spec(SPEC_B)
    a_lab, b_lab = label(A_NAME, A_KW), label(B_NAME, B_KW)
    # The map only explains a difference when one side actually applies it.
    show_map = 'horley' in (A_NAME, B_NAME)
    hmap = load_horley_map() if show_map else {}
    rows = affected_codes(hmap) if show_map else []

    b_tok, b_lines = per_tablet_tokens(SPEC_A)
    h_tok, h_lines = per_tablet_tokens(SPEC_B)
    bf, hf = glyph_frequencies(b_lines), glyph_frequencies(h_lines)

    b_rank = {g: i for i, (g, _) in enumerate(bf.most_common(), 1)}
    h_rank = {g: i for i, (g, _) in enumerate(hf.most_common(), 1)}

    bu = unicity(bf)
    hu = unicity(hf)

    # Listing every sign of a large inventory would swamp the report; cap and count.
    only_b, only_h = sorted(set(bf) - set(hf)), sorted(set(hf) - set(bf))
    CAP = 60

    def listing(signs):
        head = ', '.join(signs[:CAP]) or '-'
        return head + (f'  ... (+{len(signs)-CAP} more)' if len(signs) > CAP else '')

    # --- machine-readable ---
    payload = {
        'a': {'spec': SPEC_A, 'source': A_NAME, 'policy': A_KW},
        'b': {'spec': SPEC_B, 'source': B_NAME, 'policy': B_KW},
        'inventory': {a_lab: len(bf), b_lab: len(hf), 'delta': len(hf) - len(bf)},
        'tokens': {a_lab: sum(bf.values()), b_lab: sum(hf.values())},
        'ops': {k: len(hmap.get(k, [])) for k in ('merges', 'splits', 'ligatures')},
        'unicity': {
            a_lab: {'n': bu[0], 'H_key_bits': bu[1], 'H1_bits': bu[2],
                    'redundancy_bits': bu[3], 'U_signs': bu[4],
                    'tokens_over_U': bu[6]},
            b_lab: {'n': hu[0], 'H_key_bits': hu[1], 'H1_bits': hu[2],
                    'redundancy_bits': hu[3], 'U_signs': hu[4],
                    'tokens_over_U': hu[6]},
        },
        'affected_codes': [
            {'barthel': c, 'op': op, 'horley': tgt, 'source': src,
             'confidence': conf, 'note': note}
            for (c, op, tgt, src, conf, note) in rows],
        f'signs_only_in_{b_lab}': only_h,
        f'signs_only_in_{a_lab}': only_b,
    }
    os.makedirs(RES, exist_ok=True)
    stem = f'corpus_diff_{a_lab}_vs_{b_lab}'
    with open(os.path.join(RES, stem + '.json'), 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    # --- human-readable ---
    W = max(len(a_lab), len(b_lab), 7)
    L = []
    L.append(f'=== {SPEC_A} vs {SPEC_B} corpus difference report ===')
    L.append('(generated by compare_corpora.py; do not edit by hand)\n')
    L.append(f'Sign inventory : {a_lab} {len(bf):4d}   {b_lab} {len(hf):4d}   '
             f'delta {len(hf)-len(bf):+d}')
    L.append(f'Total tokens   : {a_lab} {sum(bf.values()):5d}   '
             f'{b_lab} {sum(hf.values()):5d}')
    if show_map:
        L.append(f'Map ops        : {len(hmap.get("merges",[]))} merges, '
                 f'{len(hmap.get("splits",[]))} splits, '
                 f'{len(hmap.get("ligatures",[]))} ligatures')
    L.append('')

    L.append('Unicity distance (unigram approximation; trigram LM implies shorter U):')
    L.append(f'  {"corpus":{W}s} | n_signs | H(key) bits |  H1 b/sign | redund. | '
             'U (signs) | tokens/U')
    for name, u in ((a_lab, bu), (b_lab, hu)):
        L.append(f'  {name:{W}s} | {u[0]:7d} | {u[1]:11.0f} | {u[2]:9.3f} | '
                 f'{u[3]:7.3f} | {u[4]:9.1f} | {u[6]:7.1f}x')
    L.append('  (tokens/U is the README\'s "x unicity distance" figure: higher = more'
             ' over-determined.)\n')

    L.append(f'Signs only in {b_lab} ({len(only_h)}): ' + listing(only_h))
    L.append(f'Signs only in {a_lab} ({len(only_b)}): ' + listing(only_b) + '\n')

    if show_map:
        L.append('Affected Barthel codes (op | -> horley | confidence | source):')
        if not rows:
            L.append('  (none - horley_map.json is empty; the horley corpus == its base)')
        for (c, op, tgt, src, conf, note) in rows:
            present = ' ' if c in bf else '*'  # * = code not in corpus, op is a no-op here
            L.append(f'  {present}{c:>5s} {op:9s} -> {tgt:14s} [{conf}] {src}')
            if note:
                L.append(f'         note: {note}')
        L.append('  (* = code absent from this corpus, so the op does not fire.)\n')

    # rank shifts among the most frequent signs of the left-hand corpus
    L.append(f'Top-20 {a_lab} signs: frequency and rank shift under {b_lab}')
    L.append(f'  sign | {a_lab} f (rank) | {b_lab} f (rank) | note')
    for g, c in bf.most_common(20):
        hr = h_rank.get(g)
        hc = hf.get(g, 0)
        tag = '' if g in hf else 'REMOVED (merged/split/decomposed)'
        rk = f'{hr}' if hr else '-'
        L.append(f'  {g:>7s} | {c:6d} ({b_rank[g]:>4}) | {hc:6d} ({rk:>4}) | {tag}')

    # largest per-tablet token deltas
    deltas = sorted(((nm, h_tok.get(nm, 0) - b_tok.get(nm, 0))
                     for nm in set(b_tok) | set(h_tok)),
                    key=lambda x: -abs(x[1]))
    changed = [d for d in deltas if d[1]]
    L.append(f'\nPer-line token deltas ({b_lab} - {a_lab}), nonzero only '
             f'({len(changed)} of {len(deltas)} lines):')
    if not changed:
        L.append('  (none - every op nets to zero tokens on every line)')
    for nm, d in changed[:20]:
        L.append(f'  {nm:8s} {d:+d}')

    out = os.path.join(RES, stem + '.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print(f'wrote {out}')
    print(f'wrote {os.path.join(RES, stem + ".json")}')
    print(f'inventory: {a_lab} {len(bf)} -> {b_lab} {len(hf)} ({len(hf)-len(bf):+d}); '
          f'tokens/U: {bu[6]:.1f}x -> {hu[6]:.1f}x')


if __name__ == '__main__':
    main()
