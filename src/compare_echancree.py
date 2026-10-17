"""Check the Barthel/C.E.I.P.P. reading of item D against the INSCRIBE 3D re-transcription.

The Echancree is the one object in the corpus with a published, independent transcription
made from a sub-millimetre 3D model (Lastilla et al. 2022, DSH 37(2), CC BY-NC). That makes
it the corpus's only available ground truth: where the two readings disagree, at least one
of them is wrong about what is physically carved -- unlike every other disagreement in this
lab, which is a matter of interpretation.

Writes `results/echancree_vs_ceipp.txt`. Usage: python compare_echancree.py [RESULTS_DIR]

What a disagreement means
-------------------------
* a differing element count on a line  -> the two readings segment the incisions differently
  (one sees a ligature where the other sees two signs), or one saw signs the other missed;
* a differing element at the same position -> a genuine reading conflict, the candidate
  discoveries the lab is after.
Neither is automatically a finding: the INSCRIBE transcription marks doubtful readings by
underlining, which does not survive text extraction (see tablets_echancree.json _meta), and
its alternatives (381/741) are deliberately unresolved. Treat the output as a worklist.
"""
import json, os, re, sys

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), '..', 'results')

PAREN = re.compile(r'\([^)]*\)')          # editorial content; may contain '-'
EQUATION = re.compile(r'\(=[^)]*\)')      # an editorial gloss, e.g. 173(=5.225/325)
NUM = re.compile(r'(\d+)')
COMPONENT = re.compile(r'([.:;])')        # linking / stacking inside one element


UNKNOWN = '?'   # an element position the source leaves indeterminate


def split_elements(line):
    """Split one INSCRIBE line into graphic elements, protecting parenthesised content.

    '2*1(-)6-381/741-700' -> ['2*1(-)6', '381/741', '700']; the '-' inside '(-)' is an
    editorial mark, not an element boundary.

    Empty pieces are treated two different ways, and the distinction matters:

    * at the **edges** of a line they are the separator abutting the broken-edge bracket
      (`...-6-[`) and are dropped;
    * in the **interior** they mean the source has an element there that this transcription
      cannot pin down -- Db3 position 9 is printed as a bare `--`, whose glyph is lost in
      both the publisher HTML and the PDF. Such a position becomes UNKNOWN rather than
      vanishing. Dropping it instead would shorten the line by one, which in Db3's case made
      the element count coincidentally match C.E.I.P.P. and silently compared every
      subsequent element against the wrong position.
    """
    held = []

    def hold(m):
        held.append(m.group(0))
        return f'\x00{len(held)-1}\x00'

    masked = PAREN.sub(hold, line.strip().strip('][').strip())
    out = []
    for el in masked.split('-'):
        el = re.sub(r'\x00(\d+)\x00', lambda m: held[int(m.group(1))], el).strip()
        out.append(el)
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return [el or UNKNOWN for el in out]


def pad(el):
    """Zero-fill every numeric run so Barthel's '60' and C.E.I.P.P.'s '060' compare equal."""
    return NUM.sub(lambda m: m.group(1).zfill(3) if len(m.group(1)) <= 3 else m.group(1), el)


def readings(el):
    """Every reading an INSCRIBE element allows, zero-filled.

    The notation is richer than a single string, and comparing it naively manufactures
    conflicts. Three things are expanded:

    * an editorial gloss `(=...)` is dropped -- `173(=5.225/325)` reads as `173`;
    * any other parenthesised chunk is *optional*, because the article uses it for a
      component whose presence is uncertain -- `371/379(.61)` allows both `371/379.61` and
      `371/379`, and `(6x.)206s` both `6x.206s` and `206s`;
    * a `/` offers alternatives for the **component it sits in**, not for the whole element,
      so `42:200.41/11` is `42:200.41` or `42:200.11` -- never the bare `11`.

    Getting the second and third wrong is what previously scored Da4.2 (`371/379(.61)` vs
    C.E.I.P.P. `379.061`) as a reading conflict when the two in fact agree.
    """
    forms = set()
    base = EQUATION.sub('', el)
    for candidate in {PAREN.sub('', base),                      # optional chunks omitted
                      base.replace('(', '').replace(')', '')}:  # ... and included
        parts = COMPONENT.split(candidate)
        options = [[a for a in p.split('/') if a] or [''] if i % 2 == 0 else [p]
                   for i, p in enumerate(parts)]
        for combo in _product(options):
            form = pad(''.join(combo)).strip('.:;')
            if form:
                forms.add(form)
    return forms or {pad(el)}


def _product(options):
    """Cartesian product of per-component alternatives (itertools.product, spelled out to
    keep the dependency surface of this repo at numpy alone)."""
    combos = [[]]
    for opts in options:
        combos = [c + [o] for c in combos for o in opts]
    return combos


def bases(form):
    """The bare 3-digit codes in one concrete reading, in order ('200.052x' -> ['200','052'])."""
    return [n.zfill(3) for n in NUM.findall(form)]


