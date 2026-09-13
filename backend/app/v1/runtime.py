"""Process-wide gateway runtime (SQLite + mock executor)."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.orm import Session

from .db import Base, make_engine, make_session_factory
from .executor import MockExecutor, ToolExecutor
from .seed import reset_and_seed, seed_if_empty

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

_engine = None
_Session = None

def build_executor() -> ToolExecutor:
    mode = os.getenv("AGENTJAIL_EXECUTOR", "mock").strip().lower()
    if mode == "mock":
        return MockExecutor()
    if mode == "coreweave":
        from .coreweave_executor import CoreWeaveSandboxExecutor

        return CoreWeaveSandboxExecutor()
    if mode == "arga":
        from .arga_executor import ArgaTwinExecutor

        return ArgaTwinExecutor()
    raise RuntimeError("AGENTJAIL_EXECUTOR must be 'mock', 'coreweave', or 'arga'.")


_executor: ToolExecutor = build_executor()


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


def executor() -> ToolExecutor:
    return _executor


def reset_demo() -> None:
    _executor.reset()
    with session() as db:
        reset_and_seed(db)
