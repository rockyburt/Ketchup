import datetime
import typing

import strawberry
from sqlalchemy.future import select

from ketchup import sqlamodels

strawberry.type(sqlamodels.Todo)


@strawberry.type
class Query:
    todos: list[sqlamodels.Todo]

    @strawberry.field(name="todos")
    async def _todos_resolver(self) -> list[sqlamodels.Todo]:
        session = sqlamodels.make_session()
        items = (await session.execute(select(sqlamodels.Todo))).scalars()
        todos = typing.cast(list[sqlamodels.Todo], items)
        return todos


@strawberry.type(description="Standard CRUD operations for todo's")
class TodoOps:
    @strawberry.mutation
    async def add_todo(self, text: str) -> sqlamodels.Todo:
        todo = sqlamodels.Todo(text=text)
        session = sqlamodels.make_session()
        session.add(todo)
        await session.commit()
        return todo

    @strawberry.mutation
    async def remove_todo(self, id: int) -> bool:
        session = sqlamodels.make_session()
        item = (await session.execute(select(sqlamodels.Todo).where(sqlamodels.Todo.id == id))).scalars().first()
        todo = typing.cast(typing.Optional[sqlamodels.Todo], item)

        if todo is None:
            return False

        await session.delete(todo)
        await session.commit()
        return True

    @strawberry.mutation
    async def set_todo_completed(self, id: int, flag: bool = True) -> typing.Optional[sqlamodels.Todo]:
        session = sqlamodels.make_session()
        item = (await session.execute(select(sqlamodels.Todo).where(sqlamodels.Todo.id == id))).scalars().first()
        todo = typing.cast(typing.Optional[sqlamodels.Todo], item)

        if todo is None:
            return None

        todo.completed = datetime.datetime.now(datetime.timezone.utc) if flag else None

        await session.commit()
        return todo

    @strawberry.mutation
    async def modify_todo_text(self, id: int, text: str) -> typing.Optional[sqlamodels.Todo]:
        session = sqlamodels.make_session()
        item = (await session.execute(select(sqlamodels.Todo).where(sqlamodels.Todo.id == id))).scalars().first()
        todo = typing.cast(typing.Optional[sqlamodels.Todo], item)

        if todo is None:
            return None

        todo.text = text

        await session.commit()
        return todo


@strawberry.type
class Mutation:
    todos: TodoOps

    @strawberry.field(name="todos")
    def _todos_resolver(self) -> TodoOps:
        return TodoOps()


schema = strawberry.Schema(query=Query, mutation=Mutation)
