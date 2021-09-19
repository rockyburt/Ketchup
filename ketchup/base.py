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
