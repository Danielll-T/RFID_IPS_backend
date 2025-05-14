import pytest
from fastapi.testclient import TestClient
from pathlib import Path

import src.db as db_module
from src.api import app


@pytest.fixture(autouse=True)
def client(tmp_path):
    # 使用文件数据库，避免使用内存数据库
    test_db = tmp_path / "test.db"
    db_module.DB_PATH = str(test_db)
    db_module.initialize_database()
    client = TestClient(app)
    yield client


def test_antenna_endpoints(client):
    # 初始列表为空
    r = client.get("/api/antennas/")
    assert r.status_code == 200
    assert r.json() == []
    # 插入天线
    r = client.post("/api/antennas/", json={"antenna_id":"A1","x":1.0,"y":2.0})
    assert r.status_code == 200
    # 列出天线
    r = client.get("/api/antennas/")
    assert r.json() == [{"antenna_id":"A1","x":1.0,"y":2.0}]


def test_tag_endpoints(client):
    # 初始列表为空
    r = client.get("/api/tags/")
    assert r.status_code == 200
    assert r.json() == []
    # 插入参考标签
    payload = {"tag_id":"T1","type":"ref","true_x":0.0,"true_y":0.0}
    r = client.post("/api/tags/", json=payload)
    assert r.status_code == 200
    # 列出标签
    r = client.get("/api/tags/")
    data = r.json()
    assert any(t["tag_id"] == "T1" for t in data)


def test_reset_endpoint(client):
    # 插入数据
    client.post("/api/antennas/", json={"antenna_id":"A1","x":1.0,"y":2.0})
    client.post("/api/tags/", json={"tag_id":"T2","type":"tar","true_x":3.0,"true_y":4.0})
    # 重置
    r = client.delete("/api/reset")
    assert r.status_code == 200
    # 确认清空
    assert client.get("/api/antennas/").json() == []
    assert client.get("/api/tags/").json() == []


def test_export_tags(client):
    # 插入标签
    client.post("/api/tags/", json={"tag_id":"T3","type":"tar","true_x":5.0,"true_y":6.0})
    # 导出 CSV
    r = client.get("/api/export/tags")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    text = r.text
    assert "T3" in text
