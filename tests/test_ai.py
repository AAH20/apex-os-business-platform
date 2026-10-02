"""Tests for the AI agent system."""

import asyncio
import json
import os
import tempfile
import time

import pytest

from apex_os_bp.ai import (
    Agent,
    AgentOrchestrator,
    AgentResult,
    AgentStatus,
    MemoryEntry,
    MemoryManager,
    MemoryType,
    Plan,
    PlanStatus,
    PlanStep,
    Planner,
    ReflectionEngine,
    ReflectionLevel,
    ReflectionResult,
    Tool,
    ToolError,
    ToolRegistry,
    ToolResult,
)


# ── Orchestrator Tests ──────────────────────────────────────────────


class TestAgent:
    def test_agent_creation(self):
        agent = Agent(name="test", role="tester", capabilities=["test"])
        assert agent.name == "test"
        assert agent.role == "tester"
        assert "test" in agent.capabilities
        assert agent.status == AgentStatus.PENDING

    def test_agent_execute_success(self):
        async def handler(task, ctx):
            return f"done: {task}"

        agent = Agent(name="test", role="tester", handler=handler)
        result = asyncio.run(agent.execute("my task"))
        assert result.success
        assert result.output == "done: my task"
        assert result.status == AgentStatus.COMPLETED
        assert result.duration >= 0

    def test_agent_execute_failure(self):
        async def handler(task, ctx):
            raise ValueError("boom")

        agent = Agent(name="test", role="tester", handler=handler)
        result = asyncio.run(agent.execute("task"))
        assert not result.success
        assert result.status == AgentStatus.FAILED
        assert "boom" in result.error

    def test_agent_no_handler(self):
        agent = Agent(name="test", role="tester")
        result = asyncio.run(agent.execute("task"))
        assert not result.success
        assert "no handler" in result.error.lower()


class TestAgentOrchestrator:
    def test_register_and_list(self):
        orch = AgentOrchestrator()
        agent = Agent(name="a1", role="worker", capabilities=["compute"])
        orch.register_agent(agent)
        assert len(orch.list_agents()) == 1
        assert orch.get_agent(agent.agent_id) is agent

    def test_unregister(self):
        orch = AgentOrchestrator()
        agent = Agent(name="a1", role="worker")
        orch.register_agent(agent)
        assert orch.unregister_agent(agent.agent_id) is True
        assert orch.get_agent(agent.agent_id) is None
        assert orch.unregister_agent("nonexistent") is False

    def test_find_by_capability(self):
        orch = AgentOrchestrator()
        agent = Agent(name="a1", role="worker", capabilities=["compute", "search"])
        orch.register_agent(agent)
        found = orch.find_agent_by_capability("search")
        assert found is agent
        assert orch.find_agent_by_capability("nonexistent") is None

    def test_find_by_role(self):
        orch = AgentOrchestrator()
        a1 = Agent(name="a1", role="worker")
        a2 = Agent(name="a2", role="worker")
        a3 = Agent(name="a3", role="reviewer")
        orch.register_agent(a1)
        orch.register_agent(a2)
        orch.register_agent(a3)
        workers = orch.find_agents_by_role("worker")
        assert len(workers) == 2

    def test_execute_single(self):
        async def handler(task, ctx):
            return f"result: {task}"

        orch = AgentOrchestrator()
        agent = Agent(name="a1", role="worker", handler=handler)
        orch.register_agent(agent)
        result = asyncio.run(orch.execute_single(agent.agent_id, "do something"))
        assert result.success
        assert result.output == "result: do something"

    def test_execute_single_not_found(self):
        orch = AgentOrchestrator()
        result = asyncio.run(orch.execute_single("bad_id", "task"))
        assert not result.success
        assert "not found" in result.error.lower()

    def test_execute_parallel(self):
        async def handler(task, ctx):
            await asyncio.sleep(0.01)
            return f"done: {task}"

        orch = AgentOrchestrator()
        a1 = Agent(name="a1", role="w", handler=handler)
        a2 = Agent(name="a2", role="w", handler=handler)
        orch.register_agent(a1)
        orch.register_agent(a2)
        tasks = [
            (a1.agent_id, "task1", None),
            (a2.agent_id, "task2", None),
        ]
        results = asyncio.run(orch.execute_parallel(tasks))
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_execute_sequential(self):
        async def handler(task, ctx):
            return f"processed: {task}"

        orch = AgentOrchestrator()
        a1 = Agent(name="a1", role="w", handler=handler)
        a2 = Agent(name="a2", role="w", handler=handler)
        orch.register_agent(a1)
        orch.register_agent(a2)
        tasks = [
            (a1.agent_id, "first", None),
            (a2.agent_id, "second", None),
        ]
        results = asyncio.run(orch.execute_sequential(tasks))
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_route_and_execute(self):
        async def handler(task, ctx):
            return f"routed: {task}"

        orch = AgentOrchestrator()
        agent = Agent(name="a1", role="worker", capabilities=["compute"], handler=handler)
        orch.register_agent(agent)
        result = asyncio.run(orch.route_and_execute("do math", "compute"))
        assert result.success
        assert result.output == "routed: do math"

    def test_route_and_execute_no_agent(self):
        orch = AgentOrchestrator()
        result = asyncio.run(orch.route_and_execute("task", "nonexistent"))
        assert not result.success
        assert "no agent found" in result.error.lower()

    def test_history_and_success_rate(self):
        async def handler(task, ctx):
            return "ok"

        orch = AgentOrchestrator()
        agent = Agent(name="a1", role="w", handler=handler)
        orch.register_agent(agent)
        asyncio.run(orch.execute_single(agent.agent_id, "t1"))
        asyncio.run(orch.execute_single(agent.agent_id, "t2"))
        assert len(orch.get_history()) == 2
        assert orch.get_success_rate() == 1.0
        orch.clear_history()
        assert len(orch.get_history()) == 0

    def test_success_rate_empty(self):
        orch = AgentOrchestrator()
        assert orch.get_success_rate() == 0.0


