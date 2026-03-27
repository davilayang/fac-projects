"""Smoke tests for the chunking logic.

These tests exercise pure functions only — no database, no Prefect, no I/O.
"""


from flows.chunking import (
    MAX_TOKENS,
    MIN_TOKENS,
    _classify_section_type,
    _count_tokens,
    _merge_equation_context,
    _merge_orphans,
    _Para,
    _parse_section_number,
    _preprocess,
    chunk_markdown,
)

# ---------------------------------------------------------------------------
# _parse_section_number
# ---------------------------------------------------------------------------


def test_parse_section_number_arabic():
    assert _parse_section_number("3.2.1 Title") == ("3.2.1", 3)
    assert _parse_section_number("3 Title") == ("3", 1)
    assert _parse_section_number("1. Introduction") == ("1", 1)


def test_parse_section_number_appendix():
    number, depth = _parse_section_number("A. Appendix Title")
    assert number == "A"
    assert depth == 1


def test_parse_section_number_none():
    assert _parse_section_number("Abstract") == ("", 0)
    assert _parse_section_number("Introduction") == ("", 0)


# ---------------------------------------------------------------------------
# _classify_section_type
# ---------------------------------------------------------------------------


def test_classify_abstract():
    assert _classify_section_type("", "Abstract") == "abstract"


def test_classify_introduction():
    assert _classify_section_type("1", "Introduction") == "introduction"
    assert _classify_section_type("", "Introduction") == "introduction"


def test_classify_related_work():
    assert _classify_section_type("2", "Related Work") == "related_work"
    assert _classify_section_type("2", "Background and Motivation") == "related_work"


def test_classify_method():
    assert _classify_section_type("3", "Our Method") == "method"
    assert _classify_section_type("3", "Proposed Framework") == "method"


def test_classify_experiment():
    assert _classify_section_type("4", "Experiments") == "experiment"
    assert _classify_section_type("4", "Evaluation") == "experiment"
    assert _classify_section_type("4", "Ablation Study") == "experiment"


def test_classify_conclusion():
    assert _classify_section_type("5", "Conclusion") == "conclusion"
    assert _classify_section_type("6", "Discussion and Future Work") == "conclusion"


def test_classify_appendix():
    assert _classify_section_type("A", "Experimental Details") == "appendix"
    assert _classify_section_type("", "Appendix A") == "appendix"


# ---------------------------------------------------------------------------
# _preprocess
# ---------------------------------------------------------------------------

_SAMPLE_WITH_REFS = """\
## **Abstract**

This is the abstract.

## **1. Introduction**

This is the introduction.

## **References**

[1] Smith et al. 2024.
[2] Jones et al. 2023.

## **A. Appendix**

Extra results here.
"""


def test_preprocess_strips_references():
    result = _preprocess(_SAMPLE_WITH_REFS)
    assert "Smith et al." not in result
    assert "Jones et al." not in result


def test_preprocess_keeps_appendix_after_references():
    result = _preprocess(_SAMPLE_WITH_REFS)
    assert "Extra results here." in result


def test_preprocess_strips_page_numbers():
    text = "Some content.\n\n5\n\nMore content."
    result = _preprocess(text)
    assert "\n5\n" not in result
    assert "Some content." in result
    assert "More content." in result


def test_preprocess_strips_repeated_title():
    title = "My Paper Title"
    text = f"Intro text.\n\n{title}\n\nMore text."
    result = _preprocess(text, document_title=title)
    # Title line should be removed; surrounding content kept
    lines = [line.strip() for line in result.splitlines() if line.strip()]
    assert title not in lines
    assert "Intro text." in result
    assert "More text." in result


# ---------------------------------------------------------------------------
# _merge_equation_context
# ---------------------------------------------------------------------------

_EQ_PLACEHOLDER = "**==> picture [221 x 13] intentionally omitted <==**"


def test_merge_standalone_equation_into_preceding():
    paras = [
        _Para(text="The formula is:", is_atomic=False),
        _Para(text=_EQ_PLACEHOLDER, is_atomic=True),
    ]
    result = _merge_equation_context(paras)
    assert len(result) == 1
    assert _EQ_PLACEHOLDER in result[0].text
    assert "The formula is:" in result[0].text


def test_merge_continuation_after_equation():
    paras = [
        _Para(text="The loss is:", is_atomic=False),
        _Para(text=_EQ_PLACEHOLDER, is_atomic=True),
        _Para(text="where θ are the model parameters.", is_atomic=False),
    ]
    result = _merge_equation_context(paras)
    assert len(result) == 1
    assert "where θ are the model parameters." in result[0].text


