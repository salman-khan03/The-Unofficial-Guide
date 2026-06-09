# The Unofficial Guide — Project 1

> ⚠️ **DRAFT generated with AI assistance — reword each section in your own voice before
> submitting, and confirm every claim matches what you understand about your system.**
> The technical content reflects the system as actually built and tested.

A Retrieval-Augmented Generation (RAG) system that answers plain-language questions
about university CS professors using only real student reviews, with cited sources.

---

## Domain

Student-written reviews of **Computer Science professors at Stanford and Harvard**,
collected from Rate My Professors. This is the unofficial counterpart to a course
catalog: catalogs list who teaches a class, but never whether the professor is a tough
grader, whether the lectures are clear, or whether attendance actually matters. That
knowledge only exists in what students tell each other, scattered across hundreds of
short individual reviews that no single page summarizes. Covering two schools also lets
the system answer cross-school comparison questions.

---

## Document Sources

11 documents, one plain-text file per professor, collected programmatically from the
Rate My Professors GraphQL API via `scrape_rmp.py`. Each file holds that professor's
reviews plus a header (overall rating, difficulty, total rating count).

| #  | Source (file) | Type | URL or file path |
|----|---------------|------|------------------|
| 1  | cs_harvard_david_malan_reviews.txt      | RMP reviews (60) | ratemyprofessors.com — Harvard CS |
| 2  | cs_stanford_chris_piech_reviews.txt     | RMP reviews (27) | ratemyprofessors.com — Stanford CS |
| 3  | cs_stanford_andrew_ng_reviews.txt       | RMP reviews (25) | ratemyprofessors.com — Stanford CS |
| 4  | cs_stanford_chris_gregg_reviews.txt     | RMP reviews (11) | ratemyprofessors.com — Stanford CS |
| 5  | cs_stanford_percy_liang_reviews.txt     | RMP reviews (10) | ratemyprofessors.com — Stanford CS |
| 6  | cs_stanford_sean_szumlanski_reviews.txt | RMP reviews (9)  | ratemyprofessors.com — Stanford CS |
| 7  | cs_harvard_michael_smith_reviews.txt    | RMP reviews (7)  | ratemyprofessors.com — Harvard CS |
| 8  | cs_stanford_emma_brunskill_reviews.txt  | RMP reviews (5)  | ratemyprofessors.com — Stanford CS |
| 9  | cs_harvard_mostafa_amir_reviews.txt     | RMP reviews (5)  | ratemyprofessors.com — Harvard CS |
| 10 | cs_stanford_greg_tucker_reviews.txt     | RMP reviews (3)  | ratemyprofessors.com — Stanford CS |
| 11 | cs_stanford_binh_le_reviews.txt         | RMP reviews (1–2)| ratemyprofessors.com — Stanford CS |

**Ingestion/cleaning:** `scrape_rmp.py` queries the GraphQL API for each school's CS
professors and writes only the substantive review text + ratings — no HTML, nav, or
ads, since the API returns structured data. A department filter keeps only Computer
Science professors (using a word-boundary match so "economi**cs**" is excluded).

---

## Chunking Strategy

**Chunk size:** One student review per chunk (variable, ~60–414 characters; avg 188).
Documents are split on the `[Review N]` boundaries that `scrape_rmp.py` writes.

**Overlap:** 0.

**Why these choices fit your documents:** These documents are collections of discrete
records, not continuous prose. Each review is a self-contained opinion from one student
about one course, so a review is the natural retrieval unit. Fixed-size chunking (e.g.
500 chars) would merge several unrelated reviews into one embedding — averaging "best
professor I've had" together with "garbage, useless knowledge" into a muddy vector that
matches no specific query well. Because reviews are independent, no fact spans a
boundary, so overlap would only duplicate text without rescuing split context.

**Preprocessing:** Each chunk is prepended with metadata before embedding —
`Professor <name>, <school>, course <class>: <review text>` — so even a one-line review
carries the professor and course and stays retrievable. The identical templated review
RMP returns for every professor ("Clear lectures, fair exams.") is dropped as noise.

**Final chunk count:** 154 chunks across 11 documents (within the 50–2,000 range).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dimensional, runs
locally with no API key or rate limits). It's well-suited here because reviews are
short English text and this model is tuned for short-sentence semantic similarity.

**Production tradeoff reflection:** If cost weren't a constraint, I'd weigh a larger
hosted model (e.g. OpenAI `text-embedding-3-large` or Cohere embeddings) for better
accuracy on nuanced or sarcastic review text, which MiniLM can miss. Other axes:
**context length** matters little here (reviews are short) but would for long-form
guides; **multilingual** support would matter if reviews weren't all English;
**latency / local-vs-API** — MiniLM's local inference means zero per-query cost and no
rate limits, ideal for a free, demoable project, at some accuracy cost versus a larger
API model.

