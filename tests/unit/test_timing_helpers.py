"""
Unit tests for timing instrumentation helpers.

Guards against epoch/timezone mistakes in audit timestamps.
"""

from datetime import datetime, timezone
from time import sleep
from src.qnwis.instrumentation.timing import Stopwatch


def test_stopwatch_start():
    """Stopwatch should start with current UTC time."""
    sw = Stopwatch.start()
    
    # Should have a UTC timestamp
    assert sw.started_at_utc.tzinfo == timezone.utc
    
    # Should be recent (within last second)
    now = datetime.now(timezone.utc)
    delta = (now - sw.started_at_utc).total_seconds()
    assert delta < 1.0


def test_stopwatch_stop_ms():
    """Stopwatch should measure elapsed time correctly."""
    sw = Stopwatch.start()
    sleep(0.01)  # Sleep for ~10ms
    
    elapsed_ms, finished_at = sw.stop_ms()
    
    # Should have measured some time
    assert elapsed_ms >= 10.0
    assert elapsed_ms < 100.0  # Should not be wildly off
    
    # Finished timestamp should be UTC
    assert finished_at.tzinfo == timezone.utc
    
    # Finished should be after started
    assert finished_at > sw.started_at_utc


def test_stopwatch_elapsed_ms():
    """Stopwatch should report elapsed time without stopping."""
    sw = Stopwatch.start()
    sleep(0.01)
    
    elapsed1 = sw.elapsed_ms()
    sleep(0.01)
    elapsed2 = sw.elapsed_ms()
    
    # Second reading should be larger
    assert elapsed2 > elapsed1
    
    # Both should be reasonable
    assert elapsed1 >= 10.0
    assert elapsed2 >= 20.0


def test_stopwatch_lap_ms():
    """Stopwatch should measure lap times correctly."""
    sw = Stopwatch.start()
    sleep(0.01)
    
    lap1 = sw.lap_ms()
    sleep(0.01)
    lap2 = sw.lap_ms()
    
    # Each lap should be ~10ms
    assert lap1 >= 10.0
    assert lap2 >= 10.0
    
    # Laps should be independent
    assert abs(lap1 - lap2) < 50.0  # Should be similar


def test_no_epoch_confusion():
    """
    Critical test: Timestamps should NOT be Unix epoch (1970-01-01).
    
    This guards against using perf_counter() as a timestamp.
    """
    sw = Stopwatch.start()
    
    # Should NOT be epoch
    assert sw.started_at_utc.year >= 2024
    assert sw.started_at_utc.year != 1970
    
    elapsed_ms, finished_at = sw.stop_ms()
    
    # Finished should also not be epoch
    assert finished_at.year >= 2024
    assert finished_at.year != 1970


def test_utc_timezone_present():
    """
    Critical test: Timestamps must have UTC timezone info.
    
    Guards against naive datetime objects.
    """
    sw = Stopwatch.start()
    
    # Started timestamp must have timezone
    assert sw.started_at_utc.tzinfo is not None
    assert sw.started_at_utc.tzinfo == timezone.utc
    
    elapsed_ms, finished_at = sw.stop_ms()
    
    # Finished timestamp must have timezone
    assert finished_at.tzinfo is not None
    assert finished_at.tzinfo == timezone.utc


def test_iso_format_includes_timezone():
    """ISO format should include timezone offset."""
    sw = Stopwatch.start()
    iso_str = sw.started_at_utc.isoformat()
    
    # Should end with +00:00 or Z
    assert "+00:00" in iso_str or iso_str.endswith("Z")


def test_duration_uses_perf_counter():
    """
    Duration measurement should use perf_counter for accuracy.
    
    This is a smoke test - we can't directly verify perf_counter usage,
    but we can verify that durations are reasonable.
    """
    sw = Stopwatch.start()
    sleep(0.05)  # 50ms
    
    elapsed_ms, _ = sw.stop_ms()
    
    # Should be close to 50ms (within 20ms tolerance for system variance)
    assert 40.0 <= elapsed_ms <= 70.0
