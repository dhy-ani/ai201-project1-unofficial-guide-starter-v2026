# The Unofficial Guide

**Dhyan** · corpus: `city_guides`

---

# Unit 1

## What This Does

<!-- Three or four sentences. Which corpus you picked, and the kinds of
     questions your system answers. Write it for someone who has never seen
     this repo.

     Milestone 5. -->

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

**The thing I changed my mind about.** My first version emitted the bare section
and nothing else, and it looked fine until I read Halden Bay's "Getting around"
on its own:

> The town is small enough to cross in fifteen minutes but is built on three
> levels connected by stepped lanes... The harbour front is level; everything
> above it is not.

Nothing in it says Halden Bay. A section body in this corpus almost never names
its own town, because the title at the top of the file already did. Cut loose
from the file, that chunk is unusable twice over: retrieval has nothing to match
the word "Halden" against, and an answer built from it has nothing to attribute.
So every chunk now carries `# <document title>` at the top. That is why the
floor is 150 rather than the ~100 the raw sections would have allowed — the
title line costs characters.

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

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:**

**Answer:**

```
```

**My relevance cutoff:**

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

| Question | In corpus? | Best distance |
|---|---|---|
|  |  |  |

## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1.**

**2.**

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
