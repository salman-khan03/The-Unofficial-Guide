"""
chunk_documents.py — Milestone 3 chunking.

Loads the per-professor review files produced by scrape_rmp.py and splits them into
one chunk per student review. Each chunk is prepended with professor/school/course
metadata so even one-line reviews carry enough context to be retrievable, and the
templated "Clear lectures, fair exams." seed review RMP returns is dropped as noise.

Run directly to inspect chunks:
    python chunk_documents.py
Or import:
    from chunk_documents import load_chunks
"""

import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "documents"

# RMP returns this identical placeholder review for every professor — pure noise.
SEED_REVIEW = "clear lectures, fair exams."

# Lines inside a review block that are metadata, not the student's comment.
META_PREFIXES = ("Quality:", "Tags:")

REVIEW_HEADER = re.compile(r"^\[Review \d+\]\s*Course:\s*(?P<course>.*?)\s*\|", re.IGNORECASE)
SEPARATOR = re.compile(r"^-{5,}$")


def _parse_header(lines: list[str]) -> dict:
    """Pull professor + school from the file's top header lines."""
    header = {"professor": "Unknown", "school": "Unknown"}
    for line in lines[:6]:
        if line.startswith("Professor:"):
            header["professor"] = line.split(":", 1)[1].strip()
        elif line.startswith("School:"):
            header["school"] = line.split(":", 1)[1].strip()
    return header


def _chunks_from_file(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = _parse_header(lines)

    chunks = []
    current_course = None
    comment_lines: list[str] = []
    review_idx = 0

    def flush():
        nonlocal comment_lines, review_idx
        comment = " ".join(comment_lines).strip()
        comment_lines = []
        if not comment:
            return
        if comment.lower() == SEED_REVIEW:  # drop templated placeholder
            return
        review_idx += 1
        course = current_course or "N/A"
        text = (f"Professor {header['professor']}, {header['school']}, "
                f"course {course}: {comment}")
        chunks.append({
            "text": text,
            "metadata": {
                "source": path.name,
                "professor": header["professor"],
                "school": header["school"],
                "course": course,
                "review_index": review_idx,
            },
        })

    in_review = False
    for line in lines:
        m = REVIEW_HEADER.match(line)
        if m:
            flush()                      # close the previous review
            current_course = m.group("course").strip() or "N/A"
            in_review = True
            continue
        if not in_review:
            continue                     # still in the file's top header
        if SEPARATOR.match(line):
            flush()
            in_review = False
            continue
        if line.startswith(META_PREFIXES) or not line.strip():
            continue                     # skip Quality:/Tags: and blank lines
        comment_lines.append(line.strip())
    flush()                              # in case the file didn't end on a separator
    return chunks


def load_chunks() -> list[dict]:
    """Return all chunks across every document file, each as {text, metadata}."""
    files = sorted(DOCS_DIR.glob("*.txt"))
    all_chunks: list[dict] = []
    for path in files:
        all_chunks.extend(_chunks_from_file(path))
    return all_chunks


def main():
    chunks = load_chunks()
    print(f"Total chunks: {len(chunks)} "
          f"(from {len(list(DOCS_DIR.glob('*.txt')))} documents)\n")

    lengths = [len(c["text"]) for c in chunks]
    print(f"Chunk length (chars): min={min(lengths)}  "
          f"max={max(lengths)}  avg={sum(lengths) // len(lengths)}\n")

    print("=== 5 sample chunks ===\n")
    import random
    random.seed(7)
    for c in random.sample(chunks, 5):
        md = c["metadata"]
        print(f"[{md['source']} · review {md['review_index']} · course {md['course']}]")
        print(c["text"])
        print("-" * 70)


if __name__ == "__main__":
    main()
