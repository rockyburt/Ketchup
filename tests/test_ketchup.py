import pytest

from ketchup import __version__, webapp


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.asyncio
class TestViews:
    async def test_index(self):
        assert "Welcome" in (await webapp.index())
