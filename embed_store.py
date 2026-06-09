"""
embed_store.py — Milestone 4 embedding + vector store + retrieval.

Embeds every chunk with all-MiniLM-L6-v2 and stores them in a local ChromaDB
collection with source metadata. Provides retrieve() for semantic search.

Build/refresh the index:
    python embed_store.py --build
Test retrieval on the eval questions:
    python embed_store.py --test
"""

import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from chunk_documents import load_chunks

EMBED_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "professor_reviews"
CHROMA_DIR = str(Path(__file__).parent / "chroma_db")

_model = None
_collection = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def get_collection():
    """Return the persistent Chroma collection (created if missing)."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # cosine distance, range ~0..2
        )
    return _collection


def build_index() -> int:
    """Embed all chunks and (re)load them into ChromaDB. Returns chunk count."""
    chunks = load_chunks()
    model = get_model()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    # Start clean so re-running doesn't duplicate or stale-out entries.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    print(f"Embedding {len(texts)} chunks with {EMBED_MODEL}...")
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=metadatas,
    )
    print(f"Stored {collection.count()} chunks in ChromaDB at {CHROMA_DIR}")
    return collection.count()


def retrieve(query: str, k: int = 5) -> list[dict]:
    """Return the top-k chunks for a query, each with text, metadata, distance."""
    model = get_model()
    collection = get_collection()
    q_emb = model.encode([query], normalize_embeddings=True)[0].tolist()
    res = collection.query(query_embeddings=[q_emb], n_results=k)

    results = []
    for doc, md, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({"text": doc, "metadata": md, "distance": dist})
    return results


# The 5 evaluation questions from planning.md (used by --test).
EVAL_QUESTIONS = [
    "What do students say about Andrew Ng's machine learning courses?",
    "How do students describe Percy Liang as a professor?",
    "Do students find David Malan's CS50 lectures clear, or too lecture-heavy?",
    "Which CS professor is described as funny or like a stand-up comedian?",
    "Do any reviews mention group projects or team assignments?",
]


def test_retrieval(k: int = 5):
    for q in EVAL_QUESTIONS:
        print(f"\n{'=' * 78}\nQ: {q}")
        for r in retrieve(q, k=k):
            md = r["metadata"]
            print(f"  [dist {r['distance']:.3f}] {md['professor']} ({md['source']})")
            print(f"      {r['text'][:160]}{'...' if len(r['text']) > 160 else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="(re)build the index")
    parser.add_argument("--test", action="store_true", help="test retrieval on eval Qs")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    if args.build:
        build_index()
    if args.test:
        test_retrieval(k=args.k)
    if not args.build and not args.test:
        parser.print_help()
