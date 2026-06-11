from app.services.belief_engine import build_belief_snapshot


def test_belief_explanation_is_derived_and_non_empty():
    snapshot = build_belief_snapshot("GOOGL", "2026-06-11T12:00:00Z")

    assert snapshot.explanation.summary
    assert str(snapshot.belief.score) not in snapshot.explanation.summary or snapshot.asset.symbol in snapshot.explanation.summary
    assert len(snapshot.explanation.drivers) >= 3
    assert snapshot.narratives[0].title in " ".join(snapshot.explanation.drivers)
    assert any("demo" in warning.lower() for warning in snapshot.explanation.warnings)