def test_no_merge_when_no_preceding_paragraph():
    paras = [
        _Para(text=_EQ_PLACEHOLDER, is_atomic=True),
    ]
    result = _merge_equation_context(paras)
    assert len(result) == 1
    assert result[0].is_atomic


# ---------------------------------------------------------------------------
# _merge_orphans
# ---------------------------------------------------------------------------


def test_merge_orphans_absorbs_short_chunks():
    # Each long chunk must exceed MIN_TOKENS (50); "tiny" is well below it
    long = "word " * 60  # ~60 tokens
    chunks = [long, "tiny", long]
    result = _merge_orphans(chunks, min_tokens=MIN_TOKENS)
    assert len(result) == 2
    assert "tiny" in result[0]


def test_merge_orphans_keeps_adequate_chunks():
    long = "word " * 60
    chunks = [long, long]
    result = _merge_orphans(chunks, min_tokens=MIN_TOKENS)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# chunk_markdown — integration
# ---------------------------------------------------------------------------

_MINIMAL_PAPER = """\
# My Paper Title

**Author One**[1]

> 1 Some University

## **Abstract**

We propose a new method for doing things.
It works well on benchmarks.

## **1. Introduction**

Large language models have changed everything.
We build on prior work to address remaining challenges.
Our contributions are threefold.

## **2. Related Work**

Previous approaches include A and B.

## **3. Method**

### **3.1. Overview**

Our method works as follows.

### **3.2. Details**

We use a transformer backbone.
The key insight is that attention is all you need.

## **4. Experiments**

We evaluate on three benchmarks.

## **5. Conclusion**

We presented a new method.
Future work will extend this.

## **References**

[1] LeCun et al. 1989.
[2] Vaswani et al. 2017.
"""


def test_chunk_markdown_returns_chunks():
    chunks = chunk_markdown(_MINIMAL_PAPER)
    assert len(chunks) > 0


def test_chunk_markdown_abstract_is_single_chunk():
    chunks = chunk_markdown(_MINIMAL_PAPER)
    abstract_chunks = [c for c in chunks if c.section_type == "abstract"]
    assert len(abstract_chunks) == 1


def test_chunk_markdown_references_excluded():
    chunks = chunk_markdown(_MINIMAL_PAPER)
    for chunk in chunks:
        assert "LeCun et al." not in chunk.text
        assert "Vaswani et al." not in chunk.text


def test_chunk_markdown_section_types_populated():
    chunks = chunk_markdown(_MINIMAL_PAPER)
    types = {c.section_type for c in chunks}
    assert "abstract" in types
    assert "introduction" in types


def test_chunk_markdown_no_chunk_exceeds_max_tokens():
    chunks = chunk_markdown(_MINIMAL_PAPER)
    for chunk in chunks:
        # Atomic oversized blocks may exceed the limit; normal chunks must not
        if not chunk.has_equations and not chunk.has_tables:
            assert _count_tokens(chunk.text) <= MAX_TOKENS * 1.1, (
                f"Chunk exceeded token budget: {_count_tokens(chunk.text)} tokens\n{chunk.text[:200]}"
            )


def test_chunk_markdown_section_numbers_parsed():
    chunks = chunk_markdown(_MINIMAL_PAPER)
    numbered = [c for c in chunks if c.section_number]
    assert len(numbered) > 0


def test_chunk_markdown_block_flags():
    # Table must be in a section body with enough tokens to survive the orphan filter.
    # We replace the short experiments body with a realistic paragraph + table.
    long_experiments_body = (
        "We evaluate on three benchmarks covering reasoning, factuality, and robustness. "
        "Baseline models include GPT-4, LLaMA-3, and Gemma-2. "
        "Results are shown in Table 1. Our method outperforms all baselines by a significant margin "
        "on every benchmark, demonstrating the effectiveness of the proposed approach.\n\n"
        "_Table 1._ **Main results across benchmarks.**\n\n"
        "| Model | Reasoning | Factuality |\n"
        "|---|---|---|\n"
        "| Baseline | 72.1 | 68.4 |\n"
        "| Ours | 85.3 | 81.9 |"
    )
    paper_with_table = _MINIMAL_PAPER.replace(
        "We evaluate on three benchmarks.", long_experiments_body
    )
    chunks = chunk_markdown(paper_with_table)
    table_chunks = [c for c in chunks if c.has_tables]
    assert len(table_chunks) > 0
