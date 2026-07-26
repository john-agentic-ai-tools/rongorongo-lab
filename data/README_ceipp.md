# The C.E.I.P.P. corpus (`source='ceipp'`)

`tablets_ceipp.json` is the Commission Rongorongo / C.E.I.P.P. **extended-Barthel**
transliteration of all 26 inscribed objects, built by `src/fetch_ceipp.py` from
`http://kohaumotu.org/rongorongo_org/translit/`.

It is **not committed**. The source's terms permit copying and redistribution only for
non-profit use with attribution, which does not sit comfortably inside this GPL-3.0 tree, so
the file and its HTML cache are gitignored. Rebuild it in one command:

```bash
cd src && python fetch_ceipp.py        # ~200 KB of HTML, cached under data/.ceipp_cache/
```

## Why it exists

The lab's stated worry has always been that *the transliteration bakes in contestable
sign-merging decisions and every statistic inherits them*. That worry is correct — but the
largest merging decisions in `tablets_simple.json` are **not Barthel's**. They were taken
downstream, by the rongopy re-encoding, and they are far more aggressive than anything in
Barthel:

| | `barthel` (rongopy) | `ceipp` |
| --- | --- | --- |
| sign inventory | 239 | **1584** |
| tokens | 11,742 | 14,179 |
| allographic suffixes (`074f`, `600V`, `052x`) | none | 23.9% of tokens |
| linking / stacking structure | discarded | preserved |
| tokens per unicity distance | 17.7× | **2.2×** |

Two further symptoms of the same flattening: under `barthel` the codes `200`/`400`/`000` are
**21.2% of all tokens** — because whole stretches of the 200–/400– series were collapsed onto
the bare series numbers — and `common.TAXOGRAMS` then discards all of them. And `barthel`
contains codes that are not in Barthel's catalogue at all (`901`, `6`), which stops at 791.

## What is stored, and what is decided at load time

`fetch_ceipp.py` stores the encoding **verbatim** and takes no taxonomy decisions:

```
Ca01  001-009-755-050.010.037-005.037-045-001.208.069-700-290-600V-...
      ^ juxtaposed groups separated by '-'; within a group:
        .  linked        signs drawn holding or attached to one another
        :  stacked       one above the other, separate
        ;  stacked       one above the other, vertically joined
        ?  doubtful reading (per sign)      !  illegible, code 000
```

Barthel's `'` (merging) never occurs: the C.E.I.P.P. extended system dropped the ill-defined
link/merge distinction in favour of linking. Codes are zero-filled to three digits, because
some pages publish Barthel's original unpadded numbers (`9`, `40`) and others the padded form.

Turning that into a list of signs requires two decisions, and `common.flatten_ceipp` makes
both explicit, reversible, and recorded in every result file:

| policy | values | effect |
| --- | --- | --- |
| `RR_CEIPP_VARIANTS` | `keep` (default) / `strip` | is `074f` a different sign from `074`? |
| `RR_CEIPP_GROUPS` | `atomic` (default) / `fused` | is `050.010.037` three signs or one? |

The four combinations **are** the sign-merging sensitivity experiment, measured:

| policy | inventory | tokens/U |
| --- | --- | --- |
| `keep` + `atomic` (faithful) | 1584 | 2.2× |
| `strip` + `atomic` | 629 | 5.9× |
| `keep` + `fused` | 3232 | 0.5× |
| `strip` + `fused` | 2257 | — |

`strip`+`atomic` lands at 629 signs, close to the size of Barthel's actual catalogue, and is
the nearest honest analogue to what `barthel` was *trying* to be.

## How to use it

```bash
RR_CORPUS=ceipp python solver_syllabic.py 1
RR_CEIPP_VARIANTS=strip RR_CORPUS=ceipp python solver_syllabic.py 1
python compare_corpora.py barthel ceipp
python compare_corpora.py ceipp ceipp:variants=strip
```

Every result JSON records `corpus` **and** `ceipp_policy`, so no run is ambiguous after the
fact (`common.corpus_stamp`). `source='horley'` now derives from `ceipp` when it has been
built — but note that `horley_map.json`'s entries are keyed on rongopy-style bare codes, so
over a `keep` corpus they barely fire. See [README_horley.md](README_horley.md).

## Attribution

> Numerical transliteration of the corpus: Commission Rongorongo, Centre d'Études sur l'Île
> de Pâques et la Polynésie (C.E.I.P.P.), after Thomas Barthel (1958), who bequeathed his
> materials to the C.E.I.P.P. Presentation: rongorongo.org.
>
> "There are no restrictions on copying and distributing the contents of this site as long as
> the sources are acknowledged and the distribution is non-profit."
> — <http://kohaumotu.org/rongorongo_org/copy.html>

## Caveats

- The site was last updated in 2005 and states that the Rongorongo Commission was then still
  processing line 6 of the Santiago Staff (item I) and had yet to transliterate minor texts
  such as the snuff box (item Y). Later corrections may exist;
- Its TLS certificate is expired, so `fetch_ceipp.py` speaks plain HTTP.
- This is still **Barthel's** taxonomy, in a less lossy encoding. It is not Horley's
  re-tracing and must never be cited as such.
