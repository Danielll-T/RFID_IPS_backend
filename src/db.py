import os
import sqlite3
from contextlib import contextmanager
from typing import Generator
from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS antenna (
  antenna_id   TEXT    PRIMARY KEY,
  x             REAL   NOT NULL,
  y             REAL   NOT NULL
);

CREATE TABLE IF NOT EXISTS tag (
  tag_id       TEXT    PRIMARY KEY,
  type         TEXT    NOT NULL CHECK(type IN ('ref','tar')),
  true_x       REAL,
  true_y       REAL,
  pred_x       REAL,
  pred_y       REAL,
  is_read      INTEGER NOT NULL DEFAULT 0,
  CHECK (
    (type='ref' AND pred_x IS NULL AND pred_y IS NULL)
    OR (type='tar')
  )
);

CREATE TABLE IF NOT EXISTS record (
  record_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  tag_id       TEXT    NOT NULL,
  antenna_id   TEXT    NOT NULL,
  rc           INTEGER NOT NULL,
  rssi         REAL    NOT NULL,
  read_time    DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (tag_id)     REFERENCES tag(tag_id) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (antenna_id) REFERENCES antenna(antenna_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_record_tag     ON record(tag_id);
CREATE INDEX IF NOT EXISTS idx_record_antenna ON record(antenna_id);
"""

def initialize_database() -> None:
    # Ensure the directory for the database exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON;")
        # Create tables and indexes
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager to provide a SQLite connection with foreign keys enabled.
    Commits transactions and closes the connection upon exit.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Return rows as sqlite3.Row for name-based access
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# Automatically initialize database schema on import
initialize_database()
