"""
Deciding what counts as correct.

`run_eval.py` picks this file up automatically and uses `judge` to fill the Run
columns. The other functions here exist because my five criteria in
`criteria.md` do not all measure the same thing, and one boolean per run cannot
answer all five:

  criterion 1  is about RETRIEVAL   -> retrieval_hit()
  criterion 2  is about the ANSWER  -> names_source()
  criterion 3  is about the GATE    -> measured by run_eval's own out-of-scope pass
  criterion 4  is about CHUNKS      -> chunks_well_formed(), no question needed
  criterion 5  is about CITATION    -> citation_correct()

`aggregate.py` calls these to build the per-criterion run log.

Why matching on `expects` rather than reading the answers myself: I wrote each
`expects` in unit 1 as a proper noun or a number, before I had seen a single
result, precisely so that this check would not become me grading my own
wording. It is a blunt instrument and it has a known failure mode, recorded
here rather than discovered later: an answer that contains "Fell Street" scores
a pass even if the surrounding sentence is nonsense. I accept that. The
alternative — me deciding case by case whether an answer was good — is the
thing my unit 1 criteria were written to avoid.
"""

import re

import config
from ingest import load_documents

# ─── Helpers ─────────────────────────────────────────────────────────────────

_FILENAME = re.compile(r"[A-Za-z0-9_\-]+\.(?:md|txt)")


def _norm(text: str) -> str:
    """Lowercase and collapse whitespace, so a line break can't fail a match."""
    return re.sub(r"\s+", " ", (text or "")).lower()


def contains(haystack: str, needle: str) -> bool:
    return bool(needle) and _norm(needle) in _norm(haystack)


def filenames_in(answer: str) -> set[str]:
    """Every filename the answer names."""
    return set(_FILENAME.findall(answer or ""))


_docs_cache: dict[str, dict[str, str]] = {}


def _corpus_docs(corpus: str | None = None) -> dict[str, str]:
    """{filename: full text} for the corpus, loaded once."""
    name = corpus or config.CORPUS
    if name not in _docs_cache:
        _docs_cache[name] = {d.source: d.text for d in load_documents(name)}
    return _docs_cache[name]


# ─── Criterion 1: did retrieval bring back the answer? ───────────────────────


def retrieval_hit(expects: str, results) -> bool:
    """True if any retrieved chunk contains the expected phrase.

    This is criterion 1, and it deliberately ignores the answer entirely — it
    is a question about retrieval, and it stays true or false whether or not
    the model is reachable.
    """
    return any(contains(r.text, expects) for r in results)


# ─── Criterion 2: did the answer name a source? ──────────────────────────────


def names_source(answer: str, results) -> bool:
    """True if the answer names at least one real document.

    "Real" matters. An answer that invents `guide_marchwood_hotels.md` has
    named a source and still fails this, because the criterion exists to make
    an answer checkable and an invented filename is not checkable.
    """
    retrieved = {r.source for r in results}
    return bool(filenames_in(answer) & retrieved)


# ─── Criterion 5: was the named source the right one? ────────────────────────


def citation_correct(expects: str, answer: str, corpus: str | None = None) -> bool:
    """True if at least one document the answer names actually contains the fact.

    Criterion 5. Nine of the fourteen `city_guides` documents end with an
    identical "Practical notes" paragraph, so an answer can name a genuine
    retrieved document, look perfectly well-sourced, and still point at the
    wrong town. This opens the files it named and checks.
    """
    named = filenames_in(answer)
    if not named:
        return False
    docs = _corpus_docs(corpus)
    return any(contains(docs.get(f, ""), expects) for f in named)


# ─── Criterion 4: are the chunks well formed? ────────────────────────────────


def chunks_well_formed(chunks, minimum: int | None = None) -> dict:
    """Check every chunk against criterion 4. Returns counts and the offenders.

    Criterion 4 as written in unit 1: every chunk begins at the document title
    or a `##` heading, no chunk ends mid-sentence, no chunk is under 150
    characters. Checked across ALL chunks rather than a sample of ten, which is
    stricter than the criterion asks for — the criterion allowed me to read ten
    by hand, and checking all 94 costs nothing once it is code.
    """
    minimum = config.CHUNK_MIN if minimum is None else minimum

    bad_start = [c.label for c in chunks if not re.match(r"^#{1,2} ", c.text)]
    bad_end = [c.label for c in chunks if not c.text.rstrip().endswith((".", "!", "?"))]
    too_short = [c.label for c in chunks if len(c.text) < minimum]

    return {
        "total": len(chunks),
        "bad_start": bad_start,
        "bad_end": bad_end,
        "too_short": too_short,
        "passed": not (bad_start or bad_end or too_short),
    }


# ─── The headline judgement run_eval.py uses ─────────────────────────────────


def judge(question: str, expects: str, answer: str, results) -> bool:
    """One pass/fail per run, for run_eval.py's Run columns.

    A run passes when the answer carries the expected fact AND names a real
    retrieved document. Both halves are needed: a correct answer with no source
    is not what this system is for, and a well-cited answer that is wrong is
    worse than one that admits it doesn't know.
    """
    return contains(answer, expects) and names_source(answer, results)