---

## Sample Chunks

Five representative chunks, each labeled with its source document:

1. **`cs_stanford_andrew_ng_reviews.txt`** — *"Professor Andrew Ng, Stanford University, course CS229: Prof. Ng is very polite but he rushes explanations and his notes don't distinguish scalars/vectors/matrices... Homework is very hard... Great subject but absolutely ridiculous course."*
2. **`cs_harvard_david_malan_reviews.txt`** — *"Professor David Malan, Harvard University, course CS50: Best professor I've had in my entire undergraduate career. He is super passionate about coding... His lectures are organized."*
3. **`cs_stanford_chris_gregg_reviews.txt`** — *"Professor Chris Gregg, Stanford University, course CS106B: This teacher may come off as a bit conservative and rigid, but when you get used to his teaching style you see he's very consistent... Super nice, really wants you to succeed."*
4. **`cs_stanford_percy_liang_reviews.txt`** — *"Professor Percy Liang, Stanford University, course CS221: The worst form of professor. Useless knowledge. Garbage."*
5. **`cs_harvard_david_malan_reviews.txt`** — *"Professor David Malan, Harvard University, course CS50X: ...Malan has to condense usual 50-70 hour Udemy/YouTube course material into 10 2hr videos so it makes sense why its too difficult. Professor Malan is good but the course is too dense."*

---

## Retrieval Test Results

Embedding model + ChromaDB (cosine distance), top-k = 5. Three queries:

**Query 1 — "What do students say about Andrew Ng's machine learning courses?"**
Top 5 chunks (distances 0.274–0.352) are all from `cs_stanford_andrew_ng_reviews.txt`,
e.g. *"Greatest professor ever! ...his Machine Learning course"* and *"one of the best
instructors in the ML field."*
*Why relevant:* every chunk is from the correct professor and directly addresses his ML
teaching — the query terms ("machine learning", "courses") map cleanly onto reviews
that discuss exactly that, and the low distances confirm strong semantic match.

**Query 2 — "How do students describe Percy Liang as a professor?"**
Top 5 (distances 0.332–0.466) are all from `cs_stanford_percy_liang_reviews.txt`,
spanning *"The worst form of professor. Useless knowledge. Garbage."* and *"I really
love his lecturing style!"*
*Why relevant:* retrieval surfaced both extremes of a polarizing professor rather than
one side, giving the LLM the full range — the metadata prefix ("Professor Percy Liang")
anchors even short reviews to the right person.

**Query 3 — "Which CS professor is described as funny or like a stand-up comedian?"**
Top hit (distance 0.288): `cs_stanford_chris_gregg_reviews.txt` — *"He is hilarious and
I think he can be a great stand-up comedian."* Also surfaces Malan's "funniest dad
jokes" review.

---

## Grounded Generation

**System prompt grounding instruction:** The model is instructed to *"Answer using ONLY
information in the provided reviews. Do not use any outside or prior knowledge about
these professors. If the reviews do not contain enough information to answer, reply
exactly: 'I don't have enough information on that.'"* It is also told to reflect the
range when reviews disagree and not to invent professors, courses, or quotes. The
retrieved chunks are passed as labeled context blocks (`[Review N | source: ...]`).

**How source attribution is surfaced:** Sources are added **programmatically** from
each retrieved chunk's metadata (`query.py`), not left to the LLM to generate — so
citations can't be hallucinated. When the answer is a refusal, no sources are attached.

---

## Example Responses

**Example 1 (in-scope, cited):**
> **Q:** How do students describe Percy Liang as a professor?
> **A:** Students have varying opinions about Professor Percy Liang, with some describing
> him as "useless" and "the worst form of professor", while others find him "polite" and
> "knowledgable"... His age is also mentioned, with one student suggesting he is "too young".
> **Sources:** cs_stanford_percy_liang_reviews.txt

**Example 2 (in-scope, cited):**
> **Q:** Which CS professor is described as funny or like a stand-up comedian?
> **A:** Professors Chris Gregg and David Malan are described as funny, with Chris Gregg
> being considered a potential stand-up comedian and David Malan telling the "funniest
> dad jokes". Professor Sean Szumlanski is also mentioned as being funny.
> **Sources:** cs_stanford_chris_gregg_reviews.txt, cs_harvard_david_malan_reviews.txt, ...

**Example 3 (out-of-scope refusal):**
> **Q:** How much does campus parking cost?
> **A:** I don't have enough information on that.
> **Sources:** (none — system declined to answer)

---

## Query Interface

