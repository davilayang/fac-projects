# Chunking & Embedding Strategy

**Project:** Production RAG — arXiv Deep Learning Corpus
**Status:** Adopted
**Last updated:** 2026-03-27

---

## 1. Context

This document records the chunking and embedding decisions made for the production RAG system built on a corpus of 38 recent arXiv papers covering attention mechanisms, transformers, LoRA, scaling laws, RLHF, mixture of experts, quantisation, RAG, model serving, synthetic data, and LLM evaluation.

It is intended to serve two purposes:

1. **Defence** — justify the design choices made to peers and reviewers.
2. **Reference** — record why this design was chosen so that future contributors understand the trade-offs and can make informed changes.

The system must be able to answer precise, citation-grounded queries such as:

> *"In the Bielik-Q2-Sharp study, which 2-bit quantization method performed best on the Polish 11B model?"*
> *"What are the five modular components that the RAGPerf framework decomposes a RAG pipeline into?"*

These queries require locating specific claims within specific papers, which makes chunking quality the most consequential design decision in the entire pipeline.

---

## 2. Corpus Analysis

Before designing any chunking logic, we read the extracted markdown for a representative sample of papers. The findings directly shaped every decision below.

### 2.1 Document structure is consistent

All 38 papers follow the same structural template:

```
Title + Author block
Abstract
1. Introduction
2. Related Work / Background
3. Method / Our Approach
   3.1 Sub-section
   3.2 Sub-section
      3.2.1 Sub-sub-section
4. Experiments / Evaluation
   4.1 Setup
   4.2 Results
   4.3 Ablation Study
5. Conclusion
References
Appendix A ...
Appendix B ...
```

This is not a guess — it was verified across all 38 files. The consistency is high enough that section type can be inferred from heading text and section number reliably (see §4.3).

### 2.2 The PDF extractor flattens all headings to `##`

PyMuPDF4LLM converts every heading to `##` regardless of its logical level. Sections `3`, `3.2`, and `3.2.1` all produce `##` headings. The actual hierarchy is encoded in the section number prefix (`3.2.1` = depth 3), not the markdown heading level. Any chunking strategy that relies on heading level to infer hierarchy will fail on this corpus.

### 2.3 Introduction sections are not uniformly short

We measured the introduction length across all 38 papers:

| Metric | Value |
|---|---|
| Minimum | 112 words (~84 tokens) |
| Maximum | 1,037 words (~778 tokens) |
| Median | 661 words (~496 tokens) |
| Papers exceeding 400 tokens | ~78% |

**Consequence:** the introduction cannot be treated as a guaranteed single-chunk unit. It must be kept as a separate logical unit but allowed to split internally if it exceeds the token budget.

### 2.4 Abstracts are always short and structurally uniform

Every abstract is a single paragraph under `## **Abstract**`, averaging 150–300 words (~110–225 tokens). No abstract in the corpus exceeds the 400-token target. This makes the abstract a reliable fixed single-chunk unit.

### 2.5 Special blocks require atomic treatment

Three types of content must never be split across chunk boundaries:

**Equations.** Mathematical expressions are rendered by PyMuPDF4LLM as `**==> picture [W x H] intentionally omitted <==**` placeholders. They appear either standalone (their own paragraph) or inline within a paragraph. The surrounding prose — typically the sentence that introduces the equation and the "where..." clause that follows — forms an inseparable semantic unit with the placeholder.

**Tables.** Rendered as markdown tables (lines beginning with `|`). Table cells contain numerical results critical to answering test queries. Splitting a table across chunks destroys the information it carries.

**Algorithm blocks.** Pseudocode appears under `## **Algorithm N**` headings followed by a markdown table. The heading, pseudocode table, and the prose explanation immediately before it form one unit.

### 2.6 Figure captions are structurally predictable

Every figure caption follows the format `_Figure N._ **Bold title.** Description.` and always appears immediately after the figure placeholder or picture-text block. The caption and its figure content must be kept together.

### 2.7 The References section is pure bibliography noise

