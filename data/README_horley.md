# The Horley corpus (`source='horley'`)

The lab reads its transliteration through one function, `common.load_tablets(source=...)`.
`source` resolves from an explicit argument, then the `RR_CORPUS` environment variable,
then defaults to `barthel`.

- **`barthel`** — `tablets_simple.json`, the Barthel (1958) transliteration via rongopy.
  Unchanged historical behaviour. Note it is a **lossy** re-encoding — see
  [README_ceipp.md](README_ceipp.md).
- **`ceipp`** — the C.E.I.P.P. extended-Barthel text, which keeps the allographic suffixes
  and ligature structure rongopy discarded. Built by `src/fetch_ceipp.py`.
- **`horley`** — if a standalone `tablets_horley.json` exists it is loaded directly;
  otherwise the corpus is **derived** by applying `horley_map.json` over the best available
  base (`ceipp` once built, else `barthel`). This lets us test Horley-informed sign decisions
  before a full manual re-encoding of every tablet exists.

> **The shipped map barely fires over `ceipp`.** Its entries are keyed on rongopy-style bare
> three-digit codes (`074`, `280`), but a faithful corpus spells the same signs `074f`,
> `074x`, `050.010.037`. Over `ceipp` the inventory moves only 1584 → 1582. Real entries must
> be written against extended codes; until then, run map experiments against `barthel` and
> read the result as mechanism, not measurement.

## Why a transform instead of a re-typed corpus

The headline concern is that Barthel's transliteration bakes in **contestable
sign-merging decisions**, and every statistic inherits them. Most of the difference
between Barthel and a re-tracing is not *where* signs sit but *which incisions count as
one sign* — allographs, ligatures/fusions, and splits. Those decisions form a bounded
catalog that can be expressed as a function on Barthel codes, which is far more tractable
than re-transcribing ~12k tokens by hand. When individual tablets are fully re-encoded
from Horley's plates or the INSCRIBE 3D models, they drop into `tablets_horley.json` and
supersede the transform for those tablets.

## `horley_map.json` op schema

Applied per raw code sequence (taxograms still present), precedence **ligatures > splits > merges**;
any code named by no op passes through unchanged.

```jsonc
{
  "merges": [
    // several Barthel codes -> one Horley sign (Barthel over-split allographs)
    { "barthel": ["074", "075"], "horley": "H074",
      "confidence": "illustrative", "source": "...", "note": "..." }
  ],
  "splits": [
    // one Barthel code -> a context-dependent Horley sign (Barthel merged distinct signs)
    // 'cases' are tried in order (first match wins); each may test prev_in / next_in
    // against the ORIGINAL neighbours; 'default' applies if no case matches.
    { "barthel": "006",
      "cases": [ { "prev_in": ["003"], "horley": "H006a" } ],
      "default": "006",
      "confidence": "illustrative", "source": "...", "note": "..." }
  ],
  "ligatures": [
    // one Barthel code -> several Horley signs (Barthel fused what Horley reads apart)
    { "barthel": "280", "horley": ["200", "010"],
      "confidence": "illustrative", "source": "...", "note": "..." }
  ]
}
```

Every entry carries **`source`** (citation) and **`confidence`**:

- `published` — the code-level grouping is explicitly stated in a cited source;
- `preliminary` — inferred from a source's method, not verbatim; verify;
- `illustrative` — a placeholder to exercise the pipeline, **not** a real Horley decision.

## Status of the shipped seed — read this

The corpus in `tablets_simple.json` already collapses Barthel allographic sub-variants to
base 3-digit codes, so the shipped `horley_map.json` entries are **`illustrative`
placeholders** chosen only to exercise each op on codes that actually occur. **They are
not verified against Horley's plates and must not be cited as Horley's decisions.**
Replace and extend them with groupings read from the primary sources
(see `docs/HORLEY_ACQUISITION.md`) before drawing any conclusion. `compare_corpora.py`
prints the confidence of every affected code so preliminary content can never be mistaken
for a result.
