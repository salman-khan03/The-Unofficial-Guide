# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

> ⚠️ DRAFT — rewrite each section in your own words before submitting. The reasoning
> below is yours to defend on video, so make sure you understand and agree with it.

---

## Domain

Student-written reviews of **Computer Science professors at Stanford and Harvard**,
collected from Rate My Professors. This is the unofficial counterpart to a course
catalog: catalogs tell you a class exists and who teaches it, but not whether the
professor is a tough grader, whether attendance actually matters, or whether the
lectures are clear. That knowledge only lives in what students tell each other.
Covering two schools also lets the system answer cross-school comparison questions.

This knowledge is hard to find officially because universities don't publish candid
critiques of their own faculty, and the information is scattered across hundreds of
short, individually-written reviews that no single page summarizes.

---

## Documents

11 documents, one plain-text file per professor, collected via the Rate My Professors
GraphQL API using `scrape_rmp.py`. Each file holds that professor's reviews plus a
header with their overall rating, difficulty, and total rating count.

| #  | Source (file)                          | Description                                  | Location / URL |
|----|----------------------------------------|----------------------------------------------|----------------|
| 1  | cs_harvard_david_malan_reviews.txt     | Harvard, CS50 — 60 reviews (richest doc)     | ratemyprofessors.com (Harvard, CS) |
| 2  | cs_stanford_chris_piech_reviews.txt    | Stanford, CS106A — 27 reviews                | ratemyprofessors.com (Stanford, CS) |
| 3  | cs_stanford_andrew_ng_reviews.txt      | Stanford, machine learning — 25 reviews      | ratemyprofessors.com (Stanford, CS) |
| 4  | cs_stanford_chris_gregg_reviews.txt    | Stanford, CS106B/CS110 — 11 reviews          | ratemyprofessors.com (Stanford, CS) |
| 5  | cs_stanford_percy_liang_reviews.txt    | Stanford, CS336 — 10 reviews (polarizing)    | ratemyprofessors.com (Stanford, CS) |
| 6  | cs_stanford_sean_szumlanski_reviews.txt| Stanford — 9 reviews                         | ratemyprofessors.com (Stanford, CS) |
| 7  | cs_harvard_michael_smith_reviews.txt   | Harvard — 7 reviews                          | ratemyprofessors.com (Harvard, CS) |
| 8  | cs_stanford_emma_brunskill_reviews.txt | Stanford, reinforcement learning — 5 reviews | ratemyprofessors.com (Stanford, CS) |
| 9  | cs_harvard_mostafa_amir_reviews.txt    | Harvard — 5 reviews                          | ratemyprofessors.com (Harvard, CS) |
| 10 | cs_stanford_greg_tucker_reviews.txt    | Stanford — 3 reviews                         | ratemyprofessors.com (Stanford, CS) |
| 11 | cs_stanford_binh_le_reviews.txt        | Stanford, section leader — 1–2 reviews       | ratemyprofessors.com (Stanford, CS) |

Variety: mix of highly-rated (Gregg 4.8, Piech 5.0), divisive (Liang 2.7), and
high-volume (Malan 60 reviews) professors, plus two schools for comparison.

---

## Chunking Strategy

**Chunk size:** One student review per chunk (variable length, typically ~1–4
sentences / 50–400 characters). Split on the `[Review N]` boundaries that
`scrape_rmp.py` writes.

**Overlap:** 0.

**Reasoning:** These documents are collections of discrete records, not continuous
prose. Each review is already a self-contained opinion from one student about one
course, so a review is the natural retrieval unit. Fixed-size chunking (e.g. 500
chars) would merge several unrelated reviews into one embedding — averaging together
"best professor I've had" and "garbage, useless knowledge" into a muddy vector that
matches no specific query well. Because reviews are independent, no fact spans a
boundary, so overlap would only duplicate content without rescuing any split context.

To keep short reviews retrievable, each chunk is **prepended with metadata** before
embedding, e.g.: `Professor Percy Liang, Stanford, course CS336: <review text>`. This
ensures a one-line review like "Clear lectures, fair exams." still carries the
professor and course so a query naming them can retrieve it. The raw professor/school/
course is also stored as structured metadata for source attribution.

With ~164 reviews this yields ~164 chunks — well inside the spec's 50–2,000 range.

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim, runs
locally, no API key). Good fit because reviews are short English text and this model
is tuned for short-sentence semantic similarity.