Every paper ends with `## **References**` (before any appendices). This section contains only bibliographic entries — author names, years, journal names, DOIs. It adds noise without retrieval value. The useful citation signal exists in the inline citations throughout the paper body (`(Arditi et al., 2024)`, `[42]`).

### 2.8 Appendices contain supplementary, not primary, content

Appendices follow a consistent `## **A.**`, `## **A.1.**` naming convention. They contain extended derivations, additional experimental results, and example prompts. They are valid retrieval targets but lower-priority than main-body content, and should be labelled accordingly.

### 2.9 PDF extraction artefacts require a pre-processing pass

The extractor produces two classes of noise that pollute chunks if not removed:

- **Repeated page-title headers.** The paper title repeats as a running header at the top of each extracted "page", appearing mid-section as a standalone line matching the document title.
- **Bare page numbers.** Integer lines (`4`, `7`, `12`) appearing between paragraphs as page separators.

These are structural artefacts of the PDF-to-markdown conversion, not content.

---

## 3. Chunking Strategy

### 3.1 Chosen strategy: Recursive Section-Aware with Semantic Fallback

**Strategy identifier:** `subsection_semantic_v1`

The strategy is a three-tier recursive splitter that uses document structure as its primary signal, falls back to paragraph-level packing with semantic boundary detection, and uses sentence splitting as a last resort.

This approach was chosen over alternatives for the following reasons:

| Alternative | Why rejected |
|---|---|
| Fixed-size chunking | Ignores section boundaries entirely. A 512-token window will cut across sections, producing chunks that span unrelated topics. Fatal for citation accuracy. |
| Sliding window | Produces redundant overlapping chunks. For structured scientific documents with clear sections, this adds storage and retrieval noise without proportional recall improvement. |
| H2-recursive (previous approach) | Uses the wrong primary unit (H2 = depth 1 sections). A depth-1 section like "3. Method" can span thousands of tokens across many subsections. The 6,000-token max used in the previous implementation produced chunks far too large for precise retrieval. |
| LLM-assisted chunking | Expensive, slow, and non-deterministic. Unacceptable for a 38-paper corpus running on a CI-style ingest pipeline. |
| Pure semantic / embedding-based splitting | Requires running the embedding model during ingestion to detect topic shifts. Circular dependency. Adds latency and complexity without guaranteed quality improvement at this corpus scale. |

### 3.2 Pre-processing pass (before chunking)

Before any splitting logic runs, each extracted markdown file is cleaned:

1. **Strip the References section.** Detect `## **References**` (case-insensitive) and remove everything from that heading through the next non-appendix heading or end of file.
2. **Strip page-break artefacts.** Remove standalone lines that are bare integers or that exactly repeat the document title. These are reliably identifiable because the document title is already stored in `DocumentMetadata`.
3. **Strip author affiliation blockquotes.** Lines beginning with `>` near the document preamble contain affiliation strings (e.g. `> 1 Hong Kong Polytechnic University`). These are already stored in `DocumentMetadata.institutes` and add no retrieval value when embedded in chunks.

### 3.3 Section parsing

The document is parsed into a flat list of sections by finding all `##` headings. For each heading:

- The **section number** is extracted from the heading text (e.g. `## **3.2.1. Collective Adversarial Data Generation**` → `"3.2.1"`).
- The **logical depth** is derived from the number of dot-separated components (`"3.2.1"` → depth 3; `"3"` → depth 1; no number → depth 0).
- The **section title** is the heading text with the number prefix and markdown markup stripped.
- The **section type** is classified from the title text (see §4.3).
- The **section body** is the text from the end of the heading line to the start of the next `##` heading.

### 3.4 Chunk unit selection

| Section type | Rule |
|---|---|
| Preamble (title + authors, before Abstract) | Single chunk. Author affiliation blockquotes stripped first. |
| Abstract | Always a single chunk. Never split. Abstracts are guaranteed to fit within the 400-token budget. |
| Introduction | Treated as a separate logical unit. Split internally by the paragraph packer if body exceeds 400 tokens. |
| Depth ≥ 2 sections (subsections, sub-subsections) | Primary chunk candidates. Most subsections fit within 400 tokens without further splitting. |
| Depth 1 sections (e.g. "3. Method") | Their body is typically a short transitional paragraph before the first subsection. If ≥ 50 tokens, kept as a standalone chunk. If < 50 tokens, prepended to the first subsection body. |
| Appendix sections | Chunked with the same rules. Labelled `section_type=appendix`. |
| References | **Excluded entirely.** Removed in pre-processing. |