A **Gradio web UI** (`app.py`, run with `python app.py` → http://localhost:7860).

- **Input field:** "Your question" — a text box for a plain-language question.
- **Output fields:** "Answer" (the grounded response) and "Retrieved from" (the cited
  source files). Example questions are provided as clickable buttons.

**Sample interaction transcript:**
```
Your question:  How do students describe Percy Liang as a professor?
Answer:         Students have varying opinions about Professor Percy Liang, with some
                describing him as "useless" and "the worst form of professor", while
                others find him "polite" and "knowledgable"...
Retrieved from: • cs_stanford_percy_liang_reviews.txt
```

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do students say about Andrew Ng's ML courses? | Highly regarded; clear, difficult but worth it; Coursera praised | "Amazing", "great teacher", "best in the ML field"; Coursera mentioned | Relevant (0.27–0.35) | Accurate |
| 2 | How do students describe Percy Liang? | Polarizing/low-rated; dismissive in OH, confusing, minority praise lecturing | Reflects both "worst form of professor" and "love his lecturing style" | Relevant (0.33–0.47) | Accurate |
| 3 | Are Malan's CS50 lectures clear or too lecture-heavy? | Mixed: clear/engaging vs lecture-heavy/dense | "Amazing" vs "not much substance" | Relevant (0.31–0.32) | Accurate |
| 4 | Which professor is funny / a stand-up comedian? | Chris Gregg; Piech "hilarious" | Gregg (stand-up comedian), Malan (dad jokes), Szumlanski | Relevant (0.29–0.42) | Accurate |
| 5 | Do any reviews mention group projects? | Not covered — should refuse | "No... but one review mentions a 'cutting-edge project' in CS229" | Off-target (0.63–0.76) | Partially accurate |

---

## Failure Case Analysis

**Question that failed:** "Do any reviews mention group projects or team assignments?"

**What the system returned:** *"No, the reviews do not mention group projects, but one
review mentions the freedom to work on a 'cutting-edge project' in Professor Andrew Ng's
CS229 course."* — and it attached 5 source files instead of cleanly declining.

**Root cause (tied to a specific pipeline stage):** Two stages contributed. (1)
**Retrieval:** no review actually discusses group projects, so the top-5 chunks were all
weak matches (distances 0.63–0.76, above the ~0.6 "weak" threshold) — there was nothing
relevant to retrieve. (2) **Generation + attribution:** the model latched onto the one
semantically-nearest word ("project" in Ng's CS229 review) and stretched it toward the
question instead of refusing. Because my refusal detection in `query.py` keys on the
exact phrase `"don't have enough information"`, and the model phrased its near-refusal
differently ("No, the reviews do not mention..."), the source-suppression logic didn't
fire and 5 sources were attached to an answer that's essentially "not covered."

**What you would change to fix it:** Add a **distance threshold** in `retrieve()` — if
the best distance exceeds ~0.6, treat the query as unanswerable and short-circuit to the
refusal before calling the LLM. Optionally, detect refusals semantically rather than by
exact string match so source attribution is suppressed for any form of "not covered."

---

## Spec Reflection

**One way the spec (`planning.md`) helped you during implementation:** Committing to
"one review = one chunk, overlap 0, metadata prepended" in the spec before coding made
the chunking implementation direct and unambiguous — `chunk_documents.py` simply splits
on review boundaries and prepends the metadata line, with no fixed-size tuning needed.
Deciding the strategy on paper first meant the code matched the documents' structure
instead of fighting it.

**One way your implementation diverged from the spec, and why:** The spec didn't
anticipate the templated "Clear lectures, fair exams." seed review that RMP returns for
every professor. I added a cleaning step to drop that exact string, because leaving it in
would have created 11 near-identical chunks that pollute retrieval and add no signal —
a divergence driven by what the real data actually contained once collected.

---

## AI Usage

**Instance 1**
- *What I gave the AI:* My Chunking Strategy section from `planning.md` (one review per
  chunk, overlap 0, metadata prepended) plus the format of the scraped `.txt` files.
- *What it produced:* `chunk_documents.py`, splitting on `[Review N]` boundaries and
  prepending `Professor <name>, <school>, course <class>:` to each review.
- *What I changed or overrode:* I directed it to drop the templated "Clear lectures,
  fair exams." seed review after I noticed it appears identically in every file, and I
  verified the output by inspecting 5 sample chunks and the total count (154).

**Instance 2**
- *What I gave the AI:* My grounding requirement (answer only from retrieved context,
  refuse otherwise) and the requirement that source attribution be programmatic.
- *What it produced:* `query.py` with a strict system prompt and metadata-based source
  attribution, plus `app.py` (Gradio UI).
- *What I changed or overrode:* Testing surfaced that a borderline query ("group
  projects") wasn't refused cleanly because refusal detection used exact-phrase matching;
  I documented this as my failure case and identified a distance-threshold fix.
