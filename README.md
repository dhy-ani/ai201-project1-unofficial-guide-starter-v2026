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

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
