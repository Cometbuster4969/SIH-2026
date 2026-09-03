from satquery.schemas import Trace
from satquery.trace import TraceStore


def test_trace_persists_and_reloads(tmp_path):
    db = tmp_path / "t.db"
    store = TraceStore(db)
    trace = Trace(query="Is there water?")
    store.add_event(trace, "route", "ok", tool="vqa_single", message="routed")
    store.add_event(trace, "execute", "degraded", tool="vqa_single",
                    message="heuristic")
    store.save(trace, "degraded")

    got = store.get(trace.query_id)
    assert got is not None
    assert got["query"] == "Is there water?"
    assert len(got["events"]) == 2
    assert [r["query_id"] for r in store.recent()] == [trace.query_id]
    store.close()
