"""run_build must not silently accept a minify flag it cannot honour."""
import pytest

from ux_dom.cli.build import run_build


@pytest.mark.parametrize("value", [True, False])
def test_minify_fails_closed(value, tmp_path):
    with pytest.raises(ValueError, match="uxcompose build"):
        run_build(cwd=tmp_path, minify=value)
