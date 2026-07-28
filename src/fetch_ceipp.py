"""Acquire the C.E.I.P.P. extended-Barthel transliteration of the rongorongo corpus.

Downloads the 26 per-object transliteration pages published by the Commission Rongorongo
of the Centre d'Etudes sur l'Ile de Paques et la Polynesie (rongorongo.org / kohaumotu.org)
and writes `data/tablets_ceipp.json` in the same {item: {line: sequence}} shape as
`tablets_simple.json`, so it drops straight into `common.load_tablets(source='ceipp')`.

Why this matters
----------------
`tablets_simple.json` (Barthel via rongopy) is a *lossy* re-encoding: it collapses every
allographic suffix to a bare 3-digit code and rewrites sign-combination punctuation as plain
juxtaposition. The C.E.I.P.P. text preserves both -- the exact sign-taxonomy information the
lab's Horley experiment is about. On Mamari alone that is 228 distinct codes rather than 87.

What is preserved here
----------------------
Verbatim, per line, with no taxonomy decisions taken:
  -   juxtaposition        (signs separated by a space on the object)
  .   linking              (signs drawn holding/attached to one another)
  :   stacking             (signs one above the other, separate)
  ;   linked stacking      (signs one above the other, vertically joined)
  ?   reading doubtful     (per-sign)
  !   illegible / unidentified, code 000
Barthel's `'` (merging) does not occur: the C.E.I.P.P. extended system dispensed with the
ill-defined link/merge distinction in favour of linking.

Resolving `.`/`:` groups into signs, and keeping or folding the allographic suffixes, are
*load-time policies* -- see `common.flatten_ceipp`. Nothing here prejudges them.

Licensing
---------
rongorongo.org states: "There are no restrictions on copying and distributing the contents
of this site as long as the sources are acknowledged and the distribution is non-profit."
That non-profit condition is not compatible with blanket redistribution under this repo's
GPL-3.0, so the built corpus is deliberately NOT committed (see .gitignore) -- run this
script to produce it locally.

Usage: python fetch_ceipp.py [--offline | --refresh]
       --offline rebuilds from data/.ceipp_cache/ without hitting the network;
       --refresh re-downloads every page, ignoring the cache.
"""
import html
import json
import os
import re
import ssl
import sys
import urllib.request
from collections import Counter
from datetime import date

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CACHE = os.path.join(DATA, '.ceipp_cache')
OUT = os.path.join(DATA, 'tablets_ceipp.json')

BASE = 'http://kohaumotu.org/rongorongo_org/translit/'
TERMS = ('There are no restrictions on copying and distributing the contents of this site '
         'as long as the sources are acknowledged and the distribution is non-profit. '
         '-- http://kohaumotu.org/rongorongo_org/copy.html')
CREDIT = ('Commission Rongorongo, Centre d\'Etudes sur l\'Ile de Paques et la Polynesie '
          '(C.E.I.P.P.), after Thomas Barthel (1958), in the C.E.I.P.P. extended system.')

