# Project 1 Planning: The Unofficial Guide

> Written before I wrote any pipeline code. This is the spec I used to direct the
> implementation, and I updated the Chunking and Retrieval sections as I learned things
> from the real data.

---

## Domain

I'm building this around **student reviews of Computer Science professors at Stanford
and Harvard**, pulled from Rate My Professors. The reason I picked this domain is that a
course catalog tells you a class exists and who teaches it, but it never tells you the
stuff you actually want to know before you register — is the grading fair, are the
lectures worth showing up to, does the professor actually want to be there. That kind of
knowledge only lives in what students say to each other, and it's spread across hundreds
of short reviews that no single page ever summarizes. I went with two schools on purpose
so the system can also handle comparison questions across them.

---

## Documents

11 documents, one plain-text file per professor. I collected them straight from the Rate
My Professors GraphQL API with `scrape_rmp.py` rather than copy-pasting, so the text
comes in already structured (review body + rating + course). Each file also has a header
with the professor's overall rating, difficulty, and review count.

| #  | Source | Description | URL or location |
|----|--------|-------------|-----------------|
| 1  | cs_harvard_david_malan_reviews.txt     | Harvard, CS50 — 60 reviews (my richest doc) | ratemyprofessors.com (Harvard, CS) |
| 2  | cs_stanford_chris_piech_reviews.txt    | Stanford, CS106A — 27 reviews               | ratemyprofessors.com (Stanford, CS) |
| 3  | cs_stanford_andrew_ng_reviews.txt      | Stanford, machine learning — 25 reviews     | ratemyprofessors.com (Stanford, CS) |
| 4  | cs_stanford_chris_gregg_reviews.txt    | Stanford, CS106B/CS110 — 11 reviews         | ratemyprofessors.com (Stanford, CS) |
| 5  | cs_stanford_percy_liang_reviews.txt    | Stanford, CS336 — 10 reviews (very divisive)| ratemyprofessors.com (Stanford, CS) |
| 6  | cs_stanford_sean_szumlanski_reviews.txt| Stanford — 9 reviews                        | ratemyprofessors.com (Stanford, CS) |
| 7  | cs_harvard_michael_smith_reviews.txt   | Harvard — 7 reviews                         | ratemyprofessors.com (Harvard, CS) |
| 8  | cs_stanford_emma_brunskill_reviews.txt | Stanford, reinforcement learning — 5 reviews| ratemyprofessors.com (Stanford, CS) |
| 9  | cs_harvard_mostafa_amir_reviews.txt    | Harvard — 5 reviews                         | ratemyprofessors.com (Harvard, CS) |
| 10 | cs_stanford_greg_tucker_reviews.txt    | Stanford — 3 reviews                        | ratemyprofessors.com (Stanford, CS) |
| 11 | cs_stanford_binh_le_reviews.txt        | Stanford, section leader — 1–2 reviews      | ratemyprofessors.com (Stanford, CS) |

I tried to get variety on purpose: highly-rated professors (Gregg 4.8, Piech 5.0), a
genuinely divisive one (Liang 2.7), and a high-volume one (Malan, 60 reviews), plus both
schools so I can ask comparison questions.

---

## Chunking Strategy

**Chunk size:** One student review = one chunk (variable length, roughly 1–4 sentences).
I split on the `[Review N]` markers that my scraper writes.

**Overlap:** 0.

**Reasoning:** After reading through the documents, the thing that jumped out is that
these aren't continuous prose — they're a pile of separate records, where each review is
one student's complete opinion about one course. So a single review is the obvious unit
to retrieve. If I used fixed 500-character chunks instead, I'd be cramming four or five
unrelated reviews into one embedding, and a chunk that says both "best professor I've
had" and "useless, garbage" would average out into a vector that doesn't really match any
specific question. And since the reviews don't continue into each other, there's no fact
that gets split across a boundary — which is the whole reason overlap exists — so overlap
would just duplicate text for no benefit.

The one weakness I see with per-review chunks is that some reviews are a single short
sentence, which doesn't carry much signal on its own. To fix that, I prepend metadata to
each chunk before embedding, like `Professor Percy Liang, Stanford, course CS336: <review>`.
That way even a one-liner still knows who and what it's about, so a query that names the
professor can still pull it. I also keep the professor/school/course as structured
metadata for citations later.

