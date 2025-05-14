import sqlite3
from typing import List, Optional
from datetime import datetime
from .models import Antenna, Tag, Record

# Antenna CRUD

def insert_antenna(conn: sqlite3.Connection, antenna: Antenna) -> None:
    """Insert or replace an Antenna record."""
    conn.execute(
        "INSERT OR REPLACE INTO antenna (antenna_id, x, y) VALUES (?, ?, ?)",
        (antenna.antenna_id, antenna.x, antenna.y)
    )


def get_antenna_by_id(conn: sqlite3.Connection, antenna_id: str) -> Optional[Antenna]:
    """Fetch an Antenna by its ID."""
    row = conn.execute(
        "SELECT antenna_id, x, y FROM antenna WHERE antenna_id = ?",
        (antenna_id,)
    ).fetchone()
    if row:
        return Antenna(row["antenna_id"], row["x"], row["y"])
    return None


def list_antennas(conn: sqlite3.Connection) -> List[Antenna]:
    """List all Antenna records."""
    rows = conn.execute(
        "SELECT antenna_id, x, y FROM antenna"
    ).fetchall()
    return [Antenna(r["antenna_id"], r["x"], r["y"]) for r in rows]


# Tag CRUD

def insert_tag(conn: sqlite3.Connection, tag: Tag) -> None:
    """Insert or replace a Tag record."""
    conn.execute(
        "INSERT OR REPLACE INTO tag (tag_id, type, true_x, true_y, pred_x, pred_y, is_read)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            tag.tag_id,
            tag.type,
            tag.true_x,
            tag.true_y,
            tag.pred_x,
            tag.pred_y,
            int(tag.is_read)
        )
    )


def update_tag(conn: sqlite3.Connection, tag: Tag) -> None:
    """Update fields of an existing Tag."""
    conn.execute(
        "UPDATE tag SET type = ?, true_x = ?, true_y = ?, pred_x = ?, pred_y = ?, is_read = ?"
        " WHERE tag_id = ?",
        (
            tag.type,
            tag.true_x,
            tag.true_y,
            tag.pred_x,
            tag.pred_y,
            int(tag.is_read),
            tag.tag_id
        )
    )


def get_tag_by_id(conn: sqlite3.Connection, tag_id: str) -> Optional[Tag]:
    """Fetch a Tag by its ID."""
    row = conn.execute(
        "SELECT tag_id, type, true_x, true_y, pred_x, pred_y, is_read"
        " FROM tag WHERE tag_id = ?",
        (tag_id,)
    ).fetchone()
    if row:
        return Tag(
            tag_id=row["tag_id"],
            type=row["type"],
            true_x=row["true_x"],
            true_y=row["true_y"],
            pred_x=row["pred_x"],
            pred_y=row["pred_y"],
            is_read=bool(row["is_read"])
        )
    return None


def list_tags(conn: sqlite3.Connection, tag_type: Optional[str] = None) -> List[Tag]:
    """List all Tags, optionally filtered by type ('ref' or 'tar')."""
    if tag_type in ('ref', 'tar'):
        rows = conn.execute(
            "SELECT tag_id, type, true_x, true_y, pred_x, pred_y, is_read"
            " FROM tag WHERE type = ?",
            (tag_type,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT tag_id, type, true_x, true_y, pred_x, pred_y, is_read"
            " FROM tag"
        ).fetchall()
    return [
        Tag(
            tag_id=r["tag_id"],
            type=r["type"],
            true_x=r["true_x"],
            true_y=r["true_y"],
            pred_x=r["pred_x"],
            pred_y=r["pred_y"],
            is_read=bool(r["is_read"])
        )
        for r in rows
    ]


# Record CRUD

def insert_record(conn: sqlite3.Connection, record: Record) -> int:
    """Insert a Record and return its generated ID."""
    cursor = conn.execute(
        "INSERT INTO record (tag_id, antenna_id, rc, rssi, read_time)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            record.tag_id,
            record.antenna_id,
            record.rc,
            record.rssi,
            record.read_time.isoformat(sep=' ')
        )
    )
    return cursor.lastrowid


def insert_records(conn: sqlite3.Connection, records: List[Record]) -> None:
    """Batch insert multiple Record entries."""
    tuples = [
        (r.tag_id, r.antenna_id, r.rc, r.rssi, r.read_time.isoformat(sep=' '))
        for r in records
    ]
    conn.executemany(
        "INSERT INTO record (tag_id, antenna_id, rc, rssi, read_time) VALUES (?, ?, ?, ?, ?)",
        tuples
    )


def get_records_by_tag(conn: sqlite3.Connection, tag_id: str) -> List[Record]:
    """Retrieve all Record entries for a given tag."""
    rows = conn.execute(
        "SELECT record_id, tag_id, antenna_id, rc, rssi, read_time"
        " FROM record WHERE tag_id = ?",
        (tag_id,)
    ).fetchall()
    return [
        Record(
            tag_id=r["tag_id"],
            antenna_id=r["antenna_id"],
            rc=r["rc"],
            rssi=r["rssi"],
            read_time=datetime.fromisoformat(r["read_time"]),
            record_id=r["record_id"]
        )
        for r in rows
    ]


def get_records_by_antenna(conn: sqlite3.Connection, antenna_id: str) -> List[Record]:
    """Retrieve all Record entries for a given antenna."""
    rows = conn.execute(
        "SELECT record_id, tag_id, antenna_id, rc, rssi, read_time"
        " FROM record WHERE antenna_id = ?",
        (antenna_id,)
    ).fetchall()
    return [
        Record(
            tag_id=r["tag_id"],
            antenna_id=r["antenna_id"],
            rc=r["rc"],
            rssi=r["rssi"],
            read_time=datetime.fromisoformat(r["read_time"]),
            record_id=r["record_id"]
        )
        for r in rows
    ]
