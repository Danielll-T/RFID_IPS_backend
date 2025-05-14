from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from io import StringIO
import csv
import pandas as pd

from ..db import get_connection
from ..repository import (
    insert_antenna, list_antennas,
    insert_tag, list_tags, get_tag_by_id,
    get_records_by_tag
)
from ..models import Antenna, Tag, Record
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# Pydantic 请求/响应模型
class AntennaIn(BaseModel):
    antenna_id: str
    x: float
    y: float

class TagIn(BaseModel):
    tag_id: str
    type: str  # 'ref' or 'tar'
    true_x: Optional[float] = None
    true_y: Optional[float] = None

class AntennaOut(AntennaIn):
    pass

class TagOut(BaseModel):
    tag_id: str
    type: str
    true_x: Optional[float]
    true_y: Optional[float]
    pred_x: Optional[float]
    pred_y: Optional[float]
    is_read: bool

class ReadingOut(BaseModel):
    tag_id: str
    rssi: List[float]
    rc: List[int]
    is_read: bool

class PredictionOut(BaseModel):
    tag_id: str
    pred_x: Optional[float]
    pred_y: Optional[float]

# 1. 手动录入单个天线
@router.post("/antennas/", response_model=None)
def create_antenna(antenna: AntennaIn):
    with get_connection() as conn:
        insert_antenna(conn, Antenna(**antenna.model_dump()))
    return {"message": "antenna inserted"}

# 1b. CSV 批量导入天线
@router.post("/antennas/upload", response_model=None)
def upload_antennas(file: UploadFile = File(...)):
    content = file.file.read().decode('utf-8')
    reader = csv.DictReader(StringIO(content))
    with get_connection() as conn:
        for row in reader:
            insert_antenna(conn, Antenna(
                antenna_id=row['antenna_id'],
                x=float(row['x']),
                y=float(row['y'])
            ))
    return {"message": "antennas uploaded"}

# 2. 手动录入单个标签
@router.post("/tags/", response_model=None)
def create_tag(tag_in: TagIn):
    tag = Tag(
        tag_id=tag_in.tag_id,
        type=tag_in.type,
        true_x=tag_in.true_x,
        true_y=tag_in.true_y
    )
    with get_connection() as conn:
        insert_tag(conn, tag)
    return {"message": "tag inserted"}

# 2b. CSV 批量导入标签
@router.post("/tags/upload", response_model=None)
def upload_tags(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    with get_connection() as conn:
        for _, row in df.iterrows():
            insert_tag(conn, Tag(
                tag_id=row['tag_id'],
                type=row['type'],
                true_x=row.get('true_x'),
                true_y=row.get('true_y')
            ))
    return {"message": "tags uploaded"}

# 3. 列出所有天线
@router.get("/antennas/", response_model=List[AntennaOut])
def get_all_antennas():
    with get_connection() as conn:
        ants = list_antennas(conn)
    return [AntennaOut(**a.__dict__) for a in ants]

# 3b. 列出所有标签及坐标
@router.get("/tags/", response_model=List[TagOut])
def get_all_tags():
    with get_connection() as conn:
        tags = list_tags(conn)
    return [TagOut(**t.__dict__) for t in tags]

# 4. 获取指定类型标签的读数
@router.get("/readings/", response_model=List[ReadingOut])
def get_readings(tag_type: str):
    if tag_type not in ('ref', 'tar'):
        raise HTTPException(status_code=400, detail="type must be 'ref' or 'tar'")
    out = []
    with get_connection() as conn:
        tags = list_tags(conn, tag_type)
        for t in tags:
            recs = get_records_by_tag(conn, t.tag_id)
            rssi = [r.rssi for r in recs]
            rc   = [r.rc   for r in recs]
            out.append(ReadingOut(tag_id=t.tag_id, rssi=rssi, rc=rc, is_read=t.is_read))
    return out

# 5. 获取所有目标标签预测坐标
@router.get("/predictions/", response_model=List[PredictionOut])
def get_predictions():
    out = []
    with get_connection() as conn:
        tags = list_tags(conn, 'tar')
        for t in tags:
            out.append(PredictionOut(tag_id=t.tag_id, pred_x=t.pred_x, pred_y=t.pred_y))
    return out

# 6a. 导出 tag 表
@router.get("/export/tags")
def export_tags():
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM tag", conn)
    csv_data = df.to_csv(index=False)
    return StreamingResponse(
        StringIO(csv_data),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=tags.csv'}
    )

# 6b. 导出 record 表
@router.get("/export/records")
def export_records():
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM record", conn)
    csv_data = df.to_csv(index=False)
    return StreamingResponse(
        StringIO(csv_data),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=records.csv'}
    )

# 7. 清空所有数据
@router.delete("/reset", response_model=None)
def reset_all():
    with get_connection() as conn:
        conn.execute("DELETE FROM record")
        conn.execute("DELETE FROM tag")
        conn.execute("DELETE FROM antenna")
    return {"message": "all data cleared"}
