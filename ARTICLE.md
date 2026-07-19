# We Tried to Decipher Rongorongo with Machine Learning. What We Proved Instead Is More Interesting.

*A falsifiable computational attack on Easter Island's undeciphered script — with the control experiments that show exactly why every decipherment claim so far has failed, and what it would take to succeed. All code and data included.*

---

Rongorongo may be the hardest decipherment problem in existence. Roughly 26 wooden objects from Rapa Nui (Easter Island) carry about 15,000 signs in a script nobody has read in 150 years. There is no bilingual inscription, no Rosetta Stone. We are not even certain it encodes language at all rather than serving as a mnemonic aid for chanters. The only passage whose *function* most scholars accept is a lunar calendar on the tablet known as Mamari — and even there, nobody can read the words.

Decipherment claims appear every few years. They share a pattern: a proposed sign-to-sound mapping, a few tantalizing readings, and no way to tell whether the method would produce equally convincing output from noise. That last part is the tell. A decipherment method you cannot falsify is not a method; it is a mirror.

So we ran the experiment the other way around. Instead of asking "can we find a mapping that reads well?", we asked: **if rongorongo were a solvable cipher of the Rapa Nui language, would our pipeline provably solve it — and does it?** The answer turned out to be a clean yes to the first half and a clean no to the second, and the gap between those answers is a genuine, quantitative result about the nature of the script.

Everything below is reproducible from a small open-source repository (details at the end). The experiments run in minutes on a laptop.

## The setup

Our raw material is Thomas Barthel's 1958 numerical transliteration of the corpus — each sign assigned a code like `200`, `006`, `041` — as digitized in Jonas Gregorio de Souza's open-source *rongopy* project, covering 13 tablets and roughly 14,500 sign tokens. For the target language we used a corpus of archaic Rapa Nui chants and recitations: short ritual texts of the genre most scholars believe the tablets contain, preserving fossilized forms of the old language.

Three statistical facts anchor everything that follows.

First, after merging Barthel's ligatures and variants, about **41 signs cover 90% of the corpus**. Old Rapa Nui has roughly 50 possible consonant-vowel syllables. That near-match is the classic argument (Pozdniakov, Horley) that the script could be a syllabary.

Second, after removing the two signs long suspected of being taxograms rather than phonetic signs (Barthel 200 and 400), the rank-frequency curve of the signs matches the rank-frequency curve of Rapa Nui syllables remarkably closely.

Third — and this is the number that makes the whole project decidable — the **Shannon unicity distance** for a 49-symbol substitution cipher over Rapa Nui is tiny. The key space is log₂(49!) ≈ 209 bits; Rapa Nui's redundancy under a trigram model is about 2.1 bits per syllable; so a mere **~100 symbols of ciphertext** should suffice, in principle, to pin down the key uniquely. The rongorongo corpus is about 12,000 symbols — **120 times** the unicity distance. If the script is a plain syllabic substitution of this language, the information to crack it is overwhelmingly present.

## The attack

The pipeline is a standard decipherment-as-optimization attack, the same family of methods that automatically re-derived Linear B and Ugaritic in prior computational work. Train a trigram language model over Rapa Nui syllables. Represent a candidate solution as a bijective mapping from the 49 most frequent signs to the 49 syllables. Score a mapping by the log-likelihood of the fully decoded corpus. Optimize with simulated annealing. Run many independent chains from different random seeds.

Crucially, we defined the success criteria *before* looking at outputs, and all three must hold simultaneously:

1. **Cross-chain agreement.** Independent optimization runs must converge to the same mapping. If the corpus determines the answer, seeds shouldn't matter.
2. **Score above a random-mapping baseline** — necessary but nowhere near sufficient.
3. **Lexical emergence.** The decoded corpus must contain real Rapa Nui words — including words *not* in the language-model training data, such as the old lunar night names — at a rate above what random bijections produce. The Mamari calendar serves as a held-out semantic anchor: if crescent-adjacent sign clusters decode to night names, that is signal no optimizer could fake.

## First lesson: the optimizer will cheat if you let it

Our first run allowed non-bijective mappings, and the annealer immediately found the degenerate jackpot: it mapped nearly every sign to the vowels *a*, *e*, and *u*. Decoded "text" looked like `uuaauueeeaauu...` — statistically superb under the language model (vowel runs are common in Polynesian), informationally empty. Classic reward hacking, and a mechanical demonstration of why "my mapping produces plausible-looking Rapa Nui" is worthless as evidence. Enforcing strict bijectivity eliminated the exploit. Any published decipherment that cannot show its objective is hack-proof should be assumed hacked.

## The control experiment that makes everything else meaningful

Here is the experiment we consider the paper's spine. We took the *real* Rapa Nui chant corpus, split it 60/40, trained the language model on the first part only, and enciphered the held-out part with a secret random substitution over its 49 syllables — a synthetic "rongorongo" whose answer key we hold.

The attack recovered the key **perfectly: 100% of symbols, on every random seed, from only ~3,400 tokens of ciphertext.** No partial credit needed. The pipeline, the language model, and the corpus scale are all demonstrably sufficient to crack a genuine syllabic substitution of this language — with a third of the data the real tablets provide.

## And on the real tablets?

The same attack, on 12,000 sign tokens:

- Optimized mappings beat random bijections decisively (z ≈ +10), confirming the sign stream shares real statistical structure with Rapa Nui syllable streams. Something language-like is in there.
- But seven independent chains agreed on the value of only **2 of 49 signs**. The optimization landscape is a plateau of hundreds of near-equivalent solutions.
- Decoded text contained genuine Rapa Nui vocabulary at exactly chance rate (z ≈ +0.4), and the Mamari calendar yielded no night names.

