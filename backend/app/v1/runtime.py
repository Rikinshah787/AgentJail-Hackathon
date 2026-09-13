"""Process-wide gateway runtime (SQLite + mock executor)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .db import Base, make_engine, make_session_factory
from .executor import MockExecutor
from .seed import reset_and_seed, seed_if_empty

_engine = None
_Session = None
_executor = MockExecutor()


def init_runtime() -> None:
    global _engine, _Session
    _engine = make_engine()
    Base.metadata.create_all(_engine)
    _Session = make_session_factory(_engine)
    with _Session() as session:
        seed_if_empty(session)


def session() -> Session:
    if _Session is None:
        init_runtime()
    return _Session()


def executor() -> MockExecutor:
    return _executor


def reset_demo() -> None:
    global _executor
    _executor = MockExecutor()
    with session() as db:
        reset_and_seed(db)
