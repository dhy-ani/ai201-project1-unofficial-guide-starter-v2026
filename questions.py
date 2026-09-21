"""
Your test questions.

Milestone 2 asks you to write five questions your system should be able to
answer from your corpus, specific enough to have a right answer.

  ✗ "What are good dining halls?"          — no right answer
  ✓ "What do students say about wait times at Commons during lunch?"

Fill in `QUESTIONS` below. `expects` is a word or short phrase you'd expect a
correct answer to contain — you'll use it in unit 2 when you build a scorer,
and having written it now means you decided what "correct" meant before you saw
any results.

`OUT_OF_SCOPE` holds five questions your documents clearly don't cover. You
need these in Milestone 4 to find where your relevance cutoff belongs, and
again in unit 2, where `run_eval.py` runs them through the gate and writes what
happened into your run log — that's the evidence for criterion 3.

Swap them for your own if you like. Keep five of them either way: criterion 3
names a target of "4 of 5", and four of three is not a thing.
"""

QUESTIONS = [
    # Corpus: city_guides. Each `expects` is a proper noun or a number, because
    # those are the parts of an answer I can check the same way twice. A phrase
    # like "quite early" would have me grading my own wording in unit 2.
    {
        "question": "What time do the car parks in Halden Bay fill up on a summer weekend?",
        "expects": "10am",
    },
    {
        "question": "Which street in Halden Bay has cheaper food than the harbour front?",
        "expects": "Fell Street",
    },
    {
        "question": "How often does the road out to Elder Ness flood?",
        "expects": "six times",
    },
    {
        "question": "Which town in the region is easiest to get around with limited mobility?",
        "expects": "Thornby Wells",
    },
    # The hard one, on purpose. "10am" and "1963" are repeated in three or four
    # documents each; the Corry Vale farm shop is named in exactly two
    # (guide_corry_vale.md and guide_eating.md). If one question misses, I
    # expect it to be this one.
    {
        "question": "If I am staying in Corry Vale for a few days, where can I buy food?",
        "expects": "farm shop",
    },
]

# Questions from a different world entirely. Your gate should refuse all five.
#
# There are five of these because criterion 3 in criteria.md names a target of
# "at least 4 of 5" — you need five things to try before you can report 4 of 5.
# `run_eval.py` runs these through retrieval and the gate on every eval and
# records what happened, so criterion 3 has evidence in the run log alongside
# the others. They cost no model calls: a refusal never reaches the model.
OUT_OF_SCOPE = [
    "What is the capital of Mongolia?",
    "How do I change the oil in a diesel engine?",
    "Who won the 1994 World Cup?",
    "What is the recommended dosage of ibuprofen for a headache?",
    "How do I write a for loop in Rust?",
]


def answered() -> list[dict]:
    """The questions you've actually filled in."""
    return [q for q in QUESTIONS if q.get("question", "").strip()]
