import pytest

from ketchup import __version__, gqlschema, webapp


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.asyncio
class TestViews:
    async def test_index(self):
        assert "Welcome" in (await webapp.index())


@pytest.mark.asyncio
@pytest.mark.usefixtures("empty_db")
class TestGraphQuery:
    async def _create(self, text: str) -> int:
        result = await gqlschema.schema.execute('mutation { todos { addTodo(text: "hello world") { id } } }')
        assert result.data is not None
        assert "id" in result.data["todos"]["addTodo"]

        newid = result.data["todos"]["addTodo"]["id"]
        return newid

    async def test_create_remove(self):
        newid = await self._create("hello world")
        result = await gqlschema.schema.execute("mutation { todos { removeTodo(id: %s) } }" % newid)
        assert result.data is not None
        assert result.data["todos"]["removeTodo"] == True
