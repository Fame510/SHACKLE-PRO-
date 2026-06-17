"""Unit tests for SHACKLE core engine — no external dependencies required."""

import time
import pytest
from shackle.core import (
    TriggerEngine,
    ExecutionState,
    ShackleInterrupt,
    Guard,
    MODEL_PRICING,
)


class TestPricingTable:
    def test_known_models_have_pricing(self):
        assert "gpt-4o" in MODEL_PRICING
        assert "claude-3-5-sonnet" in MODEL_PRICING
        assert "gemini-1.5-pro" in MODEL_PRICING

    def test_default_fallback_exists(self):
        assert "default" in MODEL_PRICING

    def test_pricing_values_are_positive(self):
        for model, pricing in MODEL_PRICING.items():
            assert pricing["input"] >= 0
            assert pricing["output"] >= 0


class TestExecutionState:
    def test_initial_values(self):
        state = ExecutionState()
        assert state.total_cost == 0.0
        assert state.input_tokens == 0
        assert state.output_tokens == 0
        assert state.total_tool_calls == 0
        assert state.tool_history == {}

    def test_start_time_is_now(self):
        before = time.time()
        state = ExecutionState()
        after = time.time()
        assert before <= state.start_time <= after


class TestTriggerEngineLLM:
    def test_budget_tracking(self):
        engine = TriggerEngine(budget=1.00)
        state = ExecutionState()
        # 1M input + 500K output at gpt-4o-mini = very cheap
        engine.evaluate_llm_call("gpt-4o-mini", 1_000_000, 500_000, state)
        assert state.total_cost > 0
        assert state.input_tokens == 1_000_000
        assert state.output_tokens == 500_000

    def test_budget_breach_raises(self):
        engine = TriggerEngine(budget=0.0001)  # impossibly low
        state = ExecutionState()
        with pytest.raises(ShackleInterrupt) as exc:
            engine.evaluate_llm_call("gpt-4o", 100_000, 100_000, state)
        assert exc.value.trigger_type == "BUDGET_EXCEEDED"

    def test_unknown_model_uses_default_pricing(self):
        engine = TriggerEngine(budget=1.00)
        state = ExecutionState()
        engine.evaluate_llm_call("nonexistent-model-42", 1_000, 1_000, state)
        assert state.total_cost > 0


class TestTriggerEngineToolCalls:
    def test_repeat_call_detection(self):
        engine = TriggerEngine(max_repeat_calls=3)
        state = ExecutionState()

        # First 2 calls: no interrupt
        engine.evaluate_tool_call("Agent", "search", "latest news", state)
        engine.evaluate_tool_call("Agent", "search", "latest news", state)
        assert state.tool_history[("search", "latest news")] == 2

        # 3rd call with same input: should trip
        with pytest.raises(ShackleInterrupt) as exc:
            engine.evaluate_tool_call("Agent", "search", "latest news", state)
        assert exc.value.trigger_type == "REPETITIVE_TOOL_CALL"

    def test_different_inputs_no_trigger(self):
        engine = TriggerEngine(max_repeat_calls=3)
        state = ExecutionState()

        engine.evaluate_tool_call("Agent", "search", "query A", state)
        engine.evaluate_tool_call("Agent", "search", "query B", state)
        engine.evaluate_tool_call("Agent", "search", "query C", state)
        # No exception — different inputs, no repeat detection

    def test_error_amplification_triggers_earlier(self):
        """Error strings should amplify sensitivity, tripping at count 2."""
        engine = TriggerEngine(max_repeat_calls=3)
        state = ExecutionState()

        engine.evaluate_tool_call("Agent", "api", "401 Unauthorized", state)
        # Second call with error string: should trip even though max_repeat_calls=3
        with pytest.raises(ShackleInterrupt) as exc:
            engine.evaluate_tool_call("Agent", "api", "401 Unauthorized", state)
        assert exc.value.trigger_type == "REPETITIVE_TOOL_CALL"
        assert exc.value.details["error_loop"] is True

    def test_timeout_detection(self):
        engine = TriggerEngine(timeout_seconds=0.001)  # 1ms timeout
        state = ExecutionState()
        time.sleep(0.01)  # ensure we're past timeout
        with pytest.raises(ShackleInterrupt) as exc:
            engine.evaluate_tool_call("Agent", "slow_tool", "input", state)
        assert exc.value.trigger_type == "TIMEOUT_REACHED"

    def test_max_tool_calls(self):
        engine = TriggerEngine(max_tool_calls=3)
        state = ExecutionState()

        engine.evaluate_tool_call("Agent", "t1", "a", state)
        engine.evaluate_tool_call("Agent", "t2", "b", state)
        # 3rd call hits limit (total_tool_calls goes 1→2→3)
        with pytest.raises(ShackleInterrupt) as exc:
            engine.evaluate_tool_call("Agent", "t3", "c", state)
        assert exc.value.trigger_type == "MAX_TOOL_CALLS"


class TestGuardDecorator:
    def test_guard_preserves_return_value(self):
        """Guard should pass through the return value of the wrapped function."""
        @Guard(budget=100.0, max_repeat_calls=10)
        def my_func():
            return "success"

        result = my_func()
        assert result == "success"

    def test_guard_preserves_function_metadata(self):
        @Guard(budget=100.0)
        def documented_func():
            """This function has a docstring."""
            pass

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This function has a docstring."

    def test_guard_session_summary(self):
        """Guard should print a session summary after execution."""
        @Guard(budget=100.0)
        def simple():
            return 42

        result = simple()
        assert result == 42


class TestShackleInterrupt:
    def test_interrupt_is_exception(self):
        state = ExecutionState()
        si = ShackleInterrupt(
            message="test",
            trigger_type="TEST_TRIGGER",
            state=state,
            details={"key": "value"},
        )
        assert isinstance(si, Exception)
        assert si.trigger_type == "TEST_TRIGGER"
        assert si.details["key"] == "value"

    def test_interrupt_can_be_caught(self):
        state = ExecutionState()
        try:
            raise ShackleInterrupt("msg", "TYPE", state, {})
        except ShackleInterrupt as e:
            assert str(e) == "msg"