With ~164 reviews this comes out to ~154 chunks (after dropping a placeholder review,
explained below) — comfortably inside the 50–2,000 range the project warns about.

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` through `sentence-transformers` (384-dim, runs
locally, no API key). It's a good match here because my text is short English reviews and
this model is built for short-sentence similarity.

**Top-k:** 5. Reviews of the same professor often disagree, so one chunk isn't
representative — I want enough to surface a few different opinions, but not so many that I
start pulling in loosely-related reviews that drag the answer off-topic. I planned to
re-check this once I saw real distance scores.

**If I were deploying this for real and cost didn't matter:** I'd think about swapping in
a larger hosted embedding model (something like OpenAI's `text-embedding-3-large` or
Cohere) for better accuracy on sarcastic or nuanced reviews, which MiniLM sometimes
misses. Context length barely matters here since reviews are short, but it would for
long-form guides. Multilingual support would matter if the reviews weren't all in
English. The big tradeoff is latency and local-vs-API: MiniLM running locally costs
nothing per query and has no rate limits, which is exactly what I want for a free,
demoable project — I'd only give that up if the accuracy gain were clearly worth it.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about Andrew Ng's machine learning courses? | Very positive; reviewers call him a top researcher, say he explains ML clearly, and that the class is hard but worth it. Several mention his Coursera courses. |
| 2 | How do students describe Percy Liang as a professor? | Divisive and low-rated (2.7/5). A lot of reviews say he's hard to talk to, dismissive in office hours, and confusing in CS336; a few praise his lecturing style. |
| 3 | Do students find David Malan's CS50 lectures clear, or too lecture-heavy? | Mixed — some praise the clear, engaging lectures; others say it's lecture-heavy, too dense, or "not much substance." |
| 4 | Which CS professor is described as funny or like a stand-up comedian? | Chris Gregg (literally "could be a stand-up comedian"); Chris Piech is also called "hilarious." |
| 5 | Do any reviews mention group projects or team assignments? | Probably not really covered — I expect the system to say it doesn't have enough information instead of making something up. This is my intentional stress-test question. |

---

## Anticipated Challenges

1. **A placeholder review that shows up everywhere.** Every professor's file contains the
   exact same generic review — "Clear lectures, fair exams." with a 2026 date — that the
   RMP API hands back as a default. Because it's identical across all 11 professors, a
   vague query could match it from the wrong professor, and it adds zero real signal. I
   plan to strip that exact string during cleaning.

2. **Professors with barely any reviews.** Binh Le has ~1 real review and Greg Tucker ~3.
   Questions about them might not retrieve enough to answer well — I think this is where a
   failure is most likely to show up.

3. **Reviews that contradict each other.** The same professor often gets reviews at both
   extremes (Liang is "a pro" and "the worst form of professor"). The model needs to show
   the range honestly instead of just picking a side, which depends on top-k pulling in
   more than one perspective.

4. **Short or sarcastic reviews.** One-word reviews ("great!", "Super Maikol") carry weak
   semantic signal and may not embed well.

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

**Milestone 3 — Ingestion and chunking:** Ingestion was already handled by my
`scrape_rmp.py` (RMP GraphQL API → clean per-professor `.txt` files). For chunking, I gave
Claude my Chunking Strategy section above and asked it to write a `chunk_documents()` that
splits each file on the `[Review N]` markers, drops the "Clear lectures, fair exams."
placeholder, prepends `Professor <name>, <school>, course <class>:` to each review, and
attaches `{source, professor, school}` metadata. My plan to verify was to print 5 chunks
and confirm each one is a single self-contained review with the right metadata.

**Milestone 4 — Embedding and retrieval:** I gave Claude the Retrieval Approach section
plus the diagram and asked it to embed all chunks with `all-MiniLM-L6-v2`, store them in
ChromaDB with metadata, and write a `retrieve(query, k=5)` that returns the chunks, their
sources, and distance scores. I planned to check it by running 3 of my eval questions and
making sure the chunks were on-topic with distances under 0.5.

**Milestone 5 — Generation and interface:** I gave Claude my grounding requirement (answer
only from retrieved context, refuse when there isn't enough) and asked it to write the
Groq prompt, an `ask(query)` returning `{answer, sources}`, and a small Gradio UI. My plan
to verify grounding was to ask an out-of-scope question (eval Q5) and confirm it refuses
instead of inventing an answer.
