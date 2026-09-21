# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:** Four of my five questions ask about facts that `city_guides`
repeats in three or four documents — the 10am Halden Bay parking cutoff turns up
in the town guide, the transport guide and the seasons guide. Those should be
easy to hit. The fifth asks where to buy food in Corry Vale, and the farm shop is
named in exactly two documents out of fourteen, with no repetition to help
retrieval find it. I am setting the target at 4 of 5 because I expect that one to
be the one that fails, and I would rather name it in advance than explain it
afterwards. Five of five would mean the corpus never has a thin spot, which I
already know is false.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:** This is the one criterion I hold at 5 of 5, because nothing
about the corpus makes it hard — it is a property of my own code rather than of
the documents. `build_prompt` in `generate.py` stamps `[from <filename>]` above
every excerpt and the grounding instruction asks for the filename back, and a
refusal never reaches the model at all. So the only way to miss this is for the
model to ignore an instruction it was given in two places. If that happens even
once in fifteen runs I want it recorded as a miss rather than rounded away,
because an answer with no source is exactly the kind of confident, unattributable
output this whole project exists to prevent.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:** The two groups did not overlap, and it was not close. At
`top_k=5` on my 94 section chunks the five in-corpus questions came back at
0.2118, 0.2810, 0.3121, 0.3226 and 0.5023, and the five `OUT_OF_SCOPE` questions
at 0.8026, 0.8350, 0.8365, 0.8881 and 0.9753 — a gap of 0.30 with nothing
anywhere in it. I set `THRESHOLD = 0.70` inside that gap and both groups fall
cleanly on the right side of it.

Given that, 4 of 5 looks conservative, and I thought about writing 5 of 5.
I am keeping 4 of 5 for one reason: the target has to survive questions I have
not thought of yet. `OUT_OF_SCOPE` asks about Mongolia, diesel engines and Rust,
which are about as far from a regional travel guide as a question can get, and
0.80 is what that distance looks like. A question that is off-corpus but
*adjacent* — "what's the best hotel in Marchwood for a business trip", "is there
a train to the airport" — would score far closer than 0.80 and is exactly the
kind the gate might wave through. My five are the easy version of this test, so I
am not going to claim a perfect score against the easy version.

---

## 4. Chunks begin and end where the documents do

Across all the chunks my chunker produces from `city_guides`, every chunk begins
either at the document's title line or at a `##` section heading, no chunk ends
in the middle of a sentence, and no chunk is shorter than 150 characters.

I check this by running `python app.py chunks -n 10` and reading all ten: ten of
ten must start at a heading and end on a full stop. The 150-character floor I
check against the whole corpus, from the "shortest" figure that
`chunker.py::describe` prints after indexing — it covers every chunk, not a
sample.

**Why this target:** This is 10 of 10 and not 8 of 10 because it is a structural
guarantee, not a judgement call. If my chunker splits on headings then a chunk
that starts mid-sentence is a bug in the splitter, and one counterexample means
the rule is not being applied — there is no reason for it to be true 80% of the
time. The starter gave me the counterexamples to aim at: it cut
`guide_kestrelford.md` so that chunk 0 ended on the text `## Eat and drin` and
chunk 3 was a 60-character orphan, and across the corpus its shortest chunk was
24 characters. The 150-character floor is set just above the shortest real
section in the corpus rather than at a round number: the thinnest `##` section in
`city_guides` is Elder Ness's "Eat and drink" at a bit over 200 characters, so
anything under 150 is not a section at all, it is wreckage.

---

## 5. The named source actually contains the answer

For at least 4 of my 5 test questions, the document the answer names is a
document that genuinely contains that answer — not merely one of the five
documents that happened to be retrieved.

I check this by reading the answer's filename and then opening that file to
confirm the fact is in it.

**Why this target:** Criterion 2 only asks that *a* source gets named, and a
system can pass it while citing the wrong file every time. That is a real risk in
this corpus rather than a hypothetical one: nine of the fourteen guides end with
a word-for-word identical "Practical notes" paragraph about cash, mobile coverage
and the nearest hospital. Those nine chunks are near-identical vectors, so a
question that lands near any of them can be answered from Kestrelford's copy and
cited to Pellew Sands, and the answer would look perfectly well-sourced. I care
about this more than about the answers being fluent, because a wrong citation is
worse than no citation — it invites someone to go and check, and rewards them for
checking with the wrong file. I set it at 4 of 5 rather than 5 of 5 to match
criterion 1: a question whose answer was never retrieved cannot have a correctly
named source either, so the Corry Vale question can plausibly cost me this one
too.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->