# ── Tool Integration Tests ──────────────────────────────────────────


class TestTool:
    def test_tool_creation(self):
        def handler(x, y):
            return x + y

        tool = Tool(name="add", description="Add two numbers", handler=handler)
        assert tool.name == "add"
        assert not tool.is_async

    def test_tool_async_detection(self):
        async def handler(x):
            return x

        tool = Tool(name="async_op", description="Async op", handler=handler)
        assert tool.is_async

    def test_tool_execute_sync(self):
        def handler(x, y):
            return x + y

        tool = Tool(name="add", description="Add", handler=handler)
        result = asyncio.run(tool.execute(x=1, y=2))
        assert result.success
        assert result.output == 3

    def test_tool_execute_async(self):
        async def handler(x):
            return x * 2

        tool = Tool(name="double", description="Double", handler=handler)
        result = asyncio.run(tool.execute(x=5))
        assert result.success
        assert result.output == 10

    def test_tool_execute_error(self):
        def handler():
            raise RuntimeError("fail")

        tool = Tool(name="bad", description="Bad tool", handler=handler)
        result = asyncio.run(tool.execute())
        assert not result.success
        assert "fail" in result.error

    def test_tool_validate_parameters(self):
        def handler(x: int, y: str):
            return f"{x}{y}"

        tool = Tool(
            name="concat",
            description="Concat",
            handler=handler,
            parameters={
                "required": ["x", "y"],
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "string"},
                },
            },
        )
        assert tool.validate_parameters(x=1, y="a") == []
        errors = tool.validate_parameters(x="wrong", y="a")
        assert len(errors) == 1
        assert "x" in errors[0]
        errors = tool.validate_parameters(x=1)
        assert len(errors) == 1
        assert "y" in errors[0]


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = Tool(name="t1", description="Test", handler=lambda: None)
        reg.register(tool)
        assert reg.get("t1") is tool
        assert reg.has_tool("t1")
        assert reg.count == 1

    def test_unregister(self):
        reg = ToolRegistry()
        tool = Tool(name="t1", description="Test", handler=lambda: None)
        reg.register(tool)
        assert reg.unregister("t1") is True
        assert reg.count == 0
        assert reg.unregister("t1") is False

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(Tool(name="a", description="A", handler=lambda: None))
        reg.register(Tool(name="b", description="B", handler=lambda: None))
        assert len(reg.list_tools()) == 2

    def test_list_by_tag(self):
        reg = ToolRegistry()
        reg.register(Tool(name="a", description="A", handler=lambda: None, tags=["math"]))
        reg.register(Tool(name="b", description="B", handler=lambda: None, tags=["text"]))
        assert len(reg.list_by_tag("math")) == 1
        assert reg.list_by_tag("math")[0].name == "a"

    def test_execute(self):
        reg = ToolRegistry()
        reg.register(Tool(name="add", description="Add", handler=lambda x, y: x + y))
        result = asyncio.run(reg.execute("add", x=3, y=4))
        assert result.success
        assert result.output == 7

    def test_execute_not_found(self):
        reg = ToolRegistry()
        result = asyncio.run(reg.execute("nonexistent"))
        assert not result.success
        assert "not found" in result.error.lower()

    def test_execute_validation_failure(self):
        reg = ToolRegistry()
        reg.register(Tool(
            name="add",
            description="Add",
            handler=lambda x, y: x + y,
            parameters={"required": ["x", "y"]},
        ))
        result = asyncio.run(reg.execute("add", x=1))
        assert not result.success
        assert "validation failed" in result.error.lower()

    def test_execute_many(self):
        reg = ToolRegistry()
        reg.register(Tool(name="a", description="A", handler=lambda: 1))
        reg.register(Tool(name="b", description="B", handler=lambda: 2))
        results = asyncio.run(reg.execute_many([("a", {}), ("b", {})]))
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_search(self):
        reg = ToolRegistry()
        reg.register(Tool(name="calculator", description="Math calc", handler=lambda: None))
        reg.register(Tool(name="search_web", description="Web search", handler=lambda: None))
        results = reg.search("calc")
        assert len(results) == 1
        assert results[0].name == "calculator"

    def test_clear(self):
        reg = ToolRegistry()
        reg.register(Tool(name="a", description="A", handler=lambda: None))
        reg.clear()
        assert reg.count == 0