### 3.5 Within-section splitting

When a section body exceeds 400 tokens, a three-tier fallback applies:

**Tier 1 — Semantic paragraph boundaries (preferred).**
Split at paragraphs that begin with a bold-term signal: `**Step 1:**`, `**Gradient-based direction identification.**`, `**Limitations of direct applying...**`. These bold paragraph openers are a reliable authorial convention in this corpus for signalling a topic shift within a section. Splitting before these is semantically clean.

**Tier 2 — Paragraph boundaries.**
If no bold-term boundaries exist or the section is still oversized after tier 1, split at blank-line paragraph boundaries, packing greedily up to 400 tokens.

**Tier 3 — Sentence boundaries (last resort).**
If a single paragraph exceeds 400 tokens (dense mathematical or experimental prose), split at sentence boundaries (`.`, `!`, `?` followed by a capital letter).

### 3.6 Atomic block preservation

Before paragraph packing, each section body is segmented and atomic blocks are identified:

- A **standalone equation paragraph** (entire paragraph is one or more `**==> picture...`  lines) is merged into the preceding paragraph, along with any immediately following paragraph that begins with a mathematical continuation phrase (`where`, `such that`, `we have`, `note that`).
- A **picture-text block** (`**----- Start of picture text -----**` ... `**----- End of picture text -----**`) is merged with the preceding equation placeholder.
- A **figure caption** (`_Figure N._`) is merged with the preceding figure content.
- A **markdown table** (lines beginning with `|`) is never split. The table caption (`_Table N._`) is merged with the table.
- An **algorithm block** (`## **Algorithm N**` heading + markdown table) is treated as a single atomic unit.

Atomic blocks that individually exceed 400 tokens are emitted as a single oversized chunk rather than being split. Correctness takes priority over strict size compliance.

### 3.7 Overlap

A **2-sentence overlap** is applied when a section body produces multiple sub-chunks. The last two sentences of chunk *N* are prepended to chunk *N+1* as context, formatted as `[...] {overlap text}`. This preserves continuity at split boundaries without the semantic ambiguity of character-based overlap.

Overlap is **not** applied across section boundaries. Sections are independent logical units.

### 3.8 Orphan merging

Any sub-chunk below 50 tokens is merged into the preceding chunk. These orphans typically arise from transitional sentences between subsections or short concluding remarks.

### 3.9 Section heading prepended to sub-chunks

When a section body splits into multiple chunks, the section heading line is prepended to each sub-chunk. This ensures the embedding model receives the section context (`## **3.2.1. Collective Adversarial Data Generation**`) as part of the chunk text, not just the fragment in isolation.

### 3.10 Token budget

| Parameter | Value | Rationale |
|---|---|---|
| `max_tokens` | 400 | Stays within SPECTER2's 512-token hard limit with headroom for the heading prefix and sentence overlap |
| `min_tokens` (orphan threshold) | 50 | A chunk below 50 tokens lacks sufficient context for meaningful retrieval |
| Overlap | 2 sentences | Sufficient for continuity; more would introduce noise |
| Token counter | `tiktoken cl100k_base` | Fast, deterministic, matches the tokenisation used for size estimation |

---

## 4. Chunk Metadata

Each chunk stored in the database carries the following metadata, enabling metadata filtering at query time.

### 4.1 Document-level (from `DocumentMetadata`)

| Field | Source | Use at query time |
|---|---|---|
| `document_id` | Filename stem | Primary join key |
| `title` | PDF metadata / extraction | Display in citations |
| `authors` | PDF metadata | Filter by author |
| `abstract` | Extracted from document | Summary context |

### 4.2 Chunk-level