def classify(a, b):
    """Coarsely sort a disagreement, so notation noise does not read as a discovery.

    RECOVERED  C.E.I.P.P. has only lacunae here and INSCRIBE reads actual signs: the 3D
               model recovered incisions the rubbings could not. These are the headline rows.
    ORDER      same codes, different sequence -- almost always the stacking convention
               (C.E.I.P.P. lists a stack top-to-bottom; INSCRIBE does not always).
    SUFFIX     same codes, different allographic suffixes (V, x, y, f, s): a taxonomy
               disagreement, not a disagreement about what is carved.
    CODE       different sign numbers: a genuine conflict about the reading.

    Judged across *all* readings the INSCRIBE element allows, keeping the least alarming
    bucket any of them earns -- an element offering alternatives should not be charged with
    a code conflict when one of its own alternatives lines up.
    """
    bb = bases(b)
    forms = readings(a)
    if bb and set(bb) == {'000'} and any(set(bases(f)) - {'000'} for f in forms):
        return 'RECOVERED'
    verdict = 'CODE'
    for f in forms:
        ba = bases(f)
        if ba == bb:
            return 'SUFFIX'
        if sorted(ba) == sorted(bb):
            verdict = 'ORDER'
    return verdict


def load():
    ins = json.load(open(os.path.join(DATA, 'tablets_echancree.json'), encoding='utf-8'))['D']
    path = os.path.join(DATA, 'tablets_ceipp.json')
    if not os.path.exists(path):
        raise SystemExit(f'{path} not found -- build it first: python fetch_ceipp.py')
    cei = json.load(open(path, encoding='utf-8'))['D']
    return ins, cei


def main():
    ins, cei = load()
    L = ['=== Echancree (item D): INSCRIBE 3D transcription vs C.E.I.P.P. extended Barthel ===',
         '(generated by compare_echancree.py; do not edit by hand)',
         '',
         'INSCRIBE: Lastilla, Ravanelli, Valerio & Ferrara 2022, DSH 37(2) 497-518 (CC BY-NC),',
         'from a photogrammetry + structured-light 3D model; reports 212 graphic elements.',
         'C.E.I.P.P.: Commission Rongorongo, after Barthel 1958, from the rubbings.',
         '']

    tot_i = tot_c = agree = conflict = 0
    seg_rows, conf_rows = [], []
    for lname, iline in sorted(ins.items()):
        cname = lname[:2] + lname[2:].zfill(2)          # Da1 -> Da01
        cline = cei.get(cname, '')
        ie = split_elements(iline)
        ce = [g for g in cline.split('-') if g]
        tot_i += len(ie)
        tot_c += len(ce)
        seg_rows.append((lname, len(ie), len(ce)))
        if len(ie) != len(ce):
            continue                                     # positions are not comparable
        for pos, (a, b) in enumerate(zip(ie, ce), 1):
            b_clean = b.replace('?', '').replace('!', '')
            if b_clean in readings(a) or pad(a) == b_clean:
                agree += 1
            else:
                conflict += 1
                conf_rows.append((f'{lname}.{pos}', a, b, classify(a, b)))

    L.append('Graphic elements per line (a differing count means the two readings segment')
    L.append('the incisions differently, or one of them saw signs the other did not):')
    L.append('  line  | INSCRIBE | C.E.I.P.P. | delta')
    for lname, ni, nc in seg_rows:
        flag = '' if ni == nc else '   <-- segmentation differs'
        L.append(f'  {lname:5s} | {ni:8d} | {nc:10d} | {nc-ni:+5d}{flag}')
    L.append(f'  {"TOTAL":5s} | {tot_i:8d} | {tot_c:10d} | {tot_c-tot_i:+5d}')
    L.append(f'  (INSCRIBE reports 212 graphic elements for the whole tablet; this parse of'
             f' its own\n   transcription yields {tot_i}, so the two counts are themselves'
             ' worth reconciling by hand.)\n')

    comparable = sum(1 for _, ni, nc in seg_rows if ni == nc)
    L.append(f'Position-by-position, on the {comparable} of {len(seg_rows)} lines where the '
             'element counts match:')
    L.append(f'  agree {agree}   conflict {conflict}\n')
    kinds = ('RECOVERED', 'CODE', 'ORDER', 'SUFFIX')
    tally = {k: sum(1 for r in conf_rows if r[3] == k) for k in kinds}
    L.append('  by kind: ' + '   '.join(f'{k} {tally[k]}' for k in kinds))
    L.append('  RECOVERED = C.E.I.P.P. reads only lacunae where the 3D model reads signs;')
    L.append('  CODE = different sign numbers; ORDER = same codes, different sequence')
    L.append('  (usually the stacking convention); SUFFIX = same codes, different allographs.\n')
    L.append('Disagreements (kind | position | INSCRIBE | C.E.I.P.P.):')
    if not conf_rows:
        L.append('  (none)')
    for kind in kinds:
        for pos, a, b, k in conf_rows:
            if k == kind:
                L.append(f'  {kind:9s} | {pos:8s} | {a:28s} | {b}')
    L.append('')
    L.append('Caveats that bound every row above:')
    L.append('  * the INSCRIBE transcription underlines doubtful readings; underlining does')
    L.append('    not survive text extraction, so no element here can be assumed firm;')
    L.append('  * an element is scored generously: alternatives (381/741) count as agreement')
    L.append('    if any reading matches, and a parenthesised component is tried both')
    L.append('    present and absent, so the conflict counts below are conservative;')
    L.append('  * C.E.I.P.P. markers ? (doubtful) and ! (illegible) are ignored when matching;')
    L.append('  * lines whose element counts differ are excluded from the position pass, so')
    L.append('    the conflict count is a floor, not a total.')

    os.makedirs(RES, exist_ok=True)
    out = os.path.join(RES, 'echancree_vs_ceipp.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print(f'wrote {out}')
    print(f'elements: INSCRIBE {tot_i} vs C.E.I.P.P. {tot_c}; '
          f'{comparable}/{len(seg_rows)} lines comparable; '
          f'{agree} agree, {conflict} conflict')


if __name__ == '__main__':
    main()