**Top-k:** 5. Enough to surface several independent opinions on a professor (reviews
disagree, so one chunk isn't representative) without diluting context with unrelated
reviews. Will tune after seeing real distance scores in Milestone 4.

**Production tradeoff reflection:** If cost weren't a constraint, I'd weigh a larger
hosted embedding model (e.g. OpenAI `text-embedding-3-large` or Cohere embeddings) for
better accuracy on nuanced/sarcastic review text, which MiniLM can miss. Other axes:
**context length** matters little here (reviews are short) but would for long-form
guides; **multilingual** support would matter if reviews weren't English; **latency
and local-vs-API** — MiniLM's local inference means no per-query cost and no rate
limits, which is ideal for a free, demoable project, at some accuracy cost.

---

## Evaluation Plan

> Verify each expected answer against the actual review files before relying on it.

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about Andrew Ng's machine learning courses? | Highly regarded; reviewers call him a top researcher, say he explains ML concepts thoroughly and clearly, and that the class is difficult but worth it. Several mention his Coursera courses. |
| 2 | How do students describe Percy Liang as a professor? | Polarizing and low-rated (2.7/5). Multiple reviews say he's difficult to talk to, dismissive in office hours, and confusing in CS336; a minority praise his lecturing style. |
| 3 | Do students find David Malan's CS50 lectures clear, or too lecture-heavy? | Mixed: some praise clear lectures and fair exams; several others call it lecture-heavy and say he talks too much / tells life stories. |
| 4 | Which CS professor is described as funny or like a stand-up comedian? | Chris Gregg (explicitly "could be a stand-up comedian"); Chris Piech is also called "hilarious." |
| 5 | Do any reviews mention group projects or team assignments? | Likely NOT in the documents — system should respond that it doesn't have enough information rather than inventing an answer. (Deliberate refusal / failure-case test.) |

---

## Anticipated Challenges

1. **Templated/seed reviews pollute retrieval.** Every professor's file contains an
   identical generic review — "Clear lectures, fair exams." (dated 2026, Quality 4 /
   Difficulty 3) — that RMP's API returns as a placeholder. Because it's identical
   across all professors, a vague query could retrieve it from the wrong professor,
   and it adds no real signal. Mitigation: filter out this exact string during
   cleaning, or rely on prepended professor metadata to disambiguate.

2. **Thin data for low-review professors.** Binh Le has only ~1 real review and Greg
   Tucker ~3. Questions about them may retrieve too little to answer well, or the
   single review may not address what was asked — a likely failure case to document.

3. **Contradictory opinions per professor.** Reviews for the same professor often
   disagree sharply (Liang is "a pro" and "the worst form of professor"). The LLM must
   reflect the range honestly rather than picking one side, which depends on top-k
   retrieving multiple perspectives.

4. **Sarcasm / short text.** Terse or sarcastic reviews ("Super Maikol", "great!")
   carry weak semantic signal and may embed poorly.

---

## Architecture

```
                         THE UNOFFICIAL GUIDE — RAG PIPELINE

  ┌──────────────────┐     ┌──────────────┐     ┌───────────────────────────┐
  │ 1. INGESTION     │     │ 2. CHUNKING  │     │ 3. EMBEDDING + VECTOR STORE│
  │                  │     │              │     │                           │
  │ scrape_rmp.py    │ ──> │ split on     │ ──> │ all-MiniLM-L6-v2 (384-d)  │
  │ RMP GraphQL API  │     │ [Review N];  │     │ embeds metadata+review;   │
  │ -> documents/    │     │ prepend prof/│     │ stored in ChromaDB with   │
  │ *.txt (clean)    │     │ school/course│     │ source metadata           │
  └──────────────────┘     └──────────────┘     └─────────────┬─────────────┘
                                                              │
                          ┌───────────────────────────────────┘
                          v
  ┌───────────────────────────┐     ┌──────────────────────────────────────┐
  │ 4. RETRIEVAL              │     │ 5. GENERATION                        │
  │                           │     │                                      │
  │ embed query w/ MiniLM;    │ ──> │ Groq llama-3.3-70b-versatile;        │
  │ ChromaDB similarity search│     │ prompt = "answer ONLY from context"; │
  │ top-k = 5 chunks          │     │ append source filenames (citations)  │
  └───────────────────────────┘     └────────────────┬─────────────────────┘
                                                      v
                                            Gradio UI (answer + sources)
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:** Ingestion is already done via `scrape_rmp.py`
(RMP GraphQL API → clean per-professor `.txt` files). I'll give Claude my Chunking
Strategy section above and ask it to implement a `chunk_documents()` function that
splits each file on `[Review N]` boundaries, drops the templated "Clear lectures, fair
exams." seed review, prepends `Professor <name>, <school>, course <class>:` to each
review, and attaches `{source, professor, school}` metadata. I'll verify by printing 5
chunks and confirming each is one self-contained review with correct metadata.

**Milestone 4 — Embedding and retrieval:** I'll give Claude the Retrieval Approach
section and the architecture diagram and ask it to embed all chunks with
`all-MiniLM-L6-v2`, store them in ChromaDB with metadata, and write a `retrieve(query,
k=5)` function returning chunks + sources + distance scores. I'll verify by running 3
eval questions and checking that returned chunks are on-topic with distances < 0.5.

**Milestone 5 — Generation and interface:** I'll give Claude my grounding requirement
(answer only from retrieved context; refuse when context is insufficient) and ask it to
write the Groq prompt template, an `ask(query)` function that returns
`{answer, sources}`, and a minimal Gradio UI. I'll verify grounding by asking an
out-of-scope question (eval Q5) and confirming the system refuses instead of inventing.
