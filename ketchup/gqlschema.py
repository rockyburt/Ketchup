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
        async with sqlamodels.atomic_session() as session:
            items = (await session.execute(select(sqlamodels.Todo))).scalars()
        todos = typing.cast(list[sqlamodels.Todo], items)
        return todos


@strawberry.type(description="Standard CRUD operations for todo's")
class TodoOps:
    @strawberry.mutation
    async def add_todo(self, text: str) -> sqlamodels.Todo:
        todo = sqlamodels.Todo(text=text)
        async with sqlamodels.atomic_session() as session:
            session.add(todo)
        return todo

    @strawberry.mutation
    async def remove_todo(self, id: int) -> bool:
        async with sqlamodels.atomic_session() as session:
            item = (await session.execute(select(sqlamodels.Todo).where(sqlamodels.Todo.id == id))).scalars().first()
            todo = typing.cast(typing.Optional[sqlamodels.Todo], item)

            if todo is None:
                return False

            await session.delete(todo)
        return True

    @strawberry.mutation
    async def set_todo_completed(self, id: int, flag: bool = True) -> typing.Optional[sqlamodels.Todo]:
        async with sqlamodels.atomic_session() as session:
            item = (await session.execute(select(sqlamodels.Todo).where(sqlamodels.Todo.id == id))).scalars().first()
            todo = typing.cast(typing.Optional[sqlamodels.Todo], item)

            if todo is None:
                return None

            todo.completed = datetime.datetime.now(datetime.timezone.utc) if flag else None
        return todo

    @strawberry.mutation
    async def modify_todo_text(self, id: int, text: str) -> typing.Optional[sqlamodels.Todo]:
        async with sqlamodels.atomic_session() as session:
            item = (await session.execute(select(sqlamodels.Todo).where(sqlamodels.Todo.id == id))).scalars().first()
            todo = typing.cast(typing.Optional[sqlamodels.Todo], item)

            if todo is None:
                return None

            todo.text = text
        return todo


@strawberry.type
class Mutation:
    todos: TodoOps

    @strawberry.field(name="todos")
    def _todos_resolver(self) -> TodoOps:
        return TodoOps()


schema = strawberry.Schema(query=Query, mutation=Mutation)
