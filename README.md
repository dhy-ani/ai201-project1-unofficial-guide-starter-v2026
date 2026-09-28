# The Unofficial Guide

**Dhyani** · corpus: `city_guides`

---

# Unit 1

## What This Does

This is a question-answering system over `city_guides`, fourteen travel guides
covering nine towns in one invented region — Brightwater, Halden Bay,
Kestrelford, Marchwood, Pellew Sands, Thornby Wells, Givens Mill, Elder Ness and
the Corry Vale villages — plus five guides that cut across all of them on eating,
walking, regional transport, seasons and accessibility. You ask it a plain
question and it answers from those documents only, naming the file the answer
came from.

It handles the practical questions a guidebook index can't: "what time do the car
parks in Halden Bay fill up on a summer weekend?", "which street has cheaper food
than the harbour front?", "how often does the road out to Elder Ness flood?" —
the kind where the answer is one sentence buried in the middle of a section about
something else. It is good at questions that name a place and want a specific
fact, and weaker on questions that compare towns, because those need several
documents at once and it retrieves five chunks total.

Ask it something the region's guides don't cover and it says so rather than
guessing. That is a check in my own code, not a request to the model: before any
answer is written, `gate.py` looks at how far the closest retrieved chunk
actually is, and if it is past 0.70 the question stops there and the system
returns "I don't have enough information about that."

Run it with `python app.py index` once, then
`python app.py ask "your question"`.

## Chunking Strategy

**Chunk size:** one `##` section, with a ceiling of 1100 characters
(`CHUNK_SIZE`) and a floor of 150 (`CHUNK_MIN`). In practice the sections decide
the size, not the ceiling — the corpus comes out at 322 characters on average,
shortest 174, longest 762.

**Overlap:** 150 characters (`CHUNK_OVERLAP`), and it almost never fires. The
overlap only applies when a single section is longer than the ceiling, which no
section in `city_guides` is. What every chunk *does* carry is its document's
title line, repeated at the top.

**Why these numbers.** I picked `city_guides`, and when I read four of the
guides in Milestone 1 the shape was obvious: each file is a title, sometimes an
introductory paragraph, and then a run of `##` sections called "Getting there",
"Getting around", "Eat and drink", "What to see", "Where to stay", "When to go",
"Practical notes". Someone already decided where one thought ends and the next
begins. A character count throws that away. So I split on the headings the
author wrote and made a section a chunk.

