import time

from backend.app.orchestrator.trace_emitter import TraceEmitter


def test_step_durations_are_per_step_not_cumulative():
    emitter = TraceEmitter("sq-test")
    time.sleep(0.05)
    emitter.add_step("first", "done")
    time.sleep(0.05)
    emitter.add_step("second", "done")
    first, second = (s.wall_clock_ms for s in emitter.steps)
    assert 40 <= first < 90
    # A cumulative timer would report ~100 ms here.
    assert 40 <= second < 90


def test_fast_step_is_not_floored():
    emitter = TraceEmitter("sq-test")
    emitter.add_step("instant", "done")
    assert emitter.steps[0].wall_clock_ms < 42


def test_explicit_duration_is_kept():
    emitter = TraceEmitter("sq-test")
    emitter.add_step("timed", "done", wall_clock_ms=777)
    assert emitter.steps[0].wall_clock_ms == 777
