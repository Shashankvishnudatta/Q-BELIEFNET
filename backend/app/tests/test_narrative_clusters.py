from app.services.belief_engine import build_belief_snapshot


def test_narrative_clusters_have_explainable_fields():
    snapshot = build_belief_snapshot("TSLA", "2026-06-11T12:00:00Z")

    assert snapshot.narratives
    cluster = snapshot.narratives[0]
    assert cluster.title
    assert 0 <= cluster.strength <= 1
    assert cluster.evidence_count > 0
    assert cluster.keywords
    assert cluster.representative_evidence
    assert cluster.trend_direction in {"up", "down", "flat", "mixed"}