# Item letter -> page basename. Every object is <letter>.html except C (the Mamari tablet),
# which the site publishes under its name. Verified by scraping the ../translit/ link out of
# each corpus/<letter>.html page.
ITEMS = {c: ('mamari' if c == 'C' else c.lower())
         for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'}

# A line identifier is <item letter><side><two digits>; sides are a/b or r(ecto)/v(erso).
LINE_ID = re.compile(r'(?m)^([A-Z][abrv]\d{2})\s')
# One atomic sign: digits, optional letter suffixes (V variant, y mirrored, x inverted,
# h superscript, t subscript, i/j/k missing protrusions, a-g disambiguators...), optional
# status marker. Suffixes stack, e.g. 062fx, 095bjt.
SIGN = re.compile(r'^(\d{1,3})([A-Za-z]*)([?!]?)$')
# An illegible stretch of unknown length: "(10-20)" = between 10 and 20 lost signs.
LACUNA_RUN = re.compile(r'\((\d+)-(\d+)\)([?!]?)')


def _context():
    """TLS context used only if the host redirects to HTTPS.

    The site's certificate expired years ago, so verification cannot succeed and is turned
    off. Be clear about what that costs: BASE is plain HTTP to begin with, so this transfer
    is unauthenticated either way, and anyone able to intercept it could serve a corpus of
    their choosing. Nothing fetched here is executed -- it is regex-parsed into strings and
    written as JSON -- so the exposure is to *corrupted data*, not to code execution, and
    the Mamari assertion in main() is the tripwire for exactly that. If the C.E.I.P.P. ever
    serves a valid certificate, delete this and let urllib verify normally.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(name, offline=False, refresh=False):
    """Return the raw HTML for one transliteration page, via an on-disk cache."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name + '.html')
    if os.path.exists(path) and not refresh:
        return open(path, encoding='latin-1').read()
    if offline:
        raise SystemExit(f'--offline but {path} is not cached; run without --offline first')
    # The host answers 406 to urllib's default User-Agent.
    req = urllib.request.Request(BASE + name + '.html',
                                 headers={'User-Agent': 'Mozilla/5.0 (rongorongo-lab)'})
    with urllib.request.urlopen(req, timeout=60, context=_context()) as r:
        raw = r.read().decode('latin-1')
    if '404 - PAGE NOT FOUND' in raw:
        raise SystemExit(f'{BASE}{name}.html returned the site 404 page')
    tmp = path + '.part'          # write-then-rename: never leave a half page in the cache
    with open(tmp, 'w', encoding='latin-1') as f:
        f.write(raw)
    os.replace(tmp, path)
    return raw


def strip_markup(raw):
    """HTML -> plain text, entities resolved, tags gone."""
    return html.unescape(re.sub(r'<[^>]*>', '', raw))


def normalize_sign(tok):
    """Zero-fill one atomic sign to the 3-digit C.E.I.P.P. form, keeping suffix and marker.

    Some pages (e.g. item A) publish Barthel's original unpadded codes while others are
    already padded, so `9`, `40`, `430` and `009`, `040`, `430` must land on one spelling.
    """
    m = SIGN.match(tok)
    if not m:
        raise ValueError(f'unparsable sign {tok!r}')
    num, suffix, marker = m.groups()
    return f'{int(num):03d}{suffix}{marker}'


def parse_line(seq):
    """One raw sequence string -> the canonical '-'-joined group encoding.

    Whitespace (including the hard wraps inside a page) is removed, illegible runs are
    expanded to their lower-bound count of 000 lacunae, and every atomic sign is zero-filled.
    Group structure ('.' linked, ':' stacked) is preserved untouched.
    """
    seq = re.sub(r'\s+', '', seq)
    seq = seq.split('*')[0]                      # '*' terminates the line
    # Expand "(10-20)" before splitting on '-', which otherwise cuts the run in half.
    seq = LACUNA_RUN.sub(lambda m: '-'.join(['000' + m.group(3)] * int(m.group(1))), seq)

    groups = []
    for group in seq.split('-'):
        if not group:
            continue
        parts = re.split(r'([.:;])', group)      # keep the separators
        out = [parts[0] and normalize_sign(parts[0])]
        for sep, sign in zip(parts[1::2], parts[2::2]):
            out.append(sep + normalize_sign(sign))
        groups.append(''.join(p for p in out if p))
    return '-'.join(groups)


def parse_page(raw):
    """One transliteration page -> {line_id: sequence}, in document order."""
    txt = strip_markup(raw)
    txt = txt[txt.find('Nota bene'):]            # skip nav + heading prose
    parts = LINE_ID.split(txt)
    lines = {}
    for i in range(1, len(parts) - 1, 2):
        lines[parts[i]] = parse_line(parts[i + 1])
    return lines


def atoms(seq):
    """Atomic signs of a canonical sequence, markers stripped (counting helper)."""
    return [s.strip('?!') for g in seq.split('-')
            for s in re.split(r'[.:;]', g) if s.strip('?!')]


def main():
    offline, refresh = '--offline' in sys.argv, '--refresh' in sys.argv
    if offline and refresh:
        raise SystemExit('--offline and --refresh are mutually exclusive')
    tablets, report = {}, []
    for item, name in ITEMS.items():
        lines = parse_page(fetch(name, offline, refresh))
        if not lines:
            raise SystemExit(f'item {item} ({name}.html): no lines parsed')
        tablets[item] = lines
        groups = sum(len([g for g in s.split('-') if g]) for s in lines.values())
        signs = sum(len(atoms(s)) for s in lines.values())
        report.append((item, len(lines), groups, signs))

    # --- self-checks: a parser that silently drops signs is the failure mode that matters ---
    assert len(tablets) == 26, f'expected 26 items, got {len(tablets)}'
    c = tablets['C']
    c_lines = len(c)
    c_groups = sum(len([g for g in s.split('-') if g]) for s in c.values())
    c_signs = sum(len(atoms(s)) for s in c.values())
    c_inv = len({a for s in c.values() for a in atoms(s)})
    assert (c_lines, c_groups, c_signs, c_inv) == (28, 774, 1004, 228), (
        f'Mamari check failed: got {(c_lines, c_groups, c_signs, c_inv)}, '
        f'expected (28, 774, 1004, 228) -- the page or the parser changed')

    payload = {
        '_meta': {
            'source': CREDIT,
            'urls': {i: BASE + n + '.html' for i, n in ITEMS.items()},
            'fetched': date.today().isoformat(),
            'terms': TERMS,
            'encoding': ("C.E.I.P.P. extended Barthel. Per line, signs are '-'-separated "
                         "juxtaposition groups; within a group '.' is linking, ':' is "
                         "separate stacking and ';' linked stacking. A trailing '?' marks "
                         "a doubtful reading, '!' an "
                         "illegible sign (code 000). Resolving groups and keeping or "
                         "folding allographic suffixes are load-time policies -- see "
                         "common.flatten_ceipp."),
            'not_committed': ('Built locally by src/fetch_ceipp.py and gitignored: the '
                              "source's non-profit condition does not sit comfortably "
                              'inside a GPL-3.0 tree.'),
        },
        **tablets,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    tot_signs = sum(r[3] for r in report)
    inv = Counter(a for t in tablets.values() for s in t.values() for a in atoms(s))
    print(f'wrote {OUT}')
    print(f'{"item":5s} {"lines":>6s} {"groups":>7s} {"signs":>7s}')
    for item, nl, ng, ns in report:
        print(f'{item:5s} {nl:6d} {ng:7d} {ns:7d}')
    print(f'{"TOTAL":5s} {sum(r[1] for r in report):6d} '
          f'{sum(r[2] for r in report):7d} {tot_signs:7d}')
    suffixed = sum(v for k, v in inv.items() if not k.isdigit())
    print(f'inventory {len(inv)} distinct atomic signs; '
          f'{suffixed} tokens ({100*suffixed/tot_signs:.1f}%) carry an allographic suffix')


if __name__ == '__main__':
    main()