# ── Memory Management Tests ─────────────────────────────────────────


class TestMemoryEntry:
    def test_creation(self):
        entry = MemoryEntry(content="test", memory_type=MemoryType.SHORT_TERM)
        assert entry.content == "test"
        assert entry.importance == 0.5
        assert entry.access_count == 0

    def test_touch(self):
        entry = MemoryEntry(content="test", memory_type=MemoryType.SHORT_TERM)
        entry.touch()
        assert entry.access_count == 1
        assert entry.last_accessed > 0

    def test_serialization(self):
        entry = MemoryEntry(content="test", memory_type=MemoryType.LONG_TERM, importance=0.8)
        d = entry.to_dict()
        assert d["content"] == "test"
        assert d["memory_type"] == "long_term"
        restored = MemoryEntry.from_dict(d)
        assert restored.content == entry.content
        assert restored.memory_type == entry.memory_type


class TestMemoryManager:
    def test_add_short_term(self):
        mm = MemoryManager()
        entry = mm.add("hello world", MemoryType.SHORT_TERM)
        assert entry.memory_type == MemoryType.SHORT_TERM
        assert len(mm._short_term) == 1

    def test_add_long_term(self):
        mm = MemoryManager()
        entry = mm.add("permanent fact", MemoryType.LONG_TERM)
        assert entry.memory_type == MemoryType.LONG_TERM
        assert len(mm._long_term) == 1

    def test_search(self):
        mm = MemoryManager()
        mm.add("the cat sat on the mat", MemoryType.SHORT_TERM)
        mm.add("dogs are great pets", MemoryType.SHORT_TERM)
        results = mm.search("cat")
        assert len(results) >= 1
        assert any("cat" in r.content for r in results)

    def test_search_with_type_filter(self):
        mm = MemoryManager()
        mm.add("short term data", MemoryType.SHORT_TERM)
        mm.add("long term data", MemoryType.LONG_TERM)
        results = mm.search("data", memory_type=MemoryType.LONG_TERM)
        assert len(results) == 1
        assert results[0].memory_type == MemoryType.LONG_TERM

    def test_get_recent(self):
        mm = MemoryManager()
        mm.add("first", MemoryType.SHORT_TERM)
        time.sleep(0.01)
        mm.add("second", MemoryType.SHORT_TERM)
        recent = mm.get_recent(limit=1)
        assert recent[0].content == "second"

    def test_get_by_id(self):
        mm = MemoryManager()
        entry = mm.add("find me", MemoryType.SHORT_TERM)
        found = mm.get_by_id(entry.entry_id)
        assert found is not None
        assert found.content == "find me"
        assert mm.get_by_id("nonexistent") is None

    def test_forget(self):
        mm = MemoryManager()
        entry = mm.add("delete me", MemoryType.SHORT_TERM)
        assert mm.forget(entry.entry_id) is True
        assert mm.get_by_id(entry.entry_id) is None
        assert mm.forget(entry.entry_id) is False

    def test_clear(self):
        mm = MemoryManager()
        mm.add("st", MemoryType.SHORT_TERM)
        mm.add("lt", MemoryType.LONG_TERM)
        mm.clear()
        assert len(mm._short_term) == 0
        assert len(mm._long_term) == 0

    def test_clear_by_type(self):
        mm = MemoryManager()
        mm.add("st", MemoryType.SHORT_TERM)
        mm.add("lt", MemoryType.LONG_TERM)
        mm.clear(MemoryType.SHORT_TERM)
        assert len(mm._short_term) == 0
        assert len(mm._long_term) == 1

    def test_promote(self):
        mm = MemoryManager()
        entry = mm.add("promote me", MemoryType.SHORT_TERM)
        assert mm.promote(entry.entry_id) is True
        assert entry.memory_type == MemoryType.LONG_TERM
        assert len(mm._long_term) == 1
        assert len(mm._short_term) == 0

    def test_promote_not_found(self):
        mm = MemoryManager()
        assert mm.promote("nonexistent") is False

    def test_context_window(self):
        mm = MemoryManager()
        mm.add("fact one", MemoryType.SHORT_TERM)
        mm.add("fact two", MemoryType.LONG_TERM)
        ctx = mm.get_context_window()
        assert "fact one" in ctx
        assert "fact two" in ctx

    def test_eviction_short_term(self):
        mm = MemoryManager(short_term_capacity=3)
        mm.add("low", MemoryType.SHORT_TERM, importance=0.1)
        mm.add("mid", MemoryType.SHORT_TERM, importance=0.5)
        mm.add("high", MemoryType.SHORT_TERM, importance=0.9)
        mm.add("new", MemoryType.SHORT_TERM, importance=0.8)
        assert len(mm._short_term) == 3
        contents = [e.content for e in mm._short_term]
        assert "low" not in contents

    def test_persist_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mm = MemoryManager(persist_path=path)
            mm.add("persisted data", MemoryType.LONG_TERM, importance=0.9)
            mm.persist()

            mm2 = MemoryManager(persist_path=path)
            results = mm2.search("persisted")
            assert len(results) == 1
            assert results[0].content == "persisted data"
        finally:
            os.unlink(path)

    def test_stats(self):
        mm = MemoryManager()
        mm.add("st", MemoryType.SHORT_TERM)
        mm.add("lt", MemoryType.LONG_TERM)
        stats = mm.get_stats()
        assert stats["short_term_count"] == 1
        assert stats["long_term_count"] == 1
        assert stats["total_count"] == 2


