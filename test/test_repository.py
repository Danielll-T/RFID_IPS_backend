import pytest
from pathlib import Path

import src.db as db_module
from src.repository import (
    insert_antenna, list_antennas,
    insert_tag, list_tags, get_tag_by_id, update_tag,
    insert_record, get_records_by_tag
)
from src.models import Antenna, Tag, Record


@pytest.fixture(autouse=True)
def init_db(tmp_path):
    # 使用文件数据库，避免使用内存数据库
    test_db = tmp_path / "test.db"
    # 覆盖 db_module 的 DB_PATH 并重新初始化
    db_module.DB_PATH = str(test_db)
    db_module.initialize_database()
    yield


def test_antenna_crud():
    # 测试天线的插入与查询
    with db_module.get_connection() as conn:
        # 初始应为空
        assert list_antennas(conn) == []
        # 插入天线
        antenna = Antenna(antenna_id="A1", x=1.23, y=4.56)
        insert_antenna(conn, antenna)
        ants = list_antennas(conn)
        assert len(ants) == 1
        assert ants[0] == antenna


def test_tag_crud():
    # 测试标签的插入、查询与更新
    with db_module.get_connection() as conn:
        assert list_tags(conn) == []
        # 插入参考标签
        tag = Tag(tag_id="T1", type="ref", true_x=0.0, true_y=0.0)
        insert_tag(conn, tag)
        tags = list_tags(conn)
        assert len(tags) == 1 and tags[0] == tag
        # 更新标签字段
        tag.true_x = 2.0
        tag.true_y = 3.0
        tag.is_read = True
        update_tag(conn, tag)
        t = get_tag_by_id(conn, "T1")
        assert t == tag


def test_record_crud():
    # 测试读数记录的插入与查询
    with db_module.get_connection() as conn:
        # 先插入关联的天线和标签
        ant = Antenna(antenna_id="A1", x=0.0, y=0.0)
        insert_antenna(conn, ant)
        tag = Tag(tag_id="T2", type="tar", true_x=1.0, true_y=2.0)
        insert_tag(conn, tag)
        # 插入一条读数
        record = Record(tag_id="T2", antenna_id="A1", rc=5, rssi=-60.5)
        rec_id = insert_record(conn, record)
        assert isinstance(rec_id, int) and rec_id > 0
        # 查询读数
        recs = get_records_by_tag(conn, "T2")
        assert len(recs) == 1
        r = recs[0]
        assert r.tag_id == "T2"
        assert r.antenna_id == "A1"
        assert r.rc == 5
        assert r.rssi == -60.5
