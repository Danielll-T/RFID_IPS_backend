import os
import asyncio
import json
import requests
import websockets
from typing import List, AsyncGenerator
from ..models import Record
from datetime import datetime


class TagSeeClient:
    """
    TagSee REST & WebSocket 客户端
    """
    def __init__(self, host: str = None, port: int = None):
        # 从环境变量或参数获取 TagSee 服务地址和端口
        self.host = host or os.getenv("TAGSEE_HOST", "localhost")
        self.port = port or int(os.getenv("TAGSEE_PORT", "9092"))
        # 基础 REST 接口和 WebSocket URL
        self.base_url = f"http://{self.host}:{self.port}/service"
        self.ws_url = f"ws://{self.host}:{self.port}/socket"

    def discover_agents(self) -> List[dict]:
        """
        GET /service/discover
        返回: { errorCode:0, agents:[{ip,name,remark}, ...] }
        """
        resp = requests.get(f"{self.base_url}/discover")
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != 0:
            raise RuntimeError(f"发现 Agent 失败: {data}")
        return data.get("agents", [])

    def create_agent(self, ip: str, name: str, remark: str = "") -> None:
        """
        POST /service/agent/create
        参数: ip, name, remark
        返回: { errorCode:0 }
        """
        payload = {"ip": ip, "name": name, "remark": remark}
        resp = requests.post(f"{self.base_url}/agent/create", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != 0:
            raise RuntimeError(f"创建 Agent 失败: {data}")

    def update_agent(self, ip: str, name: str, remark: str = "") -> None:
        """
        POST /service/agent/:ip/update
        参数: ip, name, remark
        返回: { errorCode:0 }
        """
        payload = {"ip": ip, "name": name, "remark": remark}
        resp = requests.post(f"{self.base_url}/agent/{ip}/update", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != 0:
            raise RuntimeError(f"更新 Agent 失败: {data}")

    def remove_agent(self, ip: str) -> None:
        """
        POST /service/agent/:ip/remove
        参数: ip
        返回: { errorCode:0 }
        """
        payload = {"ip": ip}
        resp = requests.post(f"{self.base_url}/agent/{ip}/remove", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != 0:
            raise RuntimeError(f"移除 Agent 失败: {data}")

    def start_reading(self, ip: str) -> None:
        """
        GET /service/agent/:ip/start
        启动读取
        返回: { errorCode:0 }
        """
        resp = requests.get(f"{self.base_url}/agent/{ip}/start")
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != 0:
            raise RuntimeError(f"启动读取失败: {data}")

    def stop_reading(self, ip: str) -> None:
        """
        GET /service/agent/:ip/stop
        停止读取
        返回: { errorCode:0 }
        """
        resp = requests.get(f"{self.base_url}/agent/{ip}/stop")
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != 0:
            raise RuntimeError(f"停止读取失败: {data}")

    async def readings_stream(self) -> AsyncGenerator[List[Record], None]:
        """
        订阅 WebSocket 推送的实时读数
        消息结构:
          心跳:   {errorCode:0, type:'heartbeat'}
          读数:   {errorCode:0, type:'reading', tags:[{epc, phase, rssi, doppler, channel, antenna, peekRssi, firstSeenTime, lastSeenTime, timestamp}, ...]}
        返回: Record 列表
        """
        async with websockets.connect(self.ws_url) as ws:
            async for raw in ws:
                msg = json.loads(raw)
                # 跳过心跳或错误消息
                if msg.get("errorCode") != 0 or msg.get("type") != "reading":
                    continue
                tags = msg.get("tags", [])
                recs: List[Record] = []
                for t in tags:
                    # 提取字段
                    epc = t.get("epc")
                    ant = t.get("antenna")
                    rssi = t.get("rssi")
                    # 优先使用 lastSeenTime, 其次 firstSeenTime, 再 timestamp
                    time_str = t.get("lastSeenTime") or t.get("firstSeenTime") or t.get("timestamp")
                    dt = datetime.fromisoformat(time_str) if time_str else datetime.now()
                    recs.append(Record(
                        tag_id=str(epc),
                        antenna_id=str(ant),
                        rc=1,
                        rssi=float(rssi) if rssi is not None else 0.0,
                        read_time=dt
                    ))
                yield recs


async def collect_and_store_records(ip: str, conn) -> None:
    """
    示例: 启动读取，收集一次批量读数写入数据库，然后停止读取
    """
    client = TagSeeClient()
    # 启动读取
    client.start_reading(ip)
    try:
        # 异步等待一批次数据
        async for batch in client.readings_stream():
            from ..repository import insert_records
            insert_records(conn, batch)
            break
    finally:
        # 停止读取
        client.stop_reading(ip)

# 若在同步上下文中使用，可调用 asyncio.run():
# asyncio.run(collect_and_store_records("192.168.1.100", conn))