# ── Planning Tests ──────────────────────────────────────────────────


class TestPlanStep:
    def test_creation(self):
        step = PlanStep(description="do something")
        assert step.status == PlanStatus.PENDING
        assert step.duration == 0.0

    def test_lifecycle(self):
        step = PlanStep(description="task")
        step.start()
        assert step.status == PlanStatus.IN_PROGRESS
        assert step.started_at > 0
        step.complete(result="done")
        assert step.status == PlanStatus.COMPLETED
        assert step.result == "done"
        assert step.duration >= 0

    def test_fail(self):
        step = PlanStep(description="task")
        step.start()
        step.fail("error occurred")
        assert step.status == PlanStatus.FAILED
        assert step.error == "error occurred"

    def test_block_and_skip(self):
        step = PlanStep(description="task")
        step.block()
        assert step.status == PlanStatus.BLOCKED
        step.skip()
        assert step.status == PlanStatus.SKIPPED


class TestPlan:
    def test_progress(self):
        plan = Plan(goal="test")
        plan.add_step(PlanStep(description="s1"))
        plan.add_step(PlanStep(description="s2"))
        assert plan.progress == 0.0
        plan.steps[0].complete()
        assert plan.progress == 0.5
        plan.steps[1].complete()
        assert plan.progress == 1.0

    def test_is_complete(self):
        plan = Plan(goal="test")
        plan.add_step(PlanStep(description="s1"))
        assert not plan.is_complete
        plan.steps[0].complete()
        assert plan.is_complete

    def test_has_failures(self):
        plan = Plan(goal="test")
        plan.add_step(PlanStep(description="s1"))
        assert not plan.has_failures
        plan.steps[0].fail("err")
        assert plan.has_failures

    def test_get_ready_steps(self):
        plan = Plan(goal="test")
        s1 = PlanStep(description="s1")
        s2 = PlanStep(description="s2", dependencies=[s1.step_id])
        plan.add_step(s1)
        plan.add_step(s2)
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0] is s1
        s1.complete()
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0] is s2

    def test_to_dict(self):
        plan = Plan(goal="test goal")
        plan.add_step(PlanStep(description="step 1"))
        d = plan.to_dict()
        assert d["goal"] == "test goal"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["description"] == "step 1"


