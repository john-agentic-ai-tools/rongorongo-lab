"""
Build results/consensus_report.txt from the logosyllabic chain outputs
(ror_logo_*.json) and results/best_mapping.json from the best-scoring
syllabic chain (syllabic_chain_*.json). Cross-seed agreement is the
identifiability signal.

Usage: python consensus.py [RESULTS_DIR]
"""
import glob, json, os, sys
from common import load_tablets, glyph_frequencies, resolve_source, corpus_stamp

RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), '..', 'results')
CORPUS = resolve_source(sys.argv[2] if len(sys.argv) > 2 else None)  # or env RR_CORPUS

lines, _ = load_tablets(source=CORPUS)
gfreq = glyph_frequencies(lines)
order = [g for g, _ in gfreq.most_common(49)]

logo_files = sorted(glob.glob(os.path.join(RES, 'ror_logo_*.json')))
chains = [json.load(open(f)) for f in logo_files]
if not chains:
    sys.exit("no ror_logo_*.json found")

def tag(entry):
    return ('l:' if entry['type'] == 'logo' else 's:') + entry['value']

rows, full = [], []
for g in order:
    # A chain run on a different encoding need not contain this sign at all; report that
    # rather than dying on a KeyError, and never let an absence count towards agreement.
    vals = [tag(c['mapping'][g]) if g in c['mapping'] else '(absent)' for c in chains]
    present = [v for v in vals if v != '(absent)']
    n_agree = max((present.count(v) for v in set(present)), default=0)
    mark = 'FULL' if present and n_agree == len(chains) else (
        f'{n_agree}/{len(chains)}' if n_agree > 1 else '-')
    if present and n_agree == len(chains):
        full.append((g, present[0]))
    rows.append((g, vals, mark))

out = os.path.join(RES, 'consensus_report.txt')
with open(out, 'w') as f:
    # A C.E.I.P.P.-derived run is defined by its reading policy as much as by its corpus
    # name, so pool on the full stamp: chains that merely share the name 'ceipp' may be
    # over different sign inventories entirely, and averaging them would be meaningless.
    def stamp_of(c):
        pol = c.get('ceipp_policy')
        return c.get('corpus', 'barthel') + (
            '[' + ','.join(f'{k}={v}' for k, v in sorted(pol.items())) + ']' if pol else '')

    here = corpus_stamp(CORPUS)
    here_str = CORPUS + ('[' + ','.join(
        f'{k}={v}' for k, v in sorted(here['ceipp_policy'].items())) + ']'
        if 'ceipp_policy' in here else '')
    chain_corpora = sorted({stamp_of(c) for c in chains})
    f.write(f'corpus (this report): {here_str}\n')
    f.write(f'corpus (in chains):   {", ".join(chain_corpora)}\n')
    if any(cc != here_str for cc in chain_corpora):
        f.write('WARNING: chain corpus/policy != report corpus/policy; sign order may not '
                'match.\n')
    if len(chain_corpora) > 1:
        f.write('WARNING: these chains do not share one corpus/policy. Cross-seed agreement '
                'below is NOT an identifiability signal -- rerun them on one encoding.\n')
    f.write('\n')
    hdr = 'sign  | ' + ' | '.join(f'seed{c["seed"]:<5}' for c in chains) + ' | agree'
    f.write(hdr + '\n')
    for g, vals, mark in rows:
        f.write(f' {g}  | ' + ' | '.join(f'{v:<9}' for v in vals) + f' | {mark}\n')
    f.write(f'\nFull {len(chains)}-chain agreement: {len(full)}/{len(order)}\n')
    f.write('Consensus SYLLABLES: '
            f'{[(g, v) for g, v in full if v.startswith("s:")]}\n')
    f.write('Consensus LOGOGRAMS: '
            f'{[(g, v) for g, v in full if v.startswith("l:")]}\n')
    f.write(f'\nSign 041 (Mamari crescent): '
            f'{[c["mapping"]["041"] for c in chains]}\n')
print(f'wrote {out}')

syl_files = sorted(glob.glob(os.path.join(RES, 'syllabic_chain_*.json')))
if syl_files:
    best = max((json.load(open(f)) for f in syl_files), key=lambda c: c['score'])
    bm = os.path.join(RES, 'best_mapping.json')
    json.dump({'seed': best['seed'], 'score': best['score'],
               'mapping': best['mapping']}, open(bm, 'w'))
    print(f'wrote {bm} (seed {best["seed"]}, score {best["score"]:.1f})')
