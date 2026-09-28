"""
Stages 3 and 4 of the pipeline: embedding chunks and retrieving them.

Three things in here are worth knowing about, because they'd quietly break the
rest of the project if they were wrong:

1. The Chroma collection is created with cosine distance, explicitly. Chroma
   defaults to squared L2, and the 0.6 threshold the course uses is calibrated
   against cosine. Getting this wrong makes every distance number meaningless.

2. `search` returns the distance alongside each chunk. Milestone 4 has you
   compare distances, so they have to be visible.

3. The embedding model is the one Chroma bundles, not one loaded through
   `sentence-transformers`. It is the same model — `all-MiniLM-L6-v2`, 384
   dimensions — but it arrives as an ONNX build from Chroma's own CDN, so the
   install needs neither PyTorch nor a reachable Hugging Face. See `_embedder`.
"""

import os
import re
import shutil
from dataclasses import dataclass

# Must be set BEFORE chromadb is imported. Without it, some Chroma versions
# print "Failed to send telemetry event ..." on every single call — which looks
# exactly like a real error, isn't one, and cost a previous cohort a lot of
# confused help-channel messages.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb  # noqa: E402

import config
from chunker import Chunk


@dataclass
class Result:
    """One retrieved chunk and how far it was from the question."""

    text: str
    source: str
    label: str
    distance: float   # LOWER IS BETTER. 0.3 is close, 0.9 is unrelated.
    produced_by: str


_model = None

# The model Chroma bundles. Anything else in config.EMBEDDING_MODEL means
# "fetch that one from Hugging Face instead" — see `_embedder`.
BUNDLED_MODEL = "all-MiniLM-L6-v2"


class _OnnxEmbedder:
    """
    Chroma's built-in embedder, wrapped to look like the other two.

    Chroma's embedding functions are called directly and hand back numpy
    arrays. The rest of this file wants `.encode(texts)`, so the adapter lives
    here rather than making every caller care which embedder it got.
    """

    def __init__(self):
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self._ef = ONNXMiniLM_L6_V2()

    def encode(self, texts, show_progress_bar: bool = False):
        return [vector.tolist() for vector in self._ef(list(texts))]


def _sentence_transformer(name: str):
    """
    The escape hatch: any model that isn't the bundled one.

    Unit 2's "try a second embedding model" stretch option comes through here,
    and so does anything you set `EMBEDDING_MODEL` to. This path *does* need
    `sentence-transformers` and a reachable Hugging Face, neither of which the
    default install has — which is the whole point of the default install.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            f"config.EMBEDDING_MODEL is set to {name!r}, which isn't the model "
            f"Chroma bundles ({BUNDLED_MODEL!r}), so it has to be downloaded "
            f"from Hugging Face.\n"
            f"Install the optional dependency first:\n"
            f"    pip install 'sentence-transformers>=3.4,<3.5'\n"
            f"Or set EMBEDDING_MODEL back to {BUNDLED_MODEL!r}."
        ) from exc

    return SentenceTransformer(name)


def _embedder():
    """
    Load the embedding model once and keep it.

    First call is slow — it downloads about 80 MB. That's why setup happens
    before class.
    """
    global _model

    if _model is not None:
        return _model

    # Used only by this repo's own smoke test, which runs where no model can be
    # downloaded at all. Never set this yourself.
    if os.getenv("AI201_FAKE_EMBEDDINGS") == "1":
        from _smoke_embedder import FakeEmbedder

        _model = FakeEmbedder()
    elif config.EMBEDDING_MODEL == BUNDLED_MODEL:
        _model = _OnnxEmbedder()
    else:
        _model = _sentence_transformer(config.EMBEDDING_MODEL)

    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Turn text into vectors. Runs on your machine, costs no API quota."""
    vectors = _embedder().encode(texts, show_progress_bar=False)
    # sentence-transformers and the smoke stand-in return something with a
    # .tolist(); _OnnxEmbedder has already done that conversion itself.
    return vectors.tolist() if hasattr(vectors, "tolist") else vectors


def _client():
    return chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_index(
    chunks: list[Chunk],
    corpus: str | None = None,
    variant: str = "default",
) -> int:
    """
    Embed every chunk and store it.

    `variant` lets you keep more than one index of the same corpus at the same
    time. In unit 2, when you compare two chunking strategies, index the second
    one as variant="v2" and you can query both instead of deleting the first
    and starting over.
    """
    name = config.collection_name(corpus, variant)
    client = _client()

    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        # ⚠️ Do not remove. Chroma defaults to squared L2, and every distance
        # number in this course assumes cosine.
        metadata={"hnsw:space": "cosine"},
    )

    batch = 256
    for start in range(0, len(chunks), batch):
        window = chunks[start : start + batch]
        collection.add(
            ids=[f"{c.source}#{c.index}" for c in window],
            documents=[c.text for c in window],
            embeddings=embed([c.text for c in window]),
            metadatas=[
                {"source": c.source, "index": c.index, "produced_by": c.produced_by}
                for c in window
            ],
        )

    return len(chunks)


