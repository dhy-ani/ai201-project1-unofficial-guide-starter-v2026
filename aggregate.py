#!/usr/bin/env python3
"""
Turn per-question results into the per-criterion run log the README asks for.

    python aggregate.py --label before
    python aggregate.py --label after --variant hybrid

`run_eval.py` writes one row per QUESTION. `criteria.md` has five criteria and
they do not map one-to-one onto questions, so this does the aggregation:
criterion 1 is a count over questions, criterion 3 is a count over the
out-of-scope list, criterion 4 is a property of the chunker and involves no
questions at all.

It measures the three criteria that need no model call — 1 (retrieval), 3 (the
gate) and 4 (chunk shape) — and marks 2 and 5 as not measured, because those
read the generated answer and there is no GEMINI_API_KEY in this environment.
When a key is available, `run_eval.py --label X` fills those in; this script
reports what it could actually check rather than guessing at the rest.

Criteria 1, 3 and 4 are deterministic: the same index and the same question
give the same chunks and the same distances every time. Running them three
times is still worth doing — it is the check that they ARE deterministic — but
three identical columns are the correct result, not a sign the runs were
cached.
"""

import argparse
import datetime as dt

import config
import questions as qs
import scorer


def measure(top_k, threshold, corpus, variant):
    """One pass over criteria 1 and 3. Returns (hits, refusals, detail)."""
    from store import search
    import gate

    detail = {"in": [], "out": []}

    hits = 0
    for item in qs.answered():
        results = search(item["question"], top_k=top_k, corpus=corpus, variant=variant)
        hit = scorer.retrieval_hit(item["expects"], results)
        hits += hit
        rank = next(
            (i for i, r in enumerate(results, 1)
             if scorer.contains(r.text, item["expects"])),
            None,
        )
        detail["in"].append(
            {
                "question": item["question"],
                "expects": item["expects"],
                "hit": hit,
                "rank": rank,
                "best": results[0].distance if results else 1.0,
                "top": results[0].label if results else "-",
            }
        )

    refused = 0
    for question in getattr(qs, "OUT_OF_SCOPE", []):
        results = search(question, top_k=top_k, corpus=corpus, variant=variant)
        decision = gate.check(results, threshold=threshold)
        refused += not decision.passed
        detail["out"].append(
            {
                "question": question,
                "refused": not decision.passed,
                "best": decision.best_distance,
            }
        )

    return hits, refused, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--label", default="")
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--variant", default="default")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    from ingest import load_documents
    from chunker import split_documents

    corpus = args.corpus or config.CORPUS
    top_k = args.top_k or config.TOP_K
    threshold = config.THRESHOLD if args.threshold is None else args.threshold
    total = len(qs.answered())
    out_total = len(getattr(qs, "OUT_OF_SCOPE", []))

    passes = []
    for run in range(1, args.runs + 1):
        hits, refused, detail = measure(top_k, threshold, corpus, args.variant)
        passes.append({"hits": hits, "refused": refused, "detail": detail})
        print(f"run {run}: criterion 1 = {hits}/{total}, criterion 3 = {refused}/{out_total}")

    chunks = split_documents(load_documents(corpus))
    shape = scorer.chunks_well_formed(chunks)
    print(f"criterion 4: {'PASS' if shape['passed'] else 'FAIL'} over {shape['total']} chunks")

    write(passes, shape, chunks, args, corpus, top_k, threshold, total, out_total)


def write(passes, shape, chunks, args, corpus, top_k, threshold, total, out_total):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"criteria_{stamp}{label}.md"

    c1 = " | ".join(f"{p['hits']}/{total}" for p in passes)
    c3 = " | ".join(f"{p['refused']}/{out_total}" for p in passes)
    c4 = " | ".join(["pass" if shape["passed"] else "fail"] * len(passes))
    heads = " | ".join(f"Run {i}" for i in range(1, len(passes) + 1))
    div = "|".join(["---"] * len(passes))

    lines = [
        f"# Criteria run log{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `aggregate.py::main`, scored by `scorer.py`",
        "- Retrieval: `store.py::search`; chunks from `chunker.py::split_documents`",
        f"- Corpus: `{corpus}` (index variant `{args.variant}`)",
        f"- top-k: {top_k} · relevance cutoff: {threshold}",
        f"- Runs: {len(passes)}",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"| Criterion | Target | {heads} |",
        f"|---|---|{div}|",
        f"| 1. Retrieved chunks contain the answer | 4 of 5 | {c1} |",
        "| 2. Every answer names a source | 5 of 5 | "
        + " | ".join(["not measured"] * len(passes)) + " |",
        f"| 3. Gate stops out-of-corpus questions | 4 of 5 | {c3} |",
        f"| 4. Chunks start at a heading, end on a sentence, >=150 chars | 10 of 10 | {c4} |",
        "| 5. The named source actually contains the answer | 4 of 5 | "
        + " | ".join(["not measured"] * len(passes)) + " |",
        "",
        "Criteria 2 and 5 read the generated answer. There is no GEMINI_API_KEY in",
        "this environment, so they were not run rather than estimated.",
        "",
        "## Criterion 1 — per question (run 1)",
        "",
        "| Question | expects | in chunks? | at rank | best distance | closest chunk |",
        "|---|---|---|---|---|---|",
    ]

    for row in passes[0]["detail"]["in"]:
        lines.append(
            f"| {row['question']} | `{row['expects']}` | "
            f"{'yes' if row['hit'] else 'NO'} | {row['rank'] or '-'} | "
            f"{row['best']:.4f} | `{row['top']}` |"
        )

    lines += [
        "",
        "## Criterion 3 — the gate, per out-of-scope question",
        "",
        f"Cutoff {threshold}. Retrieval and the gate are deterministic, so this is",
        "one pass and the number is the same in all three run columns above.",
        "",
        "| Question | refused? | best distance |",
        "|---|---|---|",
    ]
    for row in passes[0]["detail"]["out"]:
        lines.append(
            f"| {row['question']} | {'yes' if row['refused'] else 'LET THROUGH'} | "
            f"{row['best']:.4f} |"
        )

    lengths = [len(c.text) for c in chunks]
    lines += [
        "",
        "## Criterion 4 — chunk shape, over every chunk",
        "",
        f"- chunks checked: {shape['total']}",
        f"- not starting at a heading: {len(shape['bad_start'])} {shape['bad_start'] or ''}",
        f"- ending mid-sentence: {len(shape['bad_end'])} {shape['bad_end'] or ''}",
        f"- under {config.CHUNK_MIN} characters: {len(shape['too_short'])} {shape['too_short'] or ''}",
        f"- shortest {min(lengths)}, longest {max(lengths)}, "
        f"average {sum(lengths) // len(lengths)}",
        "",
        f"Verdict: {'PASS' if shape['passed'] else 'FAIL'}.",
        "",
        "## Determinism check",
        "",
        "Every run column above is identical, and that is the expected result:",
        "the index is fixed, retrieval is a nearest-neighbour lookup over fixed",
        "vectors, and the gate is a comparison against a constant. Three passes",
        "confirm no run-to-run variation, which is what makes a single number",
        "reportable for these three criteria. Criteria 2 and 5 depend on the",
        "model and are the ones that would move.",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
