import pytest

from satquery.registry import get_tool, load_registry, tool_for_task, tools_summary
from satquery.schemas import TaskType


def test_registry_loads():
    reg = load_registry()
    assert len(reg.tools) >= 8


def test_every_task_has_tool():
    for task in TaskType:
        spec = tool_for_task(task)
        assert spec.task == task


def test_only_landcover_marked_trained():
    trained = [t.name for t in load_registry().tools if t.trained]
    assert trained == ["landcover"]


def test_get_tools_payload_jsonable():
    payload = tools_summary()
    assert all("name" in t and "task" in t for t in payload)


def test_unknown_tool_raises():
    with pytest.raises(KeyError):
        get_tool("does_not_exist")
