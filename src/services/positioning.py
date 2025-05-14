# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import warnings
from ..db import get_connection
from datetime import datetime

warnings.filterwarnings('ignore')


def load_data_from_db() -> pd.DataFrame:
    """
    从 SQLite 数据库读取 record 和 tag 表，构建基础 DataFrame。
    返回列: ['TagID', 'read', 'rssi_antenna...', 'rc_antenna...', 'true_x', 'true_y']
    """
    with get_connection() as conn:
        # 读取 record 表
        df_records = pd.read_sql_query(
            "SELECT tag_id AS TagID, antenna_id, rssi, rc, read_time FROM record",
            conn,
            parse_dates=["read_time"]
        )
        # 读取 tag 表的真实坐标
        df_tags = pd.read_sql_query(
            "SELECT tag_id AS TagID, true_x, true_y FROM tag",
            conn
        )
    # 将 rssi 数据 pivot 为宽表
    df_rssi = df_records.pivot_table(
        index=["TagID", "read_time"],
        columns="antenna_id",
        values="rssi"
    )
    df_rssi.columns = [f"rssi_antenna{col}" for col in df_rssi.columns]

    # 将 rc 数据 pivot 为宽表
    df_rc = df_records.pivot_table(
        index=["TagID", "read_time"],
        columns="antenna_id",
        values="rc"
    )
    df_rc.columns = [f"rc_antenna{col}" for col in df_rc.columns]

    # 合并 rssi 和 rc
    df_base = pd.concat([df_rssi, df_rc], axis=1).reset_index()
    # 重命名 read_time -> read
    df_base = df_base.rename(columns={"read_time": "read"})
    # 合并真值坐标
    dbase = pd.merge(df_base, df_tags, on="TagID", how="left")
    return dbase


def load_reference_tags() -> list:
    """
    从数据库获取所有参考标签(Tag.type='ref')的 TagID 列表
    """
    with get_connection() as conn:
        df_ref = pd.read_sql_query(
            "SELECT tag_id AS TagID FROM tag WHERE type='ref'",
            conn
        )
    return df_ref['TagID'].tolist()


def sliding_window_features(
    dbase: pd.DataFrame,
    first_window_size: int = 10,
    window_size: int = 10
) -> pd.DataFrame:
    """
    对基础 DataFrame 做滑动窗口特征提取。
    """
    newdbase = dbase.iloc[0:0].copy()
    tags = np.unique(dbase['TagID'].values)
    # 动态获取天线数量
    num_ant = len([c for c in dbase.columns if c.startswith('rssi_antenna')])
    rssi_cols = [f'rssi_antenna{i+1}' for i in range(num_ant)]
    rc_cols   = [f'rc_antenna{i+1}'   for i in range(num_ant)]

    for tag in tags:
        df_tag = dbase[dbase['TagID']==tag].reset_index(drop=True)
        n = len(df_tag)
        # 首窗口
        window = df_tag.loc[0:first_window_size-1, rssi_cols+rc_cols].values if n>=first_window_size else df_tag.loc[0:n-1, rssi_cols+rc_cols].values
        stats = {p: np.around(func(window,axis=0),4) for p,func in
                 [('avg',np.mean), ('min',np.min), ('max',np.max), ('stddev',np.std)]}
        for i in range(min(first_window_size, n)):
            for prefix in stats:
                df_tag.loc[i, [f'{prefix}_{c}' for c in rssi_cols+rc_cols]] = stats[prefix]
        # 后续窗口
        for i in range(first_window_size, n):
            beg = max(0, i-window_size+1)
            window = df_tag.loc[beg:i, rssi_cols+rc_cols].values
            stats = {p: np.around(func(window,axis=0),4) for p,func in
                     [('avg',np.mean), ('min',np.min), ('max',np.max), ('stddev',np.std)]}
            for prefix in stats:
                df_tag.loc[i, [f'{prefix}_{c}' for c in rssi_cols+rc_cols]] = stats[prefix]
        newdbase = pd.concat([newdbase, df_tag], ignore_index=True)

    # 将关键列移至末尾
    for col in ['TagID', 'read', 'true_x', 'true_y']:
        if col in newdbase.columns:
            vals = newdbase.pop(col)
            newdbase[col] = vals
    # 排序并重置索引
    newdbase = newdbase.sort_values(by=['read','TagID']).reset_index(drop=True)
    return newdbase


def train_rf_models(
    feature_df: pd.DataFrame,
    reference_tags: list,
    num_features: int
):
    """
    训练 X、Y 方向的随机森林回归模型。
    """
    landmarc = feature_df[feature_df['TagID'].isin(reference_tags)]
    X = landmarc.iloc[:, :num_features].values
    yx = landmarc['true_x'].values
    yy = landmarc['true_y'].values

    regX = RandomForestRegressor(n_estimators=1000, random_state=0)
    regY = RandomForestRegressor(n_estimators=1000, random_state=0)
    regX.fit(X, yx)
    regY.fit(X, yy)
    return regX, regY


def evaluate_position(
    feature_df: pd.DataFrame,
    regX: RandomForestRegressor,
    regY: RandomForestRegressor,
    num_features: int
) -> pd.DataFrame:
    """
    对所有标签进行位置预测并计算 MAE。
    """
    tags = np.unique(feature_df['TagID'].values)
    records = []
    for tag in tags:
        df_tag = feature_df[feature_df['TagID']==tag]
        Xtest = df_tag.iloc[:, :num_features].values
        yx_true = df_tag['true_x'].values
        yy_true = df_tag['true_y'].values
        yx_pred = regX.predict(Xtest)
        yy_pred = regY.predict(Xtest)
        mae_x = mean_absolute_error(yx_true, yx_pred)
        mae_y = mean_absolute_error(yy_true, yy_pred)
        records.append({
            'TagID': tag,
            'MAE_x': round(mae_x,4),
            'MAE_y': round(mae_y,4),
            'MAE_avg': round((mae_x+mae_y)/2,4)
        })
    return pd.DataFrame(records)


if __name__ == '__main__':
    # 参数配置
    FIRST_WINDOW = 10
    WINDOW_SIZE = 10
    NUM_FEATURES = 40  # 前 num_features 列作为特征

    # 1. 从数据库加载原始观测数据
    raw = load_data_from_db()
    # 2. 从数据库获取参考标签列表
    REFERENCE_TAGS = load_reference_tags()
    # 3. 滑动窗口特征提取
    feats = sliding_window_features(raw, FIRST_WINDOW, WINDOW_SIZE)
    # 4. 训练模型
    regX, regY = train_rf_models(feats, REFERENCE_TAGS, NUM_FEATURES)
    # 5. 评估所有标签
    results = evaluate_position(feats, regX, regY, NUM_FEATURES)
    print(results.to_string(index=False))