# ─── Keyword search, for the hybrid path (unit 2's improvement) ──────────────

_TOKEN = re.compile(r"[a-z0-9]+")
_bm25_cache: dict[str, tuple] = {}


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric runs.

    Deliberately crude, and deliberately not stripping digits: three of my five
    questions turn on a number or a time ("10am", "six times"), and a tokenizer
    that threw those away would remove the main reason for adding BM25.
    """
    return _TOKEN.findall(text.lower())


def _bm25_index(collection, name: str):
    """BM25 over the collection, in a STABLE document order, built once.

    The stable order matters more than it looks. `collection.query` returns
    documents sorted by distance, so the order is different for every question.
    My first version built BM25 straight from the query result and cached it by
    collection name — which meant every question after the first was scoring
    against an index whose positions belonged to the previous question's
    ordering. Retrieval got dramatically worse and the cause was not BM25 at
    all. `collection.get()` returns a fixed order, so positions mean the same
    thing on every call, and the caller maps into it by chunk id.
    """
    if name not in _bm25_cache:
        from rank_bm25 import BM25Okapi

        data = collection.get()
        position = {chunk_id: i for i, chunk_id in enumerate(data["ids"])}
        index = BM25Okapi([_tokenize(d) for d in data["documents"]])
        _bm25_cache[name] = (index, position)
    return _bm25_cache[name]


def _rrf(rankings: list[list[int]], k: int) -> dict[int, float]:
    """Reciprocal rank fusion over several rankings of the same items.

    Each ranking is a list of item indices, best first. An item's score is the
    sum of 1/(k + rank) across the rankings it appears in. Chosen over adding
    the raw scores together because a cosine distance and a BM25 score are not
    on the same scale and never will be — fusing the ORDERINGS sidesteps having
    to invent a conversion between them.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return scores


def search(
    question: str,
    top_k: int | None = None,
    corpus: str | None = None,
    variant: str = "default",
    hybrid: bool | None = None,
) -> list[Result]:
    """
    Retrieve the chunks closest to a question.

    With `hybrid` on (the default, `config.HYBRID`), this is semantic search and
    BM25 keyword search fused by reciprocal rank. With it off, it is the unit 1
    behaviour: semantic only.

    Returns them best-first. `distance` is ALWAYS the cosine distance, in both
    modes. That is on purpose — the relevance gate is calibrated against cosine
    at 0.70, and if hybrid mode returned a fused score in that field the cutoff
    would silently stop meaning anything.
    """
    top_k = top_k or config.TOP_K
    hybrid = config.HYBRID if hybrid is None else hybrid
    name = config.collection_name(corpus, variant)

    try:
        collection = _client().get_collection(name)
    except Exception as exc:
        raise RuntimeError(
            f"No index called '{name}'. Run `python app.py index` first."
        ) from exc

    count = collection.count()

    # Semantic pass. In hybrid mode we score every chunk rather than the top-k,
    # so that a chunk BM25 likes still arrives with its true cosine distance
    # attached and the gate keeps working. Fine at 94 chunks; on a corpus of
    # 100,000 this would need a candidate pool instead.
    raw = collection.query(
        query_embeddings=embed([question]),
        n_results=count if hybrid else min(top_k, count),
    )

    chunk_ids = raw["ids"][0]
    docs = raw["documents"][0]
    metas = raw["metadatas"][0]
    distances = raw["distances"][0]

    if hybrid:
        # Everything below is in QUERY-RESULT positions: 0 is the nearest chunk.
        semantic_ranking = list(range(len(docs)))

        index, position = _bm25_index(collection, name)
        scores = index.get_scores(_tokenize(question))
        # Map each query-result row onto its score in the stable BM25 ordering.
        by_id = [scores[position[cid]] for cid in chunk_ids]
        keyword_ranking = sorted(range(len(docs)), key=lambda i: -by_id[i])

        fused = _rrf([semantic_ranking, keyword_ranking], config.RRF_K)
        order = sorted(fused, key=lambda i: -fused[i])[:top_k]
        # Present them by cosine distance, so the printed list still reads
        # nearest-first and gate.check's min() is the first row.
        order.sort(key=lambda i: distances[i])
    else:
        order = list(range(min(top_k, len(docs))))

    results: list[Result] = []
    for i in order:
        meta = metas[i]
        results.append(
            Result(
                text=docs[i],
                source=str(meta.get("source", "unknown")),
                label=f"{meta.get('source', 'unknown')}#{meta.get('index', 0)}",
                distance=float(distances[i]),
                produced_by=str(meta.get("produced_by", "unknown")),
            )
        )
    return results


def index_exists(corpus: str | None = None, variant: str = "default") -> bool:
    """Is there an index here to search, without searching it?

    `serve.py`'s health check asks this. It deliberately does not embed
    anything: loading the embedding model takes 80 MB and a few seconds, and a
    health check that heavy is a health check nobody can afford to call.
    """
    try:
        collection = _client().get_collection(config.collection_name(corpus, variant))
        return collection.count() > 0
    except Exception:
        return False


def reset():
    """Delete every index. Occasionally the fastest way out of a mess."""
    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)
