"""``cprofile_to_speedscope`` weights each frame by self time, not cumulative."""

from types import SimpleNamespace

from ux_dom.profiling import cprofile_to_speedscope


def test_weights_are_self_time_and_sum_to_total():
    outer = ("app.py", 1, "outer")
    inner = ("app.py", 5, "inner")
    # outer: 1s self, 3s cumulative (calls inner); inner: 2s self and cumulative.
    stats = SimpleNamespace(
        stats={
            outer: (1, 1, 1.0, 3.0, {}),
            inner: (1, 1, 2.0, 2.0, {outer: (1, 1, 2.0, 2.0)}),
        }
    )
    prof = cprofile_to_speedscope(stats)["profiles"][0]  # type: ignore[arg-type]
    assert prof["weights"] == [1_000_000, 2_000_000]
    assert prof["endValue"] == 3_000_000
