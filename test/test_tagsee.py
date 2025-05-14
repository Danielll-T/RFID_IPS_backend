import pytest
import json
from pathlib import Path
from datetime import datetime
import pytest_asyncio

import src.db as db_module
from src.services.tagsee import TagSeeClient, collect_and_store_records
from src.repository import get_records_by_tag, insert_antenna, insert_tag
from src.models import Antenna, Tag, Record
from src.db import get_connection

# 使用文件数据库进行测试，避免使用内存数据库
@pytest.fixture(autouse=True)
def init_db(tmp_path):
    test_db = tmp_path / "test_tagsee.db"
    # 覆盖模块中的 DB_PATH
    db_module.DB_PATH = str(test_db)
    # 重新初始化数据库
    db_module.initialize_database()
    yield

@pytest.mark.asyncio
async def test_rest_api_methods(monkeypatch):
    client = TagSeeClient(host="testhost", port=1234)

    # 模拟 HTTP 响应对象
    class DummyResp:
        def __init__(self, data):
            self._data = data
        def raise_for_status(self):
            pass
        def json(self):
            return self._data

    # discover_agents
    monkeypatch.setattr("requests.get", lambda url: DummyResp({"errorCode":0, "agents":[{"ip":"1.2.3.4","name":"R1","remark":""}]}))
    agents = client.discover_agents()
    assert agents == [{"ip":"1.2.3.4","name":"R1","remark":""}]

    # create_agent, update_agent, remove_agent
    monkeypatch.setattr("requests.post", lambda url, json=None: DummyResp({"errorCode":0}))
    client.create_agent("1.2.3.4", "R1", "remark1")
    client.update_agent("1.2.3.4", "R1-upd", "remark2")
    client.remove_agent("1.2.3.4")

    # start_reading, stop_reading
    monkeypatch.setattr("requests.get", lambda url: DummyResp({"errorCode":0}))
    client.start_reading("1.2.3.4")
    client.stop_reading("1.2.3.4")

@pytest.mark.asyncio
async def test_readings_stream_and_collect(monkeypatch):
    # 准备一系列 WebSocket 推送消息
    now_iso = datetime.now().isoformat()
    messages = [
        json.dumps({"errorCode":0, "type":"heartbeat"}),
        json.dumps({
            "errorCode":0,
            "type":"reading",
            "tags":[{"epc":"T1","antenna":1,"rssi":-55.2,"lastSeenTime": now_iso}]
        }),
        json.dumps({"errorCode":0, "type":"heartbeat"}),
    ]

    # Dummy WebSocket 上下文管理器和异步迭代器
    class DummyWS:
        def __init__(self, url):
            self._iter = iter(messages)
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        def __aiter__(self):
            return self
        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

    # Monkey-patch websockets.connect
    monkeypatch.setattr("websockets.connect", lambda url: DummyWS(url))
    # 将 start_reading/stop_reading 设置为空操作
    monkeypatch.setattr(TagSeeClient, "start_reading", lambda self, ip: None)
    monkeypatch.setattr(TagSeeClient, "stop_reading", lambda self, ip: None)

    # 调用 collect_and_store_records，并验证数据已写入数据库
    with get_connection() as conn:
        # 先插入天线和标签，满足外键约束
        insert_antenna(conn, Antenna(antenna_id="1", x=0.0, y=0.0))
        insert_tag(conn, Tag(tag_id="T1", type="tar"))
        await collect_and_store_records("1.2.3.4", conn)
        records = get_records_by_tag(conn, "T1")
        assert len(records) == 1
        rec = records[0]
        assert rec.tag_id == "T1"
        assert rec.antenna_id == "1"
        assert rec.rssi == -55.2
        # 根据默认 rc=1
        assert rec.rc == 1
