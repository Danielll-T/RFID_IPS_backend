import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

import src.db as db_module
from src.services.positioning import (
    load_data_from_db,
    sliding_window_features,
    train_rf_models,
    evaluate_position,
    load_reference_tags
)
from src.repository import insert_antenna, insert_tag, insert_record
from src.models import Antenna, Tag, Record
from src.db import get_connection

@ pytest.fixture(autouse=True)
def init_db(tmp_path):
    # 使用文件数据库，避免使用内存数据库
    test_db = tmp_path / "test_positioning.db"
    db_module.DB_PATH = str(test_db)
    db_module.initialize_database()
    # 插入测试数据：2天线，2标签，每标签3次读数
    with get_connection() as conn:
        # 天线
        insert_antenna(conn, Antenna(antenna_id="1", x=0.0, y=0.0))
        insert_antenna(conn, Antenna(antenna_id="2", x=1.0, y=1.0))
        # 标签：T1为ref, T2为tar
        insert_tag(conn, Tag(tag_id="T1", type="ref", true_x=0.0, true_y=0.0))
        insert_tag(conn, Tag(tag_id="T2", type="tar", true_x=2.0, true_y=2.0))
        # 插入3个时间点
        base_time = datetime(2025, 5, 1, 0, 0, 0)
        for i in range(3):
            t = base_time + timedelta(seconds=i)
            # T1
            insert_record(conn, Record(tag_id="T1", antenna_id="1", rc=1, rssi=-50.0, read_time=t))
            insert_record(conn, Record(tag_id="T1", antenna_id="2", rc=1, rssi=-60.0, read_time=t))
            # T2
            insert_record(conn, Record(tag_id="T2", antenna_id="1", rc=1, rssi=-55.0, read_time=t))
            insert_record(conn, Record(tag_id="T2", antenna_id="2", rc=1, rssi=-65.0, read_time=t))
    yield


def test_load_data_from_db():
    df = load_data_from_db()
    # 检查列
    expected_cols = {
        'TagID', 'read',
        'rssi_antenna1','rssi_antenna2',
        'rc_antenna1','rc_antenna2',
        'true_x','true_y'
    }
    assert expected_cols.issubset(set(df.columns))
    # 每个标签3条记录
    assert df[df.TagID=='T1'].shape[0] == 3
    assert df[df.TagID=='T2'].shape[0] == 3


def test_sliding_and_models():
    df = load_data_from_db()
    # 使用窗口大小2测试特征提取
    feats = sliding_window_features(df, first_window_size=2, window_size=2)
    # 计算特征列数量：原始特征4列，每种统计量4种，共16
    num_base = 4
    num_stats = 4
    # 检查部分统计特征列存在
    assert 'avg_rssi_antenna1' in feats.columns
    assert 'min_rc_antenna2' in feats.columns
    assert 'stddev_rssi_antenna2' in feats.columns
    # 样本行数仍为6
    assert feats.shape[0] == 6
    # 参考标签列表
    refs = load_reference_tags()
    assert refs == ['T1']
    # 训练模型，共使用16个特征
    regX, regY = train_rf_models(feats, refs, num_features=num_base*num_stats)
    # 模型应已训练
    assert hasattr(regX, 'predict') and hasattr(regY, 'predict')
    # 评估
    results = evaluate_position(feats, regX, regY, num_features=num_base*num_stats)
    # 验证结果行数和列
    assert set(results['TagID']) == {'T1','T2'}
    assert set(['MAE_x','MAE_y','MAE_avg']).issubset(results.columns)
    # 参考标签应近似0误差
    ref_row = results[results.TagID=='T1'].iloc[0]
    assert pytest.approx(ref_row.MAE_x, abs=1e-6) == 0
    assert pytest.approx(ref_row.MAE_y, abs=1e-6) == 0
