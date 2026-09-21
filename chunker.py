"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


# ─── My chunker (Milestone 3) ────────────────────────────────────────────────
#
# `city_guides` is fourteen markdown files of 1–3k characters. Every one of them
# is a title line, sometimes an introductory paragraph, and then a run of `## `
# sections with names like "Getting there", "Eat and drink", "When to go". The
# author already decided where one thought stops and the next begins. The
# starter's 800-character window ignores those decisions and cuts wherever it
# happens to land — `guide_kestrelford.md#0` ends on the text `## Eat and drin`,
# and `#3` is a 60-character orphan.
#
# So: split on the headings the author wrote, and treat a section as one chunk.
# Measured across the corpus, sections run 23 to 711 characters with a median of
# 284 — small enough that a whole section fits comfortably in a chunk.
#
# One thing does have to be added rather than merely preserved. A section body
# almost never names its own town: Halden Bay's "Getting around" says "The
# harbour front is level; everything above it is not" without saying where. Cut
# loose from its file that sentence is unusable, both for retrieval (nothing to
# match "Halden Bay" against) and for the answer (nothing to attribute). So
# every chunk carries its document's title line at the top. That also pulls the
# nine word-for-word identical "Practical notes" paragraphs apart from each
# other, which is the thing criterion 5 is about.

_SECTION_BREAK = re.compile(r"\n(?=## )")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


def _document_title(text: str) -> str:
    """The `# Heading` on the first line, without the hash. "" if there isn't one."""
    first = text.lstrip().split("\n", 1)[0].strip()
    match = re.match(r"^#\s+(.+?)\s*$", first)
    return match.group(1) if match else ""


def _overlap_tail(text: str, budget: int) -> str:
    """The last whole sentences of `text`, up to `budget` characters.

    Whole sentences rather than a raw character slice: the point of the overlap
    is to stop a thought being orphaned, and half a sentence is the thing I am
    trying to get rid of.
    """
    tail: list[str] = []
    total = 0
    for sentence in reversed(_SENTENCE_BREAK.split(text.strip())):
        if tail and total + len(sentence) > budget:
            break
        tail.insert(0, sentence)
        total += len(sentence) + 1
    return " ".join(tail)


def _pack(pieces: list[str], header: str, max_size: int, overlap: int) -> list[str]:
    """Group `pieces` (paragraphs) into chunks of at most `max_size`.

    Only reached when a single section is longer than the ceiling. No section in
    `city_guides` is, but a corpus with a 4,000-character section would fall in
    here, and a chunker that silently emitted a 4,000-character chunk would be
    the "too big" failure the brief warns about.
    """
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if current and len(header) + len(candidate) > max_size:
            chunks.append(current)
            carried = _overlap_tail(current, overlap) if overlap else ""
            current = f"{carried}\n\n{piece}" if carried else piece
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split each document at its `## ` section headings, one section per chunk.

    Every chunk is stamped with its document's title line, so a section that
    never names its own town still says which town it is about.

    Rules, in the order they apply:
      1. Cut at every `## ` heading. The text before the first one — the title
         and any introduction — is its own chunk.
      2. Prepend `# <document title>` to every chunk that doesn't already start
         with it.
      3. A chunk still over `config.CHUNK_SIZE` is split again at paragraph
         breaks, repeating the last whole sentences of the previous piece as
         `config.CHUNK_OVERLAP` characters of context.
      4. A piece under `config.CHUNK_MIN` is merged into the next one rather
         than emitted. This is what stops a bare title line becoming a chunk:
         four of the fourteen guides open with a heading and no introduction.
      5. A document with no `## ` headings at all falls through to paragraph
         packing, so this doesn't break on a corpus that isn't markdown.
    """
    max_size = config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP
    minimum = config.CHUNK_MIN

    chunks: list[Chunk] = []

    for doc in documents:
        title = _document_title(doc.text)
        header = f"# {title}\n\n" if title else ""

        sections = [s.strip() for s in _SECTION_BREAK.split(doc.text) if s.strip()]

        if len(sections) == 1:
            # Rule 5: nothing to split on. Pack paragraphs instead.
            body = sections[0]
            if header and body.startswith(header.strip()):
                body = body[len(header.strip()) :].strip()
            paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
            bodies = _pack(paragraphs, header, max_size, overlap)
        else:
            bodies = []
            for section in sections:
                if header and section.startswith(header.strip()):
                    # The preamble already carries the title line.
                    section = section[len(header.strip()) :].strip()
                    if not section:
                        continue  # rule 4: a title line on its own is not a chunk
                if len(header) + len(section) <= max_size:
                    bodies.append(section)
                    continue
                # Rule 3: an oversized section, split at paragraph breaks with
                # the heading repeated on every piece so none of them is
                # anonymous.
                lines = section.split("\n", 1)
                heading, rest = lines[0], (lines[1] if len(lines) > 1 else "")
                paragraphs = [p.strip() for p in rest.split("\n\n") if p.strip()]
                for piece in _pack(paragraphs, f"{header}{heading}\n\n", max_size, overlap):
                    bodies.append(f"{heading}\n\n{piece}")

        # Rule 4, applied last: merge anything still too short forwards, and if
        # the final piece is the short one, merge it backwards instead.
        merged: list[str] = []
        for body in bodies:
            if merged and len(header) + len(merged[-1]) < minimum:
                merged[-1] = f"{merged[-1]}\n\n{body}"
            else:
                merged.append(body)
        if len(merged) > 1 and len(header) + len(merged[-1]) < minimum:
            merged[-2] = f"{merged[-2]}\n\n{merged.pop()}"

        for index, body in enumerate(merged):
            chunks.append(
                Chunk(
                    text=f"{header}{body}" if header else body,
                    source=doc.source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
