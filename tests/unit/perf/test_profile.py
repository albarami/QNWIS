"""
Unit tests for qnwis.perf.profile module.

Tests Timer context manager and timeit decorator to ensure
they measure and record execution durations correctly.
"""

import time
from typing import Any, Dict

import pytest

from qnwis.perf.profile import Timer, timeit


class TestTimer:
    """Test Timer context manager."""

    def test_timer_measures_duration(self):
        """Timer should measure wall time in seconds."""
        recorded_data = {}

        def sink(name: str, duration: float, extra: Dict[str, Any]) -> None:
            recorded_data["name"] = name
            recorded_data["duration"] = duration
            recorded_data["extra"] = extra

        with Timer(sink, "test_op", {"key": "value"}):
            time.sleep(0.1)  # Sleep for 100ms

        assert recorded_data["name"] == "test_op"
        assert recorded_data["extra"] == {"key": "value"}
        # Allow some tolerance for timing variance
        assert 0.09 <= recorded_data["duration"] <= 0.15

    def test_timer_records_zero_duration_for_instant_op(self):
        """Timer should record near-zero duration for instant operations."""
        recorded_data = {}

        def sink(name: str, duration: float, extra: Dict[str, Any]) -> None:
            recorded_data["duration"] = duration

        with Timer(sink, "instant"):
            pass  # No operation

        assert recorded_data["duration"] < 0.01  # Less than 10ms

    def test_timer_stores_duration_attribute(self):
        """Timer should store duration in .duration attribute."""
        timer = Timer(lambda n, d, e: None, "test")

        with timer:
            time.sleep(0.05)

        assert 0.04 <= timer.duration <= 0.1

    def test_timer_handles_sink_failure_gracefully(self):
        """Timer should not raise if sink fails."""

        def failing_sink(name: str, duration: float, extra: Dict[str, Any]) -> None:
            raise ValueError("Sink error")

        # Should not raise
        with Timer(failing_sink, "test"):
            pass

    def test_timer_default_extra_is_empty_dict(self):
        """Timer should use empty dict for extra if not provided."""
        recorded_data = {}

        def sink(name: str, duration: float, extra: Dict[str, Any]) -> None:
            recorded_data["extra"] = extra

        with Timer(sink, "test"):
            pass

        assert recorded_data["extra"] == {}


class TestTimeitDecorator:
    """Test timeit decorator."""

    def test_timeit_measures_function_execution(self, caplog):
        """Timeit decorator should log execution time."""

        @timeit("fetch_data", {"source": "test"})
        def fetch_data():
            time.sleep(0.05)
            return [1, 2, 3]

        result = fetch_data()

        assert result == [1, 2, 3]
        # Check that log message was written
        assert any("PERF fetch_data" in record.message for record in caplog.records)
        assert any("source=test" in record.message for record in caplog.records)

    def test_timeit_preserves_function_metadata(self):
        """Timeit should preserve __name__ and __doc__."""

        @timeit("test_func")
        def my_function():
            """This is my function."""
            return 42

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "This is my function."
        assert my_function() == 42

    def test_timeit_works_with_args_and_kwargs(self):
        """Timeit should handle function arguments correctly."""

        @timeit("add_numbers")
        def add(a: int, b: int, multiplier: int = 1) -> int:
            return (a + b) * multiplier

        result = add(5, 3, multiplier=2)
        assert result == 16

    def test_timeit_logs_extra_context(self, caplog):
        """Timeit should include extra context in logs."""

        @timeit("operation", {"env": "test", "version": "1.0"})
        def operation():
            return "done"

        operation()

        log_messages = [record.message for record in caplog.records]
        assert any("env=test" in msg for msg in log_messages)
        assert any("version=1.0" in msg for msg in log_messages)

    def test_timeit_with_exception(self, caplog):
        """Timeit should still log even if function raises."""

        @timeit("failing_op")
        def failing_operation():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_operation()

        # Should still have logged the timing
        assert any("PERF failing_op" in record.message for record in caplog.records)


class TestTimerIntegration:
    """Integration tests for Timer with realistic scenarios."""

    def test_nested_timers(self):
        """Test nested Timer contexts."""
        outer_data = {}
        inner_data = {}

        def outer_sink(name: str, duration: float, extra: Dict[str, Any]) -> None:
            outer_data["duration"] = duration

        def inner_sink(name: str, duration: float, extra: Dict[str, Any]) -> None:
            inner_data["duration"] = duration

        with Timer(outer_sink, "outer"):
            time.sleep(0.05)
            with Timer(inner_sink, "inner"):
                time.sleep(0.05)

        # Outer should be longer than inner
        assert outer_data["duration"] > inner_data["duration"]
        assert 0.04 <= inner_data["duration"] <= 0.1
        assert 0.09 <= outer_data["duration"] <= 0.2
