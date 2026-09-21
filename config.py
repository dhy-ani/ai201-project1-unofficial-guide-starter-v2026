"""
Settings for The Unofficial Guide.

Everything you're likely to change lives here, at the top, on purpose.
You'll edit THRESHOLD in Milestone 4 and the chunking numbers in Milestone 3.

Anything you set in your .env file wins over the defaults here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


# ─── The corpus you're working with ──────────────────────────────────────────
# Change this to switch corpora, or pass --corpus on the command line.
# Options are the folder names inside corpora/. See corpora/README.md.

CORPUS = os.getenv("AI201_CORPUS", "city_guides")


# ─── Chunking (Milestone 3) ──────────────────────────────────────────────────
# These are deliberately plain, generic numbers. Milestone 3 is where you
# replace them with numbers that fit the documents you actually read.

# Milestone 3. My chunker splits on markdown section headings, not on a
# character count, so these three mean something slightly different from the
# starter's fixed window — see chunker.py::split_documents.

CHUNK_SIZE = 1100       # ceiling: a section longer than this gets split further
CHUNK_OVERLAP = 150     # characters of the previous piece repeated, but ONLY
                        # when an oversized section has to be split
CHUNK_MIN = 150         # a piece shorter than this is merged, never emitted


# ─── Retrieval (Milestone 4) ─────────────────────────────────────────────────

# Milestone 4. Left at 5, but measured rather than assumed. My hardest question
# ("which town is easiest with limited mobility?") has its answer at rank 4 —
# guide_accessibility.md#1 — so top_k=3 loses it and top_k=4 is the minimum that
# works. 5 keeps one slot of margin. Going to 8 retrieved nothing new and just
# added two more Corry Vale sections that don't answer the question.
TOP_K = 5               # how many chunks to pull back per question

# The relevance gate. If the best chunk is further away than this, the system
# refuses to answer instead of handing the model thin material.
#
# LOWER IS BETTER: 0.3 is a close match, 0.9 is unrelated.
#
# Milestone 4, measured on city_guides at 94 section chunks:
#   in corpus     0.2118  0.2810  0.3121  0.3226  0.5023
#   out of corpus 0.8026  0.8350  0.8365  0.8881  0.9753
# A gap of 0.30 with nothing in it. I am not putting the cutoff at the midpoint
# (0.65) — I am putting it at 0.70, nearer the out-of-corpus side. My five
# questions were written by someone who had read the corpus, so a real user's
# question will do worse than 0.5023, and I would rather refuse a genuine
# question rarely than answer a nonsense one at all. 0.70 still leaves 0.10 of
# margin under the closest out-of-corpus question.
THRESHOLD = 0.70


# ─── Models ──────────────────────────────────────────────────────────────────
# Embeddings run on your own machine and cost no API quota.
# Only generation calls out to a service.

# This is the model Chroma bundles, and leaving it alone is the fast path: it
# downloads about 80 MB from Chroma's own CDN and needs nothing else installed.
#
# Setting it to any other name — unit 2's "try a second embedding model"
# stretch option — switches to loading that model from Hugging Face instead,
# which needs `pip install 'sentence-transformers>=3.4,<3.5'` first. store.py
# says so with a real error message rather than a stack trace if you forget.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MODEL = os.getenv("AI201_MODEL", "gemini-3.5-flash-lite")


# ─── Rate limiting and quota guards ──────────────────────────────────────────
# You should not need to touch these. They exist so that a runaway loop costs
# you a warning instead of your whole day's allowance.

REQUESTS_PER_MINUTE = 30       # outgoing calls the limiter will allow per minute
SESSION_REQUEST_BUDGET = 300   # stop and warn rather than draining the daily quota
MAX_RETRIES = 4                # on 429 / resource-exhausted, with backoff

CACHE_ENABLED = os.getenv("AI201_CACHE", "1") != "0"
CACHE_DIR = ROOT / ".cache"


# ─── Paths ───────────────────────────────────────────────────────────────────

CORPORA_DIR = ROOT / "corpora"
CHROMA_DIR = ROOT / "chroma_db"
RESULTS_DIR = ROOT / "results"


def corpus_path(name: str | None = None) -> Path:
    """Folder holding the documents for a corpus."""
    return CORPORA_DIR / (name or CORPUS) / "documents"


def collection_name(name: str | None = None, variant: str = "default") -> str:
    """
    Name of the vector-store collection for a corpus.

    `variant` lets you index the same corpus two different ways and query both
    without deleting anything — you'll want that in unit 2 when you compare
    chunking strategies.

    Chroma is fussy about collection names: 3 to 63 characters, starting and
    ending with a letter or digit, and nothing but letters, digits, underscores
    and hyphens in between. If you bring your own corpus and name the folder
    something Chroma won't accept, this cleans it up rather than failing.
    """
    import re

    raw = f"{name or CORPUS}__{variant}"
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", raw)
    cleaned = cleaned.strip("_-")          # must start and end alphanumeric
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"c{cleaned}"
    if not cleaned[-1].isalnum():
        cleaned = f"{cleaned}0"
    return cleaned[:63].rstrip("_-") or "collection"
