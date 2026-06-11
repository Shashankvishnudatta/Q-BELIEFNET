from app.services.belief_engine import PROTOTYPE_NOTE, build_belief_snapshot


def test_belief_snapshot_metrics_are_bounded():
    snapshot = build_belief_snapshot("NVDA")

    assert 0 <= snapshot.belief.score <= 100
    assert -100 <= snapshot.belief.velocity <= 100
    assert 0 <= snapshot.belief.coherence <= 1
    assert 0 <= snapshot.belief.fragility <= 1
    assert 0 <= snapshot.breakdown.attention <= 100
    assert 0 <= snapshot.breakdown.source_agreement <= 100


def test_belief_snapshot_is_stable_for_same_symbol_and_window():
    first = build_belief_snapshot("AAPL", "2026-06-11T12:00:00Z")
    second = build_belief_snapshot("AAPL", "2026-06-11T12:00:00Z")

    assert first.belief.score == second.belief.score
    assert first.breakdown == second.breakdown
    assert [item.text for item in first.evidence] == [item.text for item in second.evidence]


def test_demo_evidence_is_clearly_labeled():
    snapshot = build_belief_snapshot("MSFT")

    assert snapshot.evidence
    assert all(item.source_name == "internal-demo-generator" for item in snapshot.evidence)
    assert all(item.note == PROTOTYPE_NOTE for item in snapshot.evidence)
    assert "not financial advice" in " ".join(snapshot.explanation.warnings).lower()
