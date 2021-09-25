# Ketchup

*Ketchup* is a simple web app for learning how to build web apps using recent Python technologies
with an emphasis on asynchronous I/O (asyncio) programming.

Project Source
: <https://github.com/rockyburt/Ketchup>

Part 1 and 2 Source:
: <https://github.com/rockyburt/Ketchup/tree/part/1-2>

Part 3 Source:
: <https://github.com/rockyburt/Ketchup/tree/part/3>

## Prerequisites

- A Linux or Linux-like work environment (all steps were tested and run on *Ubuntu 20.04* inside the *WSL* environment of *Windows 10*)
- A working Python 3.9 installation

**NOTE**: Theoretically these steps will run (using platform/OS-equivalent steps) on most modern OS's but the developer's mileage may vary.

## `Quart` + `Strawberry-GraphQL` Tutorial

The following tutorial explains how to use *Quart* and *Strawberry-GraphQL* to build a simple web application with
a GraphQL-based API.  All example code is written to heavily lean on `asyncio` based programming with a focus
on including *type hint* support in a Python setting.

**Requirements:** *Python 3.9 or higher*

### Part 1: Getting Started with Quart

*Quart* is a web framework heavily inspired by the [Flask](https://flask.palletsprojects.com/en/2.0.x/) framework.  It
strives to be API-compatible with Flask with method and class signatures only differing to allow for the Python `async/await`
approach to asynchronous I/O programming.

1. Install Poetry via <https://python-poetry.org/docs/master/#installation>

2. Create new *Ketchup* project

    ```sh
    poetry new Ketchup
    ```

3. Go into the newly created `Ketchup` directory and add *Quart* to Poetry's requirements files. Also include Hypercorn for it's ASGI running expertise.

    ```sh
    cd Ketchup
    poetry add Quart hypercorn
    ```

    At the time of writing this doc, the versions installed were:
    - `Quart 0.15.1`

4. Setup skeleton web app:

    Create new file `Ketchup/ketchup/webapp.py` with the following content:

    ```python
    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def index():
        return 'Hello World'


    if __name__ == "__main__":
        app.run()

    ```

5. Test new application by running the following from inside the `Ketchup` project directory.

    ```sh
    poetry run python ketchup/webapp.py
    ```

    And open up the following in your browser: <http://localhost:5000>

### Part 2: Adding Strawberry

*Strawberry* is a library for building GraphQL web applications on top of Python and (preferably but not limited to)
`asyncio` web frameworks.  The goal is to define GraphQL schema's using the `dataclasses` package which is part
of the Python *stdlib*.

1. Add *Strawberry-GraphQL* to Poetry's requirements files.

    ```sh
    poetry add Strawberry-graphql
    ```

    At the time of writing this doc, the versions installed were:

    - `Strawberry-graphql 0.77.10`

2. Create a new module at `Ketchup/ketchup/gqlschema.py`

    ```python
    import strawberry


    @strawberry.type
    class Query:
        @strawberry.field
        def upper(self, val: str) -> str:
            return val.upper()
    ```

3. Create new module for embedding the strawberry graphql endpoint as a standard *Quart* view as `Ketchup/ketchup/strawview.py`

    ```python
    import json
    import logging
    import pathlib
    import traceback
    from typing import Any, Union

    import strawberry
    from quart import Response, abort, render_template_string, request
    from quart.typing import ResponseReturnValue
    from quart.views import View
    from strawberry.exceptions import MissingQueryError
    from strawberry.file_uploads.utils import replace_placeholders_with_files
    from strawberry.http import (GraphQLHTTPResponse, parse_request_data,
                                process_result)
    from strawberry.schema import BaseSchema
    from strawberry.types import ExecutionResult

    logger = logging.getLogger("ketchup")


    def render_graphiql_page() -> str:
        dir_path = pathlib.Path(strawberry.__file__).absolute().parent
        graphiql_html_file = f"{dir_path}/static/graphiql.html"

        html_string = None

        with open(graphiql_html_file, "r") as f:
            html_string = f.read()

        return html_string.replace("{{ SUBSCRIPTION_ENABLED }}", "false")


    class GraphQLView(View):
        methods = ["GET", "POST"]

        def __init__(self, schema: BaseSchema, graphiql: bool = True):
            self.schema = schema
            self.graphiql = graphiql

        async def process_result(self, result: ExecutionResult) -> GraphQLHTTPResponse:
            if result.errors:
                for error in result.errors:
                    err = getattr(error, "original_error", None) or error
                    formatted = "".join(traceback.format_exception(err.__class__, err, err.__traceback__))
                    logger.error(formatted)

            return process_result(result)

        async def dispatch_request(self, *args: Any, **kwargs: Any) -> Union[ResponseReturnValue, str]:
            if "text/html" in request.headers.get("Accept", ""):
                if not self.graphiql:
                    abort(404)

                template = render_graphiql_page()
                return await render_template_string(template)

            content_type = str(request.headers.get("content-type", ""))
            if content_type.startswith("multipart/form-data"):
                form = await request.form
                operations = json.loads(form.get("operations", "{}"))
                files_map = json.loads(form.get("map", "{}"))

                data = replace_placeholders_with_files(operations, files_map, await request.files)
            else:
                data = await request.get_json()

            try:
                request_data = parse_request_data(data)
            except MissingQueryError:
                return Response("No valid query was provided for the request", 400)

            context = {"request": request}

            result = await self.schema.execute(
                request_data.query,
                variable_values=request_data.variables,
                context_value=context,
                operation_name=request_data.operation_name,
                root_value=None,
            )

            response_data = await self.process_result(result)

            return Response(
                json.dumps(response_data),
                status=200,
                content_type="application/json",
            )
    ```

4. Modify file `Ketchup/ketchup/webapp.py` to have the following content:

    ```python
    import asyncio

    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    from quart import Quart
    from strawberry import Schema

    from ketchup.gqlschema import Query
    from ketchup.strawview import GraphQLView

    app = Quart("ketchup")
    schema = Schema(Query)


    app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql_view", schema=schema))


    @app.route("/")
    async def index():
        return 'Welcome to Ketchup!  Please see <a href="/graphql">Graph<em>i</em>QL</a> to interact with the GraphQL endpoint.'


    def hypercorn_serve():
        config = Config()
        config.bind = ["0.0.0.0:5000"]
        config.use_reloader = True
        asyncio.run(serve(app, config, shutdown_trigger=lambda: asyncio.Future()))


    if __name__ == "__main__":
        hypercorn_serve()
    ```

5. Test new application by running the following from inside the `Ketchup` project directory.

    a. Run the updated web app

    ```sh
    poetry run python -m ketchup.webapp
    ```

    b. Open up the following in your browser: <http://localhost:5000/graphql>

    c. Input the following graph query into the left side text area and hit the *play* button.

    ```graphql
    query {
      upper(val: "dude, where's my car?")
    }
    ```

    The result should be (on the right side):

    ```json
    {
    "data": {
        "upper": "DUDE, WHERE'S MY CAR?"
    }    
    ```

### Bonus Points - Running Tests

1. Add *pytest* as a dependency.

    ```sh
    # The ^6.2 version identifier for pytest is required due to other dependencies pulling down older versions of pytest
    poetry add -D "pytest^6.2" pytest-asyncio
    ```

2. Ensure the `Ketchup/tests/test_ketchup.py` file exists with the following content:

    ```python
    import pytest

    from ketchup import __version__, webapp


    def test_version():
        assert __version__ == "0.1.0"


    @pytest.mark.asyncio
    class TestViews:
        async def test_index(self):
            assert "Welcome" in (await webapp.index())
    ```

3. Run the tests by issuing the following from *inside* the `Ketchup` directory.

    ```sh
    poetry run pytest
    ```

    The result should be something like:

    ```text
    =============================== test session starts ===============================
    platform linux -- Python 3.9.5, pytest-5.4.3, py-1.10.0, pluggy-0.13.1
    rootdir: /home/ubuntu/dev/Ketchup
    plugins: anyio-3.3.1, asyncio-0.15.1
    collected 2 items

    tests/test_ketchup.py ..                                                    [100%]

    ================================ 2 passed in 0.16s ================================
    ```

### Coding Conventions

It is the author's advice to add the following to help with formatting all code in a standard way.

- Add some developer dependencies:

    ```sh
    poetry add -D black isort
    ```

    The standard *Python* method for activating these formatters would be to append something like the following to `Ketchup/pyproject.toml`.

    ```toml
    exclude = '''
    /(
        \.git
      | \.tox
      | \.venv
      | build
      | dist
    )/   
    '''
    line-length = 119  # standard editor width used by github

    [tool.isort]
    profile = "black"
    ```

### Part 3a: Persistence with SQLAlchemy and PostgreSQL

Before diving into this next part, now might be a good time to mention the fact that [Docker](https://docs.docker.com/get-started/)
can make life a lot easier.  There is a sample documented [docker-compose.yml](./docker-compose.yml) file in the root of this github repo that can
be used to isolate *Python3.9* and *PostgreSQL* runtimes without the need to manually install either (only requirements are Docker and docker-compose).

This is where the project actually starts getting useful.  We are building a **ToDo** application that can persist
todo records to a PostgreSQL database.  The following steps assume you are within the `Ketchup` directory.

1. Add *SQLAlchemy*, *alembic*, and *asyncpg* as a dependencies.

    *As of the writing of this tutorial, SQLAlchemy 1.4.23 is the most recent ... with SQLAlchemy 1.4.x the first version to
    include asyncio support.  In addition, `asyncio` support comes only from PostgreSQL and the `asyncpg` db adapter.*

    ```sh
    poetry add sqlalchemy alembic asyncpg

    # for anyone using mypy/pylance/pyright/vscode ... adding the following should provide better type hint support
    # but is optional and won't affect the application
    poetry add -D sqlalchemy2.stubs
    ```

2. Initialize the *Alembic* database migration framework.

    ```sh
    poetry run alembic init --template async alembic
    ```

3. Modify `Ketchup/alembic/env.py` so that it uses the same postgres db configuration as the rest of the web app.
The file should look like this:

    ```python
    import asyncio
    from logging.config import fileConfig

    from sqlalchemy import pool
    from sqlalchemy.ext.asyncio import create_async_engine

    from alembic import context
    from ketchup import sqlamodels, base

    # this is the Alembic Config object, which provides
    # access to the values within the .ini file in use.
    config = context.config

    # Interpret the config file for Python logging.
    # This line sets up loggers basically.
    assert config.config_file_name is not None
    fileConfig(config.config_file_name)

    # add your model's MetaData object here
    # for 'autogenerate' support
    # from myapp import mymodel
    # target_metadata = mymodel.Base.metadata
    target_metadata = sqlamodels.mapper_registry.metadata

    # other values from the config, defined by the needs of env.py,
    # can be acquired:
    # my_important_option = config.get_main_option("my_important_option")
    # ... etc.


    def run_migrations_offline():
        """Run migrations in 'offline' mode.

        This configures the context with just a URL
        and not an Engine, though an Engine is acceptable
        here as well.  By skipping the Engine creation
        we don't even need a DBAPI to be available.

        Calls to context.execute() here emit the given string to the
        script output.

        """
        url = config.get_main_option("sqlalchemy.url")
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():
            context.run_migrations()


    def do_run_migrations(connection):
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


    async def run_migrations_online():
        """Run migrations in 'online' mode.

        In this scenario we need to create an Engine
        and associate a connection with the context.

        """

        connectable = create_async_engine(
            base.config.DB_URI,
            future=True,
            poolclass=pool.NullPool,
        )

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)


    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())
    ```

4. Setup the initial *SQLAlchemy* models by creating ``Ketchup/ketchup/sqlamodels.py``.

    ```python
    import asyncio
    import dataclasses
    import datetime
    import typing
    from contextlib import asynccontextmanager

    from sqlalchemy import Column, DateTime, Integer, Table, Text
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_scoped_session,
        create_async_engine,
    )
    from sqlalchemy.orm import registry, sessionmaker

    from ketchup import base

    mapper_registry = registry()

    _async_engine = create_async_engine(base.config.DB_URI, future=True)
    _async_session_factory = sessionmaker(_async_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore - having some pyright issues

    _get_session = async_scoped_session(_async_session_factory, scopefunc=asyncio.current_task)


    @asynccontextmanager
    async def atomic_session() -> typing.AsyncIterator[AsyncSession]:
        async with _get_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


    @mapper_registry.mapped
    @dataclasses.dataclass
    class Todo:
        __table__ = Table(
            "ketchup_todo",
            mapper_registry.metadata,
            Column(
                "id",
                Integer,
                primary_key=True,
                autoincrement=True,
                nullable=False,
            ),
            Column("text", Text(), nullable=False),
            Column("created", DateTime(True), nullable=False),
            Column("completed", DateTime(True), nullable=True),
        )

        id: int = dataclasses.field(init=False)
        text: str
        created: datetime.datetime = dataclasses.field(
            default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
        )
        completed: typing.Optional[datetime.datetime] = None
    ```

5. Create new `Ketchup/ketchup/base.py` file with the following contents for configuration.

    ```python
    import os
    import typing


    class Config:
        DB_URI: str = "postgresql+asyncpg://localhost/ketchup"

        def __init__(self, prefix: str = "KETCHUP_"):
            for name, type_ in typing.get_type_hints(self).items():
                envname = prefix + name
                if envname in os.environ:
                    setattr(self, name, type_(os.environ[envname]))


    config = Config()
    ```

6. At this point, make sure PostgreSQL has beeng configured properly with an empty
database setup and referenced by either `config.DB_URI` or by setting os env variable
`KETCHUP_DB_URI`.  Once that's been done, use *Alembic* to auto-generate the first revision migration file.

    ```sh
    poetry run alembic revision --autogenerate -m "New ketchup_todos table"
    ```

7. Run the following to setup the necessary database schema.

    ```sh
    poetry run alembic upgrade head
    ```

### Part 3b: Making the GraphQL schema useful

1. Modify `Ketchup/ketchup/gqlschema.py` to have basic CRUD access via *Query* and *Mutation*.

    ```python
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
    ```

2. The ``Ketchup/ketchup/webapp.py` file will need to be updated to accomodate the *SQLAlchemy* database access as well as
the new mutation support.

    ```python
    import asyncio

    from hypercorn.asyncio import serve
    from hypercorn.config import Config as HypercornConfig
    from quart import Quart

    from ketchup import base
    from ketchup.gqlschema import schema
    from ketchup.strawview import GraphQLView

    app = Quart("ketchup")
    app.config.from_object(base.config)


    app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql_view", schema=schema))


    @app.route("/")
    async def index():
        return 'Welcome to Ketchup!  Please see <a href="/graphql">Graph<em>i</em>QL</a> to interact with the GraphQL endpoint.'


    def hypercorn_serve():
        hypercorn_config = HypercornConfig()
        hypercorn_config.bind = ["0.0.0.0:5000"]
        hypercorn_config.use_reloader = True
        asyncio.run(serve(app, hypercorn_config, shutdown_trigger=lambda: asyncio.Future()))


    if __name__ == "__main__":
        hypercorn_serve()
    ```

3. At this point it should be possible to restart the web application and start playing with the actual
graphql queries.

    ```sh
    poetry run python -m ketchup.webapp
    ```

    And the go to <http://localhost:5000/graphql> to test queries/mutations.  Some examples are:

    ```graphql
    # Query #1
    # The following will show all todos persisted to the database .. upon first query it should return an empty
    # result set
    query {
      todos {
        id
        text
        created
        completed
      }
    }
    ```

    ```graphql
    # Mutation #1
    # This will create our first todo record and show ups the generated ID.  After running this at least once
    # it should be possible to re-run "Query #1" above and see data that was created and saved.
    mutation {
      todos {
        addTodo(text: "Hello World") {
          id
        }
      }
    }

    ```

### Bonus Points - Adding Query Tests

1. Add new `Ketchup/tests/conftest.py` file to setup *pytest* fixtures.

    ```python
    import asyncio
    import uuid
    from urllib.parse import urlparse, urlunparse

    import pytest
    from sqlalchemy import pool, text
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_scoped_session,
        create_async_engine,
    )
    from sqlalchemy.orm import close_all_sessions, sessionmaker

    from ketchup import __version__, base, sqlamodels


    def test_version():
        assert __version__ == "0.1.0"


    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()


    @pytest.fixture(scope="session")
    def session_monkeypatch():
        mpatch = pytest.MonkeyPatch()
        yield mpatch
        mpatch.undo()


    @pytest.fixture(scope="session")
    async def empty_db(session_monkeypatch: pytest.MonkeyPatch):
        parsed = urlparse(base.config.DB_URI)
        dbname = parsed.path[1:] + "_test_" + uuid.uuid4().hex

        newuri = urlunparse([parsed[0], parsed[1], "/template1", parsed[3], parsed[4], parsed[5]])

        anony_engine = create_async_engine(
            newuri,
            future=True,
            poolclass=pool.NullPool,
            isolation_level="AUTOCOMMIT",
        )

        async with anony_engine.connect() as conn:
            await (await conn.execution_options(isolation_level="AUTOCOMMIT")).execute(text(f"CREATE DATABASE {dbname}"))

        async_engine = None
        async_session_factory = None
        make_session = None
        try:
            newuri = urlunparse([parsed[0], parsed[1], "/" + dbname, parsed[3], parsed[4], parsed[5]])
            async_engine = create_async_engine(newuri, future=True)
            async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore - having some pyright issues
            make_session = async_scoped_session(async_session_factory, scopefunc=asyncio.current_task)
            session_monkeypatch.setattr(sqlamodels, "make_session", make_session)

            async with async_engine.begin() as conn:
                await conn.run_sync(sqlamodels.mapper_registry.metadata.create_all)

            yield
        finally:
            close_all_sessions()
            if async_engine is not None:
                try:
                    await async_engine.dispose()
                except Exception:
                    ...
            async with anony_engine.connect() as conn:
                await (await conn.execution_options(isolation_level="AUTOCOMMIT")).execute(text(f"DROP DATABASE {dbname}"))
    ```

2. Update the `Ketchup/tests/test_ketchup.py` file to have the following content.

    ```python
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
    ```

3. Run the tests by issuing the following from *inside* the `Ketchup` directory.

    ```sh
    poetry run pytest
    ```

    The result should be something like:

    ```text
    =============================== test session starts ===============================
    platform linux -- Python 3.9.5, pytest-5.4.3, py-1.10.0, pluggy-0.13.1
    rootdir: /home/ubuntu/dev/Ketchup
    plugins: anyio-3.3.1, asyncio-0.15.1
    collected 3 items

    tests/test_ketchup.py ...                                                   [100%]

    ================================ 3 passed in 0.36s ================================
    ```

## Appendices

### Appendix A: Adding Uvicorn

`Uvicorn` is a common **ASGI** server implementation that integrates easily with *Gunicorn* and is ready for production
rollouts.

1. Begin by adding *Uvicorn* and standard *uvloop* requirements to the poetry configuration.

    ```sh
    poetry add uvicorn[standard]
    ```

2. At this poitn the simplest way to run the web application for development would be as follows:

    ```sh
    poetry run uvicorn --host 0.0.0.0 --port 5000 --reload ketchup.webapp:app

### Appendix B: Setting up Docker and Docker Compose

Docker enables developers to more easily manage system depdendencies and lock requirements.  In the case of this tutorial,
it helps setup the required *Python* and *PostgreSQL* versions.

1. First install the *Docker* tool using standard docker documentation.

    - <https://docs.docker.com/get-docker/>

2. While it's possible to install *Docker Compose* separately, it is recommended to install using Poetry for this tutorial.

    ```sh
    poetry add -D docker-compose
    ```

3. Now setup a new ``Ketchup/Dockerfile`` file with the following content.

    ```Dockerfile
    FROM docker.io/python:3.9

    RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

    ENV PATH=/root/.local/bin:${PATH}
    ```

4. Next create the ``Ketchup/docker-compose.yml`` file.

    ```yaml
    version: "3.8"
    services:
    ketchup-webapp:
        build: .
        image: poetry-py3.9
        container_name: ketchup-webapp
        hostname: ketchup-webapp
        working_dir: /root/Ketchup
        tty: true
        command: ["sh", "-c", "poetry update && poetry run alembic upgrade head && exec poetry run uvicorn --host 0.0.0.0 --port 5000 --reload ketchup.webapp:app"]
        ports:
        - "5000:5000"
        volumes:
        - ".docker/home-root-cache:/root/.cache"
        - ".:/root/Ketchup"
        links:
        - ketchup-postgres
        environment:
        - "KETCHUP_DB_URI=postgresql+asyncpg://ketchupuser:ketchup123@ketchup-postgres/ketchup"
    ketchup-postgres:
        image: docker.io/postgres:13
        container_name: ketchup-postgres
        hostname: ketchup-postgres
        volumes:
        - ".docker/postgres:/var/lib/postgresql/data"
        environment:
        - "POSTGRES_PASSWORD=ketchup123"
        - "POSTGRES_USER=ketchupuser"
        - "POSTGRES_DB=ketchup"
    ```

5. Use *docker-compose* to launch the appropriate container images using *Docker*.

    ```sh
    poetry run docker-compose up
    ```

## Frameworks/Components Reference

[Quart](https://pgjones.gitlab.io/quart/index.html)
: An asynchronous I/O (asyncio) based web framework inspired by Flask

[Strawberry GraphQL](https://strawberry.rocks/docs/integrations/asgi)
: A GraphQL library for Python enabling the building of GraphQL web apps using Python dataclasses

[SQLAlchemy](https://www.sqlalchemy.org/)
: Python ORM mapper (with `asyncio` support as of v1.4).

[asyncpg](https://github.com/MagicStack/asyncpg)
: A PostgreSQL client library for Python using `asyncio`.

[Alembic](https://alembic.sqlalchemy.org/en/latest/)
: A database migration tool for *SQLAlchemy*.

[Uvicorn](https://www.uvicorn.org/)
An *ASGI* server implementation that uses *uvloop* and *httptools*.

[Docker](https://docs.docker.com/)
A popular platform for building and operating container images.

[docker-compose](https://docs.docker.com/compose/)
A tool for defining and running multi-container *Docker* applications.
