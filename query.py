"""
query.py — Milestone 5 grounded generation.

Ties retrieval to the Groq LLM. The system prompt forces the model to answer ONLY
from the retrieved review chunks and to refuse when they don't contain the answer.
Source attribution is added programmatically (from chunk metadata), not left to the
model to invent.

CLI:
    python query.py "How do students describe Percy Liang?"
"""

import os
import sys

from dotenv import load_dotenv
from groq import Groq

from embed_store import retrieve

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
TOP_K = 5

SYSTEM_PROMPT = (
    "You are The Unofficial Guide, answering questions about university CS professors "
    "using ONLY the student reviews provided in the context.\n"
    "Rules:\n"
    "1. Answer using ONLY information in the provided reviews. Do not use any outside "
    "or prior knowledge about these professors.\n"
    "2. If the reviews do not contain enough information to answer, reply exactly: "
    "\"I don't have enough information on that.\"\n"
    "3. When reviews disagree, reflect the range of opinions rather than picking one.\n"
    "4. Be concise (2-4 sentences). Do not invent professors, courses, or quotes."
)


def _build_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        md = c["metadata"]
        blocks.append(f"[Review {i} | source: {md['source']}]\n{c['text']}")
    return "\n\n".join(blocks)


def ask(question: str, k: int = TOP_K) -> dict:
    """Retrieve, generate a grounded answer, and attach source attribution.

    Returns {answer, sources, chunks}.
    """
    chunks = retrieve(question, k=k)
    context = _build_context(chunks)

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context (student reviews):\n\n{context}\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # Source attribution comes from metadata, guaranteed — not from the LLM.
    refused = "don't have enough information" in answer.lower()
    sources = []
    if not refused:
        seen = set()
        for c in chunks:
            src = c["metadata"]["source"]
            if src not in seen:
                seen.add(src)
                sources.append(src)

    return {"answer": answer, "sources": sources, "chunks": chunks}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How do students describe Percy Liang as a professor?"
    result = ask(q)
    print(f"Q: {q}\n")
    print(f"A: {result['answer']}\n")
    if result["sources"]:
        print("Sources:")
        for s in result["sources"]:
            print(f"  • {s}")
    else:
        print("Sources: (none — system declined to answer)")