class TestPlanner:
    def test_create_plan(self):
        planner = Planner()
        plan = planner.create_plan("test goal")
        assert plan.goal == "test goal"
        assert planner.get_plan(plan.plan_id) is plan

    def test_decompose(self):
        planner = Planner()
        plan = planner.decompose(
            goal="build app",
            sub_tasks=["design", "implement", "test"],
            dependencies={1: [0], 2: [1]},
        )
        assert len(plan.steps) == 3
        assert plan.steps[1].dependencies == [plan.steps[0].step_id]
        assert plan.steps[2].dependencies == [plan.steps[1].step_id]

    def test_get_execution_order(self):
        planner = Planner()
        plan = planner.decompose(
            goal="test",
            sub_tasks=["a", "b", "c"],
            dependencies={2: [0, 1]},
        )
        order = planner.get_execution_order(plan.plan_id)
        assert len(order) == 3
        ids = [s.step_id for s in order]
        assert ids[0] == plan.steps[0].step_id or ids[0] == plan.steps[1].step_id

    def test_execute_plan(self):
        planner = Planner()
        plan = planner.decompose(
            goal="test",
            sub_tasks=["step1", "step2"],
            dependencies={1: [0]},
        )

        def executor(step):
            return f"result of {step.description}"

        executed = planner.execute_plan(plan.plan_id, executor)
        assert executed.status == PlanStatus.COMPLETED
        assert executed.is_complete
        assert executed.steps[0].result == "result of step1"

    def test_execute_plan_with_failure(self):
        planner = Planner()
        plan = planner.decompose(goal="test", sub_tasks=["s1", "s2"])

        def executor(step):
            if step.description == "s1":
                raise RuntimeError("fail")
            return "ok"

        executed = planner.execute_plan(plan.plan_id, executor)
        assert executed.status == PlanStatus.FAILED
        assert executed.has_failures

    def test_cancel_plan(self):
        planner = Planner()
        plan = planner.decompose(goal="test", sub_tasks=["s1", "s2"])
        assert planner.cancel_plan(plan.plan_id) is True
        assert plan.status == PlanStatus.FAILED
        assert plan.steps[0].status == PlanStatus.SKIPPED

    def test_cancel_nonexistent(self):
        planner = Planner()
        assert planner.cancel_plan("nonexistent") is False

    def test_list_plans(self):
        planner = Planner()
        planner.create_plan("goal1")
        planner.create_plan("goal2")
        assert len(planner.list_plans()) == 2

    def test_clear(self):
        planner = Planner()
        planner.create_plan("goal")
        planner.clear()
        assert len(planner.list_plans()) == 0


# ── Self-Reflection Tests ───────────────────────────────────────────


