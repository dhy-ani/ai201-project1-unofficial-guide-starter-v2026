# Criteria run log — before

- Produced by: `aggregate.py::main`, scored by `scorer.py`
- Retrieval: `store.py::search`; chunks from `chunker.py::split_documents`
- Corpus: `city_guides` (index variant `default`)
- top-k: 5 · relevance cutoff: 0.7
- Runs: 3
- When: 2026-09-28 03:04

| Criterion | Target | Run 1 | Run 2 | Run 3 |
|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 |
| 2. Every answer names a source | 5 of 5 | not measured | not measured | not measured |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 |
| 4. Chunks start at a heading, end on a sentence, >=150 chars | 10 of 10 | pass | pass | pass |
| 5. The named source actually contains the answer | 4 of 5 | not measured | not measured | not measured |

Criteria 2 and 5 read the generated answer. There is no GEMINI_API_KEY in
this environment, so they were not run rather than estimated.

## Criterion 1 — per question (run 1)

| Question | expects | in chunks? | at rank | best distance | closest chunk |
|---|---|---|---|---|---|
| What time do the car parks in Halden Bay fill up on a summer weekend? | `10am` | yes | 2 | 0.3226 | `guide_halden_bay.md#6` |
| Which street in Halden Bay has cheaper food than the harbour front? | `Fell Street` | yes | 1 | 0.2118 | `guide_eating.md#0` |
| How often does the road out to Elder Ness flood? | `six times` | yes | 1 | 0.3121 | `guide_elder_ness.md#1` |
| Which town in the region is easiest to get around with limited mobility? | `Thornby Wells` | yes | 4 | 0.5023 | `guide_corry_vale.md#2` |
| If I am staying in Corry Vale for a few days, where can I buy food? | `farm shop` | yes | 1 | 0.2810 | `guide_corry_vale.md#3` |

## Criterion 3 — the gate, per out-of-scope question

Cutoff 0.7. Retrieval and the gate are deterministic, so this is
one pass and the number is the same in all three run columns above.

| Question | refused? | best distance |
|---|---|---|
| What is the capital of Mongolia? | yes | 0.8026 |
| How do I change the oil in a diesel engine? | yes | 0.8881 |
| Who won the 1994 World Cup? | yes | 0.9753 |
| What is the recommended dosage of ibuprofen for a headache? | yes | 0.8350 |
| How do I write a for loop in Rust? | yes | 0.8365 |

## Criterion 4 — chunk shape, over every chunk

- chunks checked: 94
- not starting at a heading: 0 
- ending mid-sentence: 0 
- under 150 characters: 0 
- shortest 174, longest 762, average 322

Verdict: PASS.

## Determinism check

Every run column above is identical, and that is the expected result:
the index is fixed, retrieval is a nearest-neighbour lookup over fixed
vectors, and the gate is a comparison against a constant. Three passes
confirm no run-to-run variation, which is what makes a single number
reportable for these three criteria. Criteria 2 and 5 depend on the
model and are the ones that would move.
