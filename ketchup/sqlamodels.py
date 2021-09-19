import asyncio
import dataclasses
import datetime
import typing

from sqlalchemy import Column, DateTime, Integer, Table, Text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import registry, sessionmaker

from ketchup import base

mapper_registry = registry()
Base = mapper_registry.generate_base()

async_engine = create_async_engine(base.config.DB_URI, future=True)
async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
make_session = async_scoped_session(async_session_factory, scopefunc=asyncio.current_task)


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