Put the control and the result side by side and the conclusion is sharp:

> **A method that provably cracks a true syllabic substitution of Rapa Nui at one-third the data completely fails on rongorongo at 120× the unicity distance. Therefore rongorongo is not a simple one-sign-one-syllable encoding of the language preserved in the 19th-century chant corpus.**

That eliminates, with quantified confidence, the most optimistic hypothesis — and converts a century of "we couldn't find the mapping" into "the mapping, in this form, does not exist." What survives: a logosyllabic mixed system (word-signs plus phonetic signs, as Albert Davletshin has argued on epigraphic grounds — our result is independent statistical support); a substantially more archaic language stage than the chants; systematic distortions in Barthel's sign segmentation; or proto-writing.

## The logosyllabic trap: compression bias

So we built a second solver in which each sign may be *either* a syllable *or* a logogram spelling a whole word, and — before trusting it — built its control experiment too: a synthetic logosyllabic cipher of real Rapa Nui in which eight frequent words are hidden behind dedicated word-symbols.

The oracle test on that control surfaced what we believe is an underappreciated structural flaw in likelihood-based decipherment. We forced the *ground-truth* answer into the scorer and compared it against wrong single-syllable readings. **The truth lost — for all eight logograms.** The reason is simple once seen: total log-likelihood sums a negative number per emitted token, so any reading that emits *fewer* tokens wins. Reading the word-sign for *mai* as one wrong syllable is cheaper than spelling out the true two syllables. Maximum likelihood is biased toward compression, and the bias points exactly opposite to logogram discovery.

Patching this is nontrivial. A scalar per-token bonus overcorrects into a new degenerate attractor (every sign becomes a logogram of the most internally-predictable word — our solver briefly declared seventeen signs to all mean "banana-plant"). What works acceptably is scoring with a word-level segmentation model plus a one-word-per-sign uniqueness constraint and an MDL penalty, alternating phonetic annealing with logogram sweeps, epigrapher-style. Even then, on the *known-answer* control the method recovers only a majority of the syllable key and a minority of the logograms, with characteristic near-miss confusions among frequent words. That is the honest calibration: **at a few thousand tokens, the logosyllabic inverse problem is only partially identifiable even under ideal conditions.** Anyone claiming a full logosyllabic decipherment of rongorongo from likelihood methods should be asked to show this control.

On the real tablets, the calibrated solver behaves exactly as the calibration predicts: the logogram layer is unstable across seeds (zero consensus assignments), while a small phonetic core keeps re-emerging no matter what we do to the model: sign **003 → i**, **010 → u**, **002 → ka**, **730 → tu**. (An earlier draft claimed the ultra-frequent signs 001 and 006 "behave as vowels"; a follow-up test prompted by Albert Davletshin showed this to be a frequency-rank artifact — in our own known-answer control, vowel symbols are recovered no better than frequency-matched CV symbols, and misassigned vowels land on other vowels at exactly the chance rate. V and CV syllables are not distributionally separable in Rapa Nui at this corpus scale, so we withdraw that observation.) We present the four stable assignments strictly as statistical observations — the kind of anchor a future method might test — not as readings.

## What would actually crack it

The experiments point at a concrete research program rather than a dead end:

**Better plaintext priors.** The chant corpus is small and late. A language model over reconstructed Old Rapa Nui / Proto-Eastern-Polynesian would test the "archaic language" branch directly — our pipeline makes swapping the LM a one-line change, and the controls tell you immediately whether the new LM helps or just hallucinates.

**Better ciphertext.** Barthel's transliteration embeds contestable sign-merging decisions, and our statistics inherit them. Paul Horley's 2021 re-tracings and the photogrammetric 3D-scanning work on the tablets (which has already recovered incisions Barthel's rubbings missed) are the real "highest-resolution images," and re-running this pipeline on a Horley-encoded corpus is probably the single highest-value experiment available.

**Hard constraints from parallel passages.** Three tablets (H, P, Q) carry the same text, and many shorter passages repeat across objects with spelling variations. Those variations are almost certainly allography or phonetic substitution — exactly the constraint type that collapses degenerate optimization plateaus. Our annealer currently ignores them.

**Semantic anchoring.** Treat the Mamari crescents as candidate logograms for lunar vocabulary and propagate constraints outward — the one place the script hands us probable meaning for free.

## Reproduce it, break it, extend it

The repository (`rongorongo-lab`) contains the corpus data (via *rongopy*, GPL-3), the two solvers, both control experiments, and the consensus reports. `pip install numpy` is the only dependency; every experiment runs in under three minutes.

The validation gauntlet is the contribution we most hope survives contact with other people's ideas. Whatever model you prefer — a neural LM, a Bayesian program, a genetic algorithm — it earns the right to be believed about rongorongo only if it (a) cracks the syllabic control, (b) reports its recovery rate on the logosyllabic control, (c) shows cross-seed agreement on the real corpus, and (d) produces held-out lexical emergence, ideally night names near the Mamari crescents. Meet the bar and your mapping means something. Miss it and you have joined a long, distinguished list — but now, at least, you'll know.

*Terminology: following convention in the field, we use "sign" for the catalogued units of the script (Barthel numbers); earlier drafts used "glyph" loosely, which conflates distinct concepts (sign / grapheme / glyph).*

*Corpus data derives from Thomas Barthel's transliteration via Jonas Gregorio de Souza's rongopy project. The interpretation of signs 200/400 as taxograms follows Jacques Guy; the sign-inventory analysis follows Konstantin Pozdniakov and Paul Horley; the logosyllabic hypothesis is argued epigraphically by Albert Davletshin. Errors and the compression-bias framing are ours.*