Then I measured before committing to a ceiling: across the 14 documents there
are 98 sections, running 23 to 711 characters with a median of 284. Nothing is
close to 1100. That is the point of the number — it is a guard against a corpus
that isn't this one, not a target. If I ever point this chunker at a document
with a 4,000-character section, rule 3 splits it at paragraph breaks rather than
silently emitting a 4,000-character chunk. The 150-character floor is the
opposite guard, and it is set just under the thinnest real section in the corpus
(Elder Ness's "Eat and drink", a bit over 200), so anything below it is not a
section — it is wreckage.

**What the starter did, for comparison.** The fixed 800-character window turned
14 documents into 51 chunks averaging 650 characters, shortest 24, longest 800.
Reading `guide_kestrelford.md` as it cut it:

- chunk `#0` ended on the literal text `## Eat and drin` — a heading sliced
  mid-word,
- chunks `#1` and `#2` each opened mid-sentence (`lower car park is steeper
  than it looks...`),
- chunk `#3` was the leftover: `irts. The nearest full hospital is in
  Brightwater; there is` — 60 characters, half of them the tail of the word
  "outskirts".

My chunker turns the same file into 8 chunks, each one a whole section.

**The thing I nearly got wrong.** The plan was to emit the bare section and
nothing else. What stopped me was running the milestone's own test — "could
someone answer a question using only this?" — against a section before writing
any code. Halden Bay's "Getting around", on its own, reads:

> The town is small enough to cross in fifteen minutes but is built on three
> levels connected by stepped lanes... The harbour front is level; everything
> above it is not.

Nothing in it says Halden Bay. A section body in this corpus almost never names
its own town, because the title at the top of the file already did. Cut loose
from the file, that chunk is unusable twice over: retrieval has nothing to match
the word "Halden" against, and an answer built from it has nothing to attribute.
So every chunk carries `# <document title>` at the top, and that went in before
the first run rather than after. That is why the floor is 150 rather than the
~100 the raw sections would have allowed — the title line costs characters.

The same fix does a second job I didn't plan for. Nine of the fourteen guides
end with a word-for-word identical "Practical notes" paragraph about cash,
mobile coverage and the nearest hospital. As raw sections those nine chunks are
nine near-identical vectors and there is no way to tell which town's copy came
back. Prefixed with their titles they are nine *different* chunks, which is what
criterion 5 in `criteria.md` is about.

**One thing I deliberately did not do.** Four of the fourteen guides — walking,
eating, seasons, regional transport — open with a title and go straight into a
`##` heading, with no introduction. That produces a 23-to-27-character preamble
that is just the title line. I merge it forward into the first section (rule 4)
rather than emitting it. It would have passed as a chunk and told a reader
nothing.

## Sample Chunks

All five printed by `python app.py --corpus city_guides chunks -n 5`, which
samples across the corpus. Function: `chunker.py::split_documents` for all of
them.

**Chunk 1** — source: `guide_accessibility.md#0` — produced by: `chunker.py::split_documents`

```
# Getting around the region with limited mobility

An honest assessment rather than a promotional one. Some of these places are
difficult and it is better to know in advance.
```

**Chunk 2** — source: `guide_corry_vale.md#5` — produced by: `chunker.py::split_documents`

```
# Corry Vale

## Where to stay

Perhaps thirty beds in the entire valley, spread across two pubs and a handful of farmhouse rooms. In summer these are booked months ahead. Camping is permitted on two marked fields and nowhere else.
```

**Chunk 3** — source: `guide_givens_mill.md#2` — produced by: `chunker.py::split_documents`

```
# Givens Mill

## Getting around

Everything is on one street along the river. The mill is at one end and the church at the other, eight minutes apart. The riverside path continues in both directions for as far as you want to walk.
```

**Chunk 4** — source: `guide_kestrelford.md#4` — produced by: `chunker.py::split_documents`

```
# Kestrelford

## What to see

The market square on a Saturday morning is the main event and has run continuously since the 1400s. The parish church has a 13th-century tower you can climb for £2. The old trackbed walk runs six miles to the next village along an easy gradient and is the best half-day here.
```

**Chunk 5** — source: `guide_pellew_sands.md#6` — produced by: `chunker.py::split_documents`

```
# Pellew Sands

## When to go

June and September for the beach without the crowds. July and August are busy and the town is at its most itself, for better and worse. Winter is bleak, largely closed, and has a following among people who like that sort of thing.
```

**Reading them against the "could someone answer a question using only this?"
test.** Chunks 2 to 5 each answer one question completely and name their own
town, which is exactly what I was after. Chunk 1 is the honest weak one: it is a
document introduction, so it says a judgement is coming without containing the
judgement. It is 174 characters, which clears my floor, and it is the kind of
chunk that can be retrieved for an accessibility question and then contribute
nothing to the answer. I left it in rather than merging it, because the four
sections that follow it in that file *are* the content and the introduction is a
fair thing for the corpus to contain — but it is the first thing I would look at
in unit 2 if accessibility questions come back thin.

## Sample Answer

<!-- PASTE PENDING: needs one real model call. See "Sample answer" note at the
     bottom of this section. -->

**Question:**

**Answer:**

```
```

### Retrieval, before the model runs

`python app.py retrieve` for the same question, which is the part that decides
what an answer can possibly be based on:

```
Question: Which street in Halden Bay has cheaper food than the harbour front?

#   distance   source                           preview
----------------------------------------------------------------------------------------------------
1   0.2118     guide_eating.md                  # Eating across the region  ## The pattern worth kno...
2   0.2162     guide_halden_bay.md              # Halden Bay  ## Eat and drink  Seafood, unsurprisin...
3   0.2827     guide_eating.md                  # Eating across the region  ## Local specifics  Hald...
4   0.3442     guide_halden_bay.md              # Halden Bay  ## Getting around  The town is small e...
5   0.3584     guide_halden_bay.md              # Halden Bay  Halden Bay is a working fishing port o...

Gate: best distance 0.212 is under the 0.7 cutoff
```

All five retrieved chunks are about Halden Bay or about regional eating, and the
answer ("Fell Street") is in both of the top two. This is the case where the
title prefix earns its keep: chunk 1 comes from `guide_eating.md`, whose "The
pattern worth knowing" section discusses five towns at once, and chunk 2 is
Halden Bay's own "Eat and drink". Both say Fell Street, which is why the
tightened instruction asks for both filenames rather than whichever one the model
noticed first.

**My relevance cutoff: `THRESHOLD = 0.70`.**

I ran all five of my questions and all five of the `OUT_OF_SCOPE` ones through
`store.search` at `top_k=5` and recorded the best (lowest) distance for each.

| Question | In corpus? | Best distance |
|---|---|---|
| Which street in Halden Bay has cheaper food than the harbour front? | yes | 0.2118 |
| If I am staying in Corry Vale for a few days, where can I buy food? | yes | 0.2810 |
| How often does the road out to Elder Ness flood? | yes | 0.3121 |
| What time do the car parks in Halden Bay fill up on a summer weekend? | yes | 0.3226 |
| Which town in the region is easiest to get around with limited mobility? | yes | 0.5023 |
| What is the capital of Mongolia? | no | 0.8026 |
| What is the recommended dosage of ibuprofen for a headache? | no | 0.8350 |
| How do I write a for loop in Rust? | no | 0.8365 |
| How do I change the oil in a diesel engine? | no | 0.8881 |
| Who won the 1994 World Cup? | no | 0.9753 |

**What the two groups looked like.** In-corpus 0.2118 to 0.5023. Out-of-corpus
0.8026 to 0.9753. A gap of 0.30 with nothing in it — no overlap, not even a near
miss. Four of the five in-corpus questions are under 0.33; the corpus is small
and the questions are answerable, so that is about what I expected.

**Why 0.70 and not the midpoint.** The midpoint of the gap is 0.65, and 0.65
would work on these ten questions. I went to 0.70 because the gap is wider than
the problem is. My five questions were written by someone who had just read all
fourteen documents, so they use the corpus's own vocabulary and score better than
a real user's question will; 0.5023 is a floor on how bad an answerable question
can look, not a ceiling. Meanwhile the `OUT_OF_SCOPE` five are absurdly far away
— Mongolia and diesel engines — and the real risk is a question that is
off-corpus but adjacent, like "is there an airport shuttle", which would score
nowhere near 0.80. So I spent the extra margin where a real question is more
likely to land: 0.70 sits 0.20 above my worst genuine question and still 0.10
below my closest nonsense one.

At 0.70 the gate lets through 5 of 5 in-corpus questions and refuses 5 of 5
out-of-corpus ones.

**What I'd get wrong at that number.** Too high in one direction: a question
about a neighbouring region, or about a town this corpus doesn't cover, could
land around 0.6–0.7 and get through the gate, at which point the only thing
stopping a bad answer is the grounding instruction. That is a real exposure and
it is the reason I tightened `GROUNDING_INSTRUCTION` in `generate.py` rather than
treating the gate as sufficient. In the other direction, at 0.70 I am almost
certainly refusing nothing I should be answering — which is a comfortable place
to be wrong, but it does mean criterion 3's "4 of 5" is being tested against the
easy version of the problem.

### Top-k

Left at 5, after checking. The answer to my accessibility question
("Thornby Wells") is in `guide_accessibility.md#1`, which comes back at **rank
4**, distance 0.5528:

| top-k | questions whose `expects` phrase is in the retrieved chunks |
|---|---|
| 3 | 4 of 5 |
| 4 | 5 of 5 |
| 5 | 5 of 5 |
| 6 | 5 of 5 |
| 8 | 5 of 5 |

So `top_k=3` would have quietly cost me a question and `top_k=4` is the minimum
that works. I kept 5 for one slot of margin. Raising it to 8 found nothing new —
it added two more Corry Vale sections that don't answer the question, which is
the "bury it in loosely related material" failure.

That question is also where the weak chunk I flagged above shows up:
`guide_accessibility.md#0`, the document's introduction, is retrieved at rank 2
(0.5113) and contributes nothing to the answer. One of my five retrieval slots is
spent on a chunk that says a judgement is coming without containing it.

<!-- Sample answer: the question/answer block at the top of this section is the
     only thing in this README that needs a live model call. Run:

         python app.py ask "Which street in Halden Bay has cheaper food than the harbour front?"

     and paste the answer and the "Sources retrieved:" line into the block. -->

## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

I built this in a Claude Code session, so AI wrote most of the code in this
repo. The two moments below are the ones where what came back needed changing,
which is the part worth writing down.

**1. It gave me a chunk size before it had looked at the documents.** I asked for
a chunker that splits `city_guides` on its `##` headings, and the draft came back
with round numbers — a 1000-character ceiling, a 200-character floor — chosen
before anything had counted a section. That is the exact thing the brief tells
you not to do, so I made it print the distribution first: 98 sections across the
14 documents, 23 to 711 characters, median 284. Two things changed once I could
see that. The ceiling turned out not to be a chunk size at all — nothing in the
corpus comes near it — so it is only a guard for some other corpus, and I wrote
`config.py`'s comment to say that rather than implying I had tuned it. And the
floor moved from 200 to 150, because the number that matters is the thinnest
genuine section in the corpus (Elder Ness's "Eat and drink", a bit over 200
characters), and a 200 floor would have started merging real sections into each
other. Counting also turned up the four title-only preambles — walking, eating,
seasons and regional transport open with a heading and no introduction, giving a
23-character fragment — which is what rule 4 in `split_documents` exists for.

**2. It pasted retrieval output into this README that it had not actually run.**
Writing up the Sample Answer section, Claude produced a `python app.py retrieve`
output block for the Halden Bay question, formatted exactly like the real thing,
column alignment and all. Rows 1 and 2 were right. Rows 3, 4 and 5 were invented
— it had my five *best* distances in context from an earlier measurement and
filled the rest of the table from documents that looked plausible. I ran the
command. The real rows 3–5 are `guide_eating.md` at 0.2827, then
`guide_halden_bay.md` at 0.3442 and 0.3584; the invented ones claimed 0.3684 and
0.4508 from sections that were never retrieved. I replaced the block with the
actual output, which is what is in this README now.

What I am taking into unit 2 from that second one: the failure looked exactly
like success. A well-formatted table is not a measurement, and the only defence
was running the command and pasting what came back. It is the same failure this
system's relevance gate and grounding instruction exist to prevent — a confident,
plausible, unsourced answer — which is an uncomfortable thing to catch in my own
write-up while building a thing designed to catch it.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---
# Unit 2

## A note on what could and couldn't be tested

Three of my five criteria were measured properly. Two were not, and the reason
is not a judgement call I made — it is that this environment has no
`GEMINI_API_KEY`, so `run_eval.py` raises on its first question and writes no
file at all:

```
RuntimeError: No GEMINI_API_KEY found.
Copy .env.example to .env and paste your key in, then try again.
```

Criteria 1, 3 and 4 do not touch the model. Criterion 1 is about what retrieval
brings back, criterion 3 is about a numeric comparison in `gate.py`, and
criterion 4 is about the shape of the chunks — none of them needs an answer to
exist. Those three are measured, three runs each, by `aggregate.py::main`
scored by `scorer.py`, with the output committed in `results/`.

Criteria 2 and 5 both read the generated answer. They are reported as **not
measured** everywhere below. I have not estimated them, inferred them from the
retrieval results, or marked them MET on the grounds that they probably would
be. An untested criterion is not a passed criterion.

## Run Log — Before

`python aggregate.py --label before` →
[`results/criteria_2026-09-28_0304_before.md`](results/criteria_2026-09-28_0304_before.md)

Corpus `city_guides`, 94 chunks, top-k 5, cutoff 0.70, semantic retrieval only.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | not measured | not measured | not measured | NOT TESTED |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Chunks: start at heading, end on sentence, ≥150 chars | 10 of 10 | pass | pass | pass | MET |
| 5. The named source actually contains the answer | 4 of 5 | not measured | not measured | not measured | NOT TESTED |

**All three run columns are identical, and that is the correct result rather
than a caching artefact.** The index is fixed, retrieval is a nearest-neighbour
lookup over fixed vectors, and the gate is a comparison against a constant —
criteria 1, 3 and 4 have no source of run-to-run variation. Running them three
times is the check that this is true, and it came back true. The two criteria
that *would* have moved between runs are exactly the two I could not run.

### Real output — criterion 1

From `aggregate.py::measure`, scored by `scorer.py::retrieval_hit`:

| Question | expects | in chunks? | at rank | best distance | closest chunk |
|---|---|---|---|---|---|
| What time do the car parks in Halden Bay fill up on a summer weekend? | `10am` | yes | 2 | 0.3226 | `guide_halden_bay.md#6` |
| Which street in Halden Bay has cheaper food than the harbour front? | `Fell Street` | yes | 1 | 0.2118 | `guide_eating.md#0` |
| How often does the road out to Elder Ness flood? | `six times` | yes | 1 | 0.3121 | `guide_elder_ness.md#1` |
| Which town in the region is easiest to get around with limited mobility? | `Thornby Wells` | yes | 4 | 0.5023 | `guide_corry_vale.md#2` |
| If I am staying in Corry Vale for a few days, where can I buy food? | `farm shop` | yes | 1 | 0.2810 | `guide_corry_vale.md#3` |

### Real output — criterion 3

From `aggregate.py::measure` via `gate.py::check`, cutoff 0.70:

| Question | refused? | best distance |
|---|---|---|
| What is the capital of Mongolia? | yes | 0.8026 |
| How do I change the oil in a diesel engine? | yes | 0.8881 |
| Who won the 1994 World Cup? | yes | 0.9753 |
| What is the recommended dosage of ibuprofen for a headache? | yes | 0.8350 |
| How do I write a for loop in Rust? | yes | 0.8365 |

### Real output — criterion 4

From `scorer.py::chunks_well_formed` over every chunk from
`chunker.py::split_documents`, not a sample of ten:

```
- chunks checked: 94
- not starting at a heading: 0 []
- ending mid-sentence: 0 []
- under 150 characters: 0 []
- shortest 174, longest 762, average 322
Verdict: PASS.
```

## Verdicts

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer (4 of 5) | **MET** | 5/5 on all three runs. No judgement needed — `scorer.py::retrieval_hit` does a substring match for the `expects` phrase I wrote in unit 1, so I am not grading my own wording. |
| 2 | Every answer names a source (5 of 5) | **NOT TESTED** | Needs a generated answer. No API key in this environment, so `run_eval.py` never completed a single question. Not marked MET. |
| 3 | Gate stops out-of-corpus questions (4 of 5) | **MET** | 5/5. The closest out-of-corpus question was 0.8026 against a 0.70 cutoff, so it wasn't close. |
| 4 | Chunk shape (10 of 10 sampled) | **MET** | My criterion allowed me to read ten chunks by hand; I checked all 94 in code instead, which is strictly harder, and got zero violations in each of the three categories. |
| 5 | Named source actually contains the answer (4 of 5) | **NOT TESTED** | Same reason as criterion 2. This is the one I most wanted to test, because it is the one I wrote the corpus-specific risk into. |

I want to be plain about criterion 4, because "MET" flatters it. I said in unit
1 that it was a structural guarantee rather than a judgement call, and that is
exactly how it behaved: my chunker prefixes every chunk with `# <title>`, so
"begins at a heading" cannot fail without the splitter being broken. Passing it
tells you the chunker is doing what it says, and nothing about whether the
chunks are good. The 150-character floor is the only part that was ever at
real risk, and 174 is not a comfortable margin — one thinner section in a
future corpus and it fails.

## Diagnoses

**No measured criterion was missed.** So, per the milestone, the honest question
is whether the targets were set low. Three of them were, in different ways, and
one wasn't but got lucky.

**Criterion 3 was set too easy, and I said so at the time.** My unit 1 reason
for keeping 4 of 5 rather than 5 of 5 reads: *"`OUT_OF_SCOPE` asks about
Mongolia, diesel engines and Rust... My five are the easy version of this test,
so I am not going to claim a perfect score against the easy version."* That was
correct and I still failed to act on it — I should have replaced the questions
with adjacent ones rather than predicting they were too easy and running them
anyway. The measured gap is 0.5023 to 0.8026, and the cutoff sits at 0.70 with
0.20 of clearance on one side and 0.10 on the other. Nothing in this test
touched the cutoff.

**Criterion 4 is true by construction**, as above.

**Criterion 1 hit its target, but my reasoning behind the target was wrong**,
and that is the most useful thing this test produced. In unit 1 I wrote: *"the
farm shop is named in exactly two documents out of fourteen... If one question
misses, I expect it to be this one."* The Corry Vale question came back at
**rank 1, distance 0.2810** — one of the strongest results in the set. The
question that nearly failed was the one I had not worried about at all:

> Which town in the region is easiest to get around with limited mobility?

Answer at **rank 4**, best distance **0.5023**, and the top-ranked chunk was
`guide_corry_vale.md#2` — a section from a document that has nothing to do with
the question. At `top_k=3` this question fails and criterion 1 comes out 4/5.
It passed on a one-slot margin.

**The mechanism, which is the actual diagnosis: the retrieval stage, and
specifically an embedding-similarity failure that chunking made visible.** My
chunker stamps every chunk with its document title, so the corpus contains nine
chunks whose text begins `## Getting around` under nine different town titles.
The question asks which town is "easiest to get around". Cosine similarity sees
nine strong, near-identical matches for the *topic* and distributes itself
across them; the document that actually answers the question is
`guide_accessibility.md`, whose title is literally "Getting around the region
with limited mobility". The discriminating term is **"limited mobility"**, which
appears in one document out of fourteen — and cosine similarity over a
384-dimension sentence embedding has no mechanism for rewarding an exact rare
term. It can only see that everything is roughly about getting around.

**The pattern.** This is not a one-question problem. It is the general shape of
my corpus: fourteen documents describing nine places using the same seven
section headings. Every question of the form "which place is X" has to
discriminate between nine near-parallel texts, and semantic similarity is
weakest at exactly that job. Q1 shows a milder version — its answer was at rank
2, behind another Halden Bay chunk. The two questions that were hardest are the
two that compare across places; the three that name a place and want a fact
from it were all rank 1.

## The Improvement

**What I changed:** hybrid retrieval. `store.py::search` now runs BM25 keyword
search alongside the existing semantic search and fuses the two rankings with
reciprocal rank fusion (`store.py::_rrf`, k=60). Toggle in `config.HYBRID`; the
semantic-only path is kept so the before/after can be re-run at any time with
`python aggregate.py --no-hybrid`.

**Why I picked it:** the diagnosis names an exact rare term — "limited
mobility", present in one document of fourteen — that cosine similarity cannot
reward and BM25 is built to reward. That is the one-sentence connection, and it
is the only change I made.

**Deliberate design decision: `Result.distance` is still the cosine distance in
both modes.** Fusion happens over the *orderings*, never over the numbers. A
BM25 score and a cosine distance are not on the same scale and no honest
conversion exists between them, but more importantly my relevance gate is
calibrated at 0.70 against cosine — if hybrid mode had written a fused score
into that field, the cutoff would have silently stopped meaning anything and
criterion 3 would have been measuring nothing.

### The bug I shipped first

My first version made retrieval dramatically **worse** — three of five questions
lost the answer completely, criterion 1 would have gone from 5/5 to 2/5. It was
not BM25's fault. I built the BM25 index straight from `collection.query`'s
result and cached it by collection name, not noticing that `query` returns
documents *sorted by distance*, so the ordering is different for every question.
Every question after the first was scoring against an index whose positions
belonged to the previous question's ordering. Rebuilding it from
`collection.get()`, which has a stable order, and mapping into it by chunk id,
fixed it — `store.py::_bm25_index` now carries that explanation in its
docstring so I don't do it again.

I am recording this because the failure looked exactly like a legitimate
negative result. Had I taken the first numbers at face value, I would have
written a confident and completely wrong conclusion that keyword search hurts
this corpus.

### Run Log — After

`python aggregate.py --label after` →
[`results/criteria_2026-09-28_0307_after.md`](results/criteria_2026-09-28_0307_after.md)

Same corpus, same 94 chunks, same top-k 5, same cutoff 0.70. Only retrieval
changed.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | not measured | not measured | not measured | NOT TESTED |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Chunks: start at heading, end on sentence, ≥150 chars | 10 of 10 | pass | pass | pass | MET |
| 5. The named source actually contains the answer | 4 of 5 | not measured | not measured | not measured | NOT TESTED |

**Did it help?**

**It helped the system and it did not help the score, and both halves of that
are worth saying.**

Not one criterion verdict changed, because criterion 1 was already at 5/5 before
I touched anything. A criterion that is at its ceiling cannot register an
improvement. The change is real and it is entirely invisible in the table above,
which is a fact about how I wrote my criteria rather than about the change.

Where it does show is the rank of the answering chunk — the thing the diagnosis
was actually about:

| Question | Rank before | Rank after | Top-ranked chunk before → after |
|---|---|---|---|
| Halden Bay car parks | 2 | **1** | `guide_halden_bay.md#6` → `guide_halden_bay.md#1` |
| Halden Bay cheaper street | 1 | 1 | `guide_eating.md#0` → unchanged |
| Elder Ness flooding | 1 | 1 | `guide_elder_ness.md#1` → unchanged |
| **Limited mobility** | **4** | **3** | `guide_corry_vale.md#2` → **`guide_accessibility.md#0`** |
| Corry Vale food | 1 | 1 | `guide_corry_vale.md#3` → unchanged |

Mean rank of the answering chunk: **1.8 → 1.4**. Nothing regressed.

The most meaningful cell is the bolded one, and it is not the rank. The
limited-mobility question's top result stopped being a Corry Vale section — a
document with no bearing on the question — and became the accessibility guide,
the document that actually answers it. That is the citation-correctness problem
criterion 5 exists for, improved at exactly the question where it was worst. I
cannot show it in criterion 5's row, because criterion 5 needs the model.

One thing the change did that I did not predict. The gate's "best distance" is
the minimum over the *returned* set, and the returned set is now chosen by fused
rank rather than by distance alone, so the semantically-nearest chunk sometimes
isn't in it. Every out-of-corpus distance rose:

| Out-of-corpus question | Before | After |
|---|---|---|
| Capital of Mongolia | 0.8026 | 0.8575 |
| Diesel engine oil | 0.8881 | 0.9190 |
| 1994 World Cup | 0.9753 | 1.0291 |
| Ibuprofen dosage | 0.8350 | 0.8617 |
| For loop in Rust | 0.8365 | 0.8378 |

The in-corpus worst case moved 0.5023 → 0.5113. So the gap the cutoff sits in
widened from [0.5023, 0.8026] to [0.5113, 0.8378], and 0.70 is still comfortably
inside it. This is a benign outcome, but it was luck rather than design: I
changed retrieval and the gate's input quietly changed underneath it. Worth
naming as a coupling between two components I had been thinking of as separate.

## What's Still Broken

**Criteria 2 and 5 are untested.** This is the biggest hole and it is not a
matter of effort. Both need a live model call and there is no `GEMINI_API_KEY`
in this environment. What I would do: add the key, run
`python run_eval.py --label before` and `--label after`, and let `scorer.py`
score them — `names_source` and `citation_correct` are written, committed and
ready, so this is one command and not one more piece of work. I stopped here
because the alternative was to guess at two numbers, and a guessed number in a
run log is worse than an empty cell.

I would expect criterion 5 to be the one that fails. Nine of fourteen documents
end with an identical "Practical notes" paragraph, and nothing in the pipeline
except the title prefix distinguishes their chunks.

**Criterion 3 is untested in the way that matters.** It passed 5/5 against
questions about Mongolia and diesel engines. The failure mode I actually care
about is a question that is off-corpus but adjacent — "is there an airport
shuttle", "what's the best hotel in Marchwood for a business trip" — which would
score far closer to the cutoff than 0.80. I did not swap the questions in
because Milestone 2 is explicit that a target you missed stays where it is and a
criterion is only revised when it could not be *measured*. Mine could be
measured; it was just easy. Changing the question set mid-unit would have made
the before/after incomparable, which is the one thing the unit asks me not to
do. So it stays, with this written next to it.

**The limited-mobility question still needs three slots.** Rank 3 of 5 is better
than rank 4, but it is not rank 1, and `guide_accessibility.md#0` — the
introduction chunk I flagged as weak back in unit 1's Sample Chunks section,
the one that "says a judgement is coming without containing the judgement" — is
still occupying the top slot ahead of the chunk that has the answer. That
prediction was made before any of this was measured and it turned out to be
exactly right. The fix is to merge a document's introduction into its first real
section rather than emitting it. I did not do it because it is a chunking change
and the unit allows one improvement, which I had already spent.

**The BM25 index is rebuilt from the whole collection.** Fine at 94 chunks,
where scoring every chunk costs nothing. On a corpus of 100,000 it would need a
candidate pool instead of a full scan. Noted in `store.py::search` rather than
fixed, because this corpus is 94 chunks.

## What I'd Do Differently

**Criterion 1 is the one I would rewrite, and it's the one that passed.** "The
retrieved chunks include one that contains the answer" is insensitive to rank:
an answer found at rank 5 scores identically to one found at rank 1. It reported
5/5 before and 5/5 after a change that measurably improved retrieval, which
means it could not see the difference between a system on the edge of failing
and one comfortably passing. I would write it as: *for at least 4 of 5
questions, the chunk containing the answer is in the top 3.* That version is
still checkable the same way, would have come out 4/5 before and 5/5 after, and
would have caught the limited-mobility problem in unit 1 rather than unit 2.

**I would also stop predicting which question is hard.** I reasoned carefully in
unit 1 that the sparsely-covered fact would be the weak one and built the 4-of-5
target around it. I was wrong: rarity of coverage turned out not to matter, and
*similarity to other documents* was what mattered. The Corry Vale farm shop is
mentioned twice in the whole corpus and nothing else competes with it, so it is
easy. The accessibility answer competes with eight near-identical "Getting
around" sections, so it is hard. A corpus of parallel documents about parallel
places punishes questions that compare, not questions that are obscure — and I
could have worked that out from reading the documents, which I did do, without
needing the test to tell me.

**Criterion 4 I would make about content rather than structure.** As written it
asks whether my splitter applied its own rule, which it cannot fail without
being broken. Something like *no chunk consists only of a document introduction
with no factual content* would have flagged `guide_accessibility.md#0` — a chunk
I spotted by eye in unit 1, wrote a paragraph about, and then wrote a criterion
that could not detect.

## How I Used AI — unit 2

**3. It fabricated a plausible negative result, and I nearly reported it.** The
hybrid retrieval change came back making things dramatically worse — three of
five questions losing the answer — and the obvious write-up was "keyword search
hurts this corpus, here are the numbers." Before writing that I asked for the
raw BM25 rankings on their own, separately from the fusion. They were *good*:
for the limited-mobility question BM25 put the answering chunk at rank 2 by
itself. A component that ranks well alone and badly in combination points at the
combination, not the component, and the bug was in my caching — I had built the
BM25 index from query-ordered documents and reused it across questions with
different orderings. The lesson is the same one as unit 1's second moment: the
wrong answer was well-formed and internally consistent, and the only thing that
caught it was checking a component against its inputs rather than reading the
summary.

**4. It wanted to mark criteria 2 and 5 as MET.** With no API key, the available
evidence for criterion 2 is that the prompt stamps `[from <filename>]` on every
excerpt and the grounding instruction asks for the filename back twice over — so
the answer would almost certainly name a source. That is a reason to *expect* a
pass and not evidence of one. They are recorded as NOT TESTED. The whole premise
of this unit is that a criterion is a thing you check rather than a thing you
reason your way to, and marking two of five on the strength of an argument would
have been the exact failure the unit is designed to teach against.
