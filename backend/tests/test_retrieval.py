from backend.kb.retrieval import rag_query


def test_rag_query_returns_cited_crop_evidence():
    result = rag_query("potato irrigation calendar pest checkpoints", crop="potato")
    assert result["matches"]
    match = result["matches"][0]
    assert match["source_type"] == "kb"
    assert match["locator"]
    assert "irrigate" in match["text"].lower()


def test_rag_query_rejects_unknown_crop_without_guessing():
    assert "error" in rag_query("crop calendar", crop="maize")