| Field | Description |
|---|---|
| `section_type` | `abstract` / `introduction` / `related_work` / `method` / `experiment` / `conclusion` / `appendix` / `preamble` / `other` |
| `section_number` | e.g. `"3.2.1"` — enables range filtering (`section_number LIKE '3.%'`) |
| `section_title` | Clean title text — surfaced in citations |
| `has_equations` | `bool` — allows filtering out equation-heavy chunks for queries where maths is not relevant |
| `has_tables` | `bool` — useful for queries asking for quantitative comparisons |
| `has_figures` | `bool` |
| `chunk_strategy` | `"subsection_semantic_v1"` — version-tracks the strategy; changing strategy name triggers re-chunking |

### 4.3 Section type classification rules

Section type is inferred from the heading text at parse time:

| Type | Heading matches (case-insensitive) |
|---|---|
| `abstract` | "abstract" |
| `introduction` | "introduction", or section number top-level = "1" |
| `related_work` | "related work", "related", "background", "prior work", "literature" |
| `method` | "method", "approach", "framework", "model", "algorithm", "our", "proposed" |
| `experiment` | "experiment", "evaluation", "result", "analysis", "ablation", "benchmark" |
| `conclusion` | "conclusion", "discussion", "future work", "limitation", "summary" |
| `appendix` | single-letter section number (A, B, C...) or heading contains "appendix" |
| `preamble` | content before the first `##` heading |
| `other` | everything else |

---

## 5. Embedding Model

### 5.1 Chosen model: SPECTER2

**Model:** `allenai/specter2` via `sentence-transformers`
**Dimensions:** 768
**Token limit:** 512
**Deployment:** local inference, no external API dependency

### 5.2 Justification

SPECTER2 is a transformer model trained specifically on scientific paper text using a citation-based training signal. It learns representations where papers that cite each other — and by extension, papers that discuss related concepts — are close in embedding space.

This corpus is 100% scientific papers. Every chunk is dense with domain-specific vocabulary: `LoRA`, `KV-cache`, `RLHF`, `IVFFlat`, `perplexity`, `mixture of experts`, `cosine distance`. A general-purpose embedding model treats these as uncommon tokens with weak or generic representations. SPECTER2 was trained on millions of abstracts and citation pairs from Semantic Scholar; these terms are central to its vocabulary.

The practical consequence for the test queries:

> *"What asymptotic dimensionality do queries and keys need for attention selection?"*

A general model embeds "asymptotic dimensionality" close to other generic dimensionality discussions. SPECTER2 embeds it close to attention mechanism papers because the model has seen this exact construct hundreds of times in cited contexts.

### 5.3 Comparison with alternatives

| Model | Dims | Deployment | Scientific domain fit | Notes |
|---|---|---|---|---|
| **SPECTER2** (chosen) | 768 | Local | Excellent — trained on scientific citations | Best domain alignment for this corpus |
| `text-embedding-3-small` | 1536 | OpenAI API | General purpose | Good general quality; no domain advantage; adds API latency and cost; rate limits affect batch ingestion |
| `text-embedding-3-large` | 3072 | OpenAI API | General purpose | Higher quality than small, but same domain limitation; ~6× more expensive |
| `all-MiniLM-L6-v2` | 384 | Local | General purpose | Fast but lower quality; not suited to technical scientific text |
| `bge-large-en-v1.5` | 1024 | Local | General purpose | Strong general model but not citation-aware |

### 5.4 Dimension and token limit alignment

SPECTER2's 512-token hard limit is the primary reason the `max_tokens` chunk budget is set to 400. The 112-token headroom accommodates:
- The prepended section heading (`## **3.2.1. Title**` ≈ 10–20 tokens)
- The 2-sentence overlap prefix (`[...] Prior sentence. Next sentence.` ≈ 30–60 tokens)
- Tokenisation variance between `cl100k_base` (used for counting) and SPECTER2's internal tokeniser

Chunks that exceed the model's limit are silently truncated by the sentence-transformers library. By staying at 400 tokens, we ensure no content is silently discarded during embedding.

### 5.5 No API dependency

