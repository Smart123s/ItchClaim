# The MIT License (MIT)
#
# Copyright (c) 2022-2026 Péter Tombor.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
from contextlib import contextmanager
from typing import Dict
from sqlalchemy import Column, ForeignKey, Integer, Table, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


# Many-to-Many association table between games and sales
game_sales = Table(
    "game_sales",
    Base.metadata,
    Column("game_id", Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True),
    Column("sale_id", Integer, ForeignKey("sales.id", ondelete="CASCADE"), primary_key=True, index=True),
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_engines: Dict[str, Engine] = {}


def get_engine(database_file: str) -> Engine:
    """Get or create a cached SQLAlchemy engine for the given SQLite database file"""
    abs_path = os.path.abspath(database_file)
    if abs_path not in _engines:
        dir_name = os.path.dirname(abs_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        engine = create_engine(f"sqlite:///{abs_path}")
        Base.metadata.create_all(engine)
        _engines[abs_path] = engine
    return _engines[abs_path]


def init_db(database_file: str) -> Engine:
    """Initialize database tables for the given database file"""
    return get_engine(database_file)


def get_sessionmaker(database_file: str) -> sessionmaker:
    """Get a sessionmaker bound to the engine for the database file"""
    engine = init_db(database_file)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_db_session(database_file: str):
    """Context manager providing an active SQLAlchemy Session with auto-commit/rollback"""
    SessionLocal = get_sessionmaker(database_file)
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
