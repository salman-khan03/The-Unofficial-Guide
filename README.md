# The Unofficial Guide — Project 1

A small RAG (Retrieval-Augmented Generation) system that answers plain-language questions
about university CS professors using only real student reviews, and cites where each
answer came from.

## How to run

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env                                     # then paste your Groq key in
python scrape_rmp.py        # collect reviews -> documents/
python embed_store.py --build   # chunk + embed + store in ChromaDB
python app.py               # launch the Gradio UI at http://localhost:7860
```

---

## Domain

I built this around **student reviews of CS professors at Stanford and Harvard**, from
Rate My Professors. A course catalog will tell you a class exists and who teaches it, but
not the things you actually want before you register — whether the grading is fair,
whether the lectures are worth attending, whether the professor wants to be there. That
knowledge only exists in what students tell each other, scattered across hundreds of short
reviews that nothing ever summarizes. I used two schools so I could also ask cross-school
comparison questions.

---

## Document Sources

11 documents, one plain-text file per professor, collected from the Rate My Professors
GraphQL API with `scrape_rmp.py`. Each file holds that professor's reviews plus a header
(overall rating, difficulty, review count).

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

**How I ingested and cleaned them:** `scrape_rmp.py` queries the GraphQL API for each
school's CS professors and writes only the review text plus ratings — there's no HTML,
nav, or ads to strip because the API returns structured data. I filter to Computer
Science professors using a word-boundary match, after I found that a naive `"cs"` check
was matching "economi**cs**" and pulling in an econ professor by mistake.

---

## Chunking Strategy

**Chunk size:** One student review per chunk (variable, ~60–414 characters, average 188).
I split documents on the `[Review N]` markers my scraper writes.

**Overlap:** 0.

**Why this fits my documents:** These documents are collections of separate records, not
flowing prose. Each review is one student's complete take on one course, so a review is
the natural thing to retrieve. Fixed-size chunking would merge several unrelated reviews
into a single embedding — a chunk holding both "best professor I've had" and "garbage,
useless knowledge" averages into a vector that matches nothing well. And because reviews
are independent, no fact gets split across a boundary, so overlap would only duplicate
text without helping.

**Preprocessing:** Before embedding, I prepend metadata to each chunk —
`Professor <name>, <school>, course <class>: <review>` — so even a one-line review still
carries who and what it's about and stays findable. I also drop the identical
"Clear lectures, fair exams." review that RMP returns as a default for every professor,
since it's pure noise.

**Final chunk count:** 154 chunks across 11 documents (well within the 50–2,000 range).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim, runs locally, no
API key or rate limits). It fits because my text is short English reviews and this model
is tuned for short-sentence similarity.

**If I were deploying this for real and cost didn't matter:** I'd consider a larger hosted
model (OpenAI `text-embedding-3-large` or Cohere) for better accuracy on sarcastic or
nuanced reviews, which MiniLM sometimes misses. Context length barely matters here since
reviews are short, but it would for long guides; multilingual support would matter if the
reviews weren't all English. The main tradeoff is latency and local-vs-API — running
MiniLM locally costs nothing per query and has no rate limits, which is ideal for a free
project, so I'd only switch if the accuracy gain clearly justified it.

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
All 5 chunks (distances 0.274–0.352) came from `cs_stanford_andrew_ng_reviews.txt`, e.g.
*"Greatest professor ever! ...his Machine Learning course"* and *"one of the best
instructors in the ML field."*
*Why these are relevant:* every chunk is the right professor and directly about his ML
teaching. The query words ("machine learning", "courses") map cleanly onto reviews that
discuss exactly that, and the low distances confirm a strong match.

**Query 2 — "How do students describe Percy Liang as a professor?"**
All 5 (distances 0.332–0.466) came from `cs_stanford_percy_liang_reviews.txt`, ranging
from *"The worst form of professor. Useless knowledge. Garbage."* to *"I really love his
lecturing style!"*
*Why these are relevant:* retrieval surfaced both extremes of a divisive professor instead
of one side, which is exactly what I want to hand the model. The metadata prefix
("Professor Percy Liang") anchors even the short reviews to the right person.

**Query 3 — "Which CS professor is described as funny or like a stand-up comedian?"**
Top hit (distance 0.288): `cs_stanford_chris_gregg_reviews.txt` — *"He is hilarious and I
think he can be a great stand-up comedian."* It also surfaced Malan's "funniest dad jokes"
review.

---

## Grounded Generation

**How I enforce grounding:** The system prompt tells the model to *"Answer using ONLY
information in the provided reviews. Do not use any outside or prior knowledge about these
professors. If the reviews do not contain enough information to answer, reply exactly:
'I don't have enough information on that.'"* It's also told to reflect the range when
reviews disagree and not to invent professors, courses, or quotes. I pass the retrieved
chunks as labeled context blocks (`[Review N | source: ...]`).

**How sources show up:** Citations are added **programmatically** from each retrieved
chunk's metadata in `query.py`, not generated by the model — so a source can't be
hallucinated. If the answer is a refusal, no sources get attached.

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
  source files). I also added a few example questions as clickable buttons.

**Sample interaction:**
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
| 1 | What do students say about Andrew Ng's ML courses? | Very positive; clear, hard but worth it; Coursera praised | "Amazing", "great teacher", "best in the ML field"; Coursera mentioned | Relevant (0.27–0.35) | Accurate |
| 2 | How do students describe Percy Liang? | Divisive/low-rated; dismissive in OH, confusing, minority praise lecturing | Reflects both "worst form of professor" and "love his lecturing style" | Relevant (0.33–0.47) | Accurate |
| 3 | Are Malan's CS50 lectures clear or too lecture-heavy? | Mixed: clear/engaging vs lecture-heavy/dense | "Amazing" vs "not much substance" | Relevant (0.31–0.32) | Accurate |
| 4 | Which professor is funny / a stand-up comedian? | Chris Gregg; Piech "hilarious" | Gregg (stand-up comedian), Malan (dad jokes), Szumlanski | Relevant (0.29–0.42) | Accurate |
| 5 | Do any reviews mention group projects? | Not covered — should refuse | "No... but one review mentions a 'cutting-edge project' in CS229" | Off-target (0.63–0.76) | Partially accurate |

---

## Failure Case Analysis

**The question that failed:** "Do any reviews mention group projects or team assignments?"

**What the system returned:** *"No, the reviews do not mention group projects, but one
review mentions the freedom to work on a 'cutting-edge project' in Professor Andrew Ng's
CS229 course."* — and it attached 5 source files instead of cleanly declining.

**Root cause (tied to specific pipeline stages):** Two things went wrong, in two different
stages. First, in **retrieval**: no review actually talks about group projects, so the
top-5 chunks were all weak matches (distances 0.63–0.76, above the ~0.6 line where I'd
call a match weak) — there was simply nothing relevant to find. Second, in **generation
and attribution**: the model latched onto the single nearest word it could find
("project" in Ng's CS229 review) and stretched it toward the question instead of refusing.
And because my refusal check in `query.py` looks for the exact phrase
`"don't have enough information"`, the model's differently-worded near-refusal ("No, the
reviews do not mention...") slipped past it, so the source-suppression logic never fired
and 5 sources got attached to what's basically a "not covered" answer.

**What I'd change to fix it:** Add a distance threshold in `retrieve()` — if even the best
distance is above ~0.6, treat the question as unanswerable and return the refusal before
ever calling the LLM. I'd also detect refusals by meaning rather than exact string so
sources are suppressed for any phrasing of "not covered."

---

## Spec Reflection

**One way the spec helped me:** Deciding "one review = one chunk, overlap 0, metadata
prepended" in `planning.md` before I wrote any code made the implementation almost
mechanical — `chunk_documents.py` just splits on review boundaries and adds the metadata
line, with no fiddling over a magic character count. Working out the strategy on paper
first meant the code matched the shape of my data instead of fighting it.

**One way my implementation diverged from the spec:** I hadn't planned for the templated
"Clear lectures, fair exams." review that RMP returns for every single professor. Once I
saw it in the real data I added a cleaning step to drop that exact string, because leaving
it in would have created 11 near-identical chunks that pollute retrieval and carry no real
information. It's a small change, but it came directly from looking at what the data
actually contained rather than what I assumed it would.

---

## AI Usage

**Instance 1 — chunking**
- *What I gave the AI:* My Chunking Strategy section from `planning.md` (one review per
  chunk, overlap 0, metadata prepended) and the format of my scraped `.txt` files.
- *What it produced:* `chunk_documents.py`, splitting on `[Review N]` boundaries and
  prepending `Professor <name>, <school>, course <class>:` to each review.
- *What I changed or directed:* I told it to drop the "Clear lectures, fair exams."
  placeholder once I noticed it appears identically in every file, and I verified the
  output by inspecting 5 sample chunks and checking the total count (154).

**Instance 2 — generation and the failure case**
- *What I gave the AI:* My grounding requirement (answer only from retrieved context,
  refuse otherwise) and the rule that source attribution had to be programmatic, not
  model-generated.
- *What it produced:* `query.py` with a strict system prompt and metadata-based citations,
  plus `app.py` (the Gradio UI).
- *What I changed or directed:* When testing surfaced that the "group projects" query
  wasn't refused cleanly, I traced it to the exact-phrase refusal check, documented it as
  my failure case, and worked out the distance-threshold fix rather than just patching
  over the symptom.