Running SPECTER2 locally eliminates:
- External API latency during batch ingestion of 38 papers
- Rate limit management code
- API key rotation
- Per-token cost accumulation

For a production pipeline that will re-ingest when new papers are added, removing the API dependency simplifies operations significantly.

---

## 6. Vector Storage and Index

**Database:** PostgreSQL + pgvector
**Column type:** `Vector(768)` (matches SPECTER2 output dimensions)
**Distance metric:** cosine distance (`vector_cosine_ops`)

Cosine distance is appropriate because SPECTER2 outputs L2-normalised vectors. On normalised vectors, cosine similarity reduces to dot product, making it both semantically correct and computationally efficient.

**Index type:** HNSW

At the scale of this corpus (~38 papers, estimated 1,000–3,000 chunks), brute-force search would be sub-millisecond and an index is technically optional. We create one regardless because:

1. The corpus is designed to be extended (swapping in a different domain should only require re-ingestion).
2. HNSW provides better recall than IVFFlat, which matters more than build time at this scale.
3. Understanding index behaviour now avoids retrofitting later.

IVFFlat requires pre-populating the table before creating the index (to compute cluster centroids). HNSW builds incrementally and is simpler to manage during ongoing ingestion runs.

---

## 7. Design Decisions Summary

| Decision | Choice | Key reason |
|---|---|---|
| Primary chunk unit | Subsection (depth ≥ 2 by section number) | Right semantic granularity for retrieval; depth-1 sections are too broad |
| Abstract treatment | Always single chunk | Fits within budget; paper identity; never split |
| Introduction treatment | Separate logical unit, split if > 400 tokens | Too long to guarantee single-chunk; must not merge with Method |
| References section | Excluded | Bibliography noise; no retrieval value |
| Appendices | Included, labelled separately | Valid retrieval targets at lower priority |
| Equation handling | Merge with surrounding paragraph | Equation + prose = inseparable semantic unit |
| Overlap type | 2 trailing sentences | Semantic continuity; avoids arbitrary character-count cuts |
| Overlap scope | Within section only | Sections are independent; cross-section overlap would conflate topics |
| Pre-processing | Strip artefacts, affiliations, references | Noise removal before any chunking logic |
| Max chunk tokens | 400 | SPECTER2 hard limit is 512; headroom for heading + overlap |
| Embedding model | SPECTER2 (local) | Scientific domain-specific; no API dependency; citation-aware training |
| Vector dimensions | 768 | Native SPECTER2 output |
| Distance metric | Cosine | Correct for normalised vectors |
| Index type | HNSW | Better recall than IVFFlat; builds incrementally |

---

## 8. Known Limitations and Future Considerations

**Equations are not retrievable.** PyMuPDF4LLM replaces all mathematical expressions with image placeholders. The embedding model encodes the surrounding prose but not the equation itself. Queries that ask about a specific formula (e.g. the exact form of an attention score) will rely on contextual language, not the mathematical notation. Higher-fidelity extraction (e.g. using Claude with PDF page images) would address this at significantly higher cost.

**Semantic grouping is deferred.** The proposed architecture included an optional Layer 3 where SPECTER2 embeddings could be used to cluster and merge semantically related chunks. This has not been implemented in v1. If retrieval quality measurements on the test queries reveal that related concepts are fragmented across chunks, semantic merging is the recommended next step.

**Citation graph is not exploited.** Each chunk contains inline citation markers (e.g. `(Arditi et al., 2024)`). A future enhancement could extract these and build a lightweight citation graph, enabling "retrieve the papers that the retrieved paper cites" as a second-hop retrieval step. The `cross_refs` metadata field in the schema is reserved for this.

**Re-chunking on strategy change.** The `chunk_strategy` field (`subsection_semantic_v1`) version-tracks the strategy. Changing the strategy requires dropping existing chunks for the affected documents and re-running the chunking and embedding flows. The pipeline is idempotent and handles this cleanly by design.

---

*This document should be updated whenever the chunking strategy or embedding model is changed. Record the date, the new strategy identifier, and the reason for the change.*