class TestExperience:
    def test_creation(self):
        from apex_os_bp.ai.reflection import Experience
        exp = Experience(task="test task", outcome="done", success=True, score=0.9)
        assert exp.task == "test task"
        assert exp.success is True
        assert exp.score == 0.9


class TestReflectionEngine:
    def test_record_experience(self):
        engine = ReflectionEngine()
        exp = engine.record_experience("task1", "done", True, 0.9)
        assert exp.task == "task1"
        assert exp.success is True
        assert len(engine._experiences) == 1

    def test_reflect_empty(self):
        engine = ReflectionEngine()
        result = engine.reflect()
        assert result.score == 0.0
        assert "no experiences" in result.summary.lower()

    def test_reflect_with_experiences(self):
        engine = ReflectionEngine()
        engine.record_experience("math task one", "ok", True, 0.9)
        engine.record_experience("math task two", "ok", True, 0.8)
        engine.record_experience("writing task three", "fail", False, 0.2)
        engine.record_experience("writing task four", "fail", False, 0.1)
        result = engine.reflect(level=ReflectionLevel.DETAILED)
        assert result.score > 0
        assert result.score < 1.0
        assert len(result.strengths) > 0
        assert len(result.weaknesses) > 0
        assert len(result.improvements) > 0

    def test_reflect_levels(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "ok", True, 0.9)
        engine.record_experience("t2", "fail", False, 0.1)

        surface = engine.reflect(level=ReflectionLevel.SURFACE)
        detailed = engine.reflect(level=ReflectionLevel.DETAILED)
        deep = engine.reflect(level=ReflectionLevel.DEEP)

        assert len(deep.improvements) >= len(detailed.improvements) >= len(surface.improvements)

    def test_overall_assessment(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "ok", True, 0.95)
        result = engine.reflect()
        assert result.overall_assessment == "excellent"

    def test_get_lessons_learned(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "fail", False, 0.1, feedback="be more careful")
        engine.reflect()
        lessons = engine.get_lessons_learned()
        assert len(lessons) > 0
        assert "be more careful" in lessons[0]

    def test_experience_stats(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "ok", True, 0.9)
        engine.record_experience("t2", "ok", True, 0.7)
        engine.record_experience("t3", "fail", False, 0.3)
        stats = engine.get_experience_stats()
        assert stats["total"] == 3
        assert stats["successes"] == 2
        assert stats["failures"] == 1
        assert 0 < stats["success_rate"] < 1

    def test_detect_patterns_consecutive_failures(self):
        engine = ReflectionEngine()
        for i in range(4):
            engine.record_experience(f"task{i}", "fail", False, 0.1)
        patterns = engine.detect_patterns()
        assert any(p["type"] == "consecutive_failures" for p in patterns)

    def test_detect_patterns_declining_performance(self):
        engine = ReflectionEngine()
        for i in range(5):
            engine.record_experience(f"task{i}", "ok", True, 0.9)
        for i in range(5):
            engine.record_experience(f"task{i+5}", "fail", False, 0.2)
        patterns = engine.detect_patterns()
        assert any(p["type"] == "declining_performance" for p in patterns)

    def test_detect_patterns_not_enough_data(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "ok", True, 0.5)
        assert engine.detect_patterns() == []

    def test_reflection_history(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "ok", True, 0.8)
        engine.reflect()
        engine.reflect()
        assert len(engine.get_reflection_history()) == 2

    def test_clear(self):
        engine = ReflectionEngine()
        engine.record_experience("t1", "ok", True, 0.8)
        engine.reflect()
        engine.clear()
        assert len(engine._experiences) == 0
        assert len(engine._reflections) == 0
        assert len(engine._lessons) == 0

    def test_max_experiences(self):
        engine = ReflectionEngine(max_experiences=5)
        for i in range(10):
            engine.record_experience(f"task{i}", "ok", True, 0.5)
        assert len(engine._experiences) == 5

    def test_reflect_with_task_filter(self):
        engine = ReflectionEngine()
        engine.record_experience("math task", "ok", True, 0.9)
        engine.record_experience("writing task", "fail", False, 0.2)
        result = engine.reflect(task_filter="math")
        assert result.metadata["total_experiences"] == 1
        assert result.score == 0.9
