"""天氣資料讀取與清理服務。"""

from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "data.db"


def load_weather_data(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    """從 SQLite 載入氣溫預報，並轉成可供前端使用的 DataFrame。"""
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"找不到資料庫：{path}")

    query = """
        SELECT regionName, dataDate, mint, maxt
        FROM TemperatureForecasts
        ORDER BY dataDate, regionName
    """
    with sqlite3.connect(path) as connection:
        dataframe = pd.read_sql_query(query, connection)

    if dataframe.empty:
        return dataframe

    dataframe["dataDate"] = pd.to_datetime(dataframe["dataDate"], errors="coerce")
    dataframe["mint"] = pd.to_numeric(dataframe["mint"], errors="coerce")
    dataframe["maxt"] = pd.to_numeric(dataframe["maxt"], errors="coerce")
    dataframe = dataframe.dropna(subset=["regionName", "dataDate", "mint", "maxt"])
    return dataframe.sort_values(["regionName", "dataDate"]).reset_index(drop=True)


def available_dates(dataframe: pd.DataFrame) -> list:
    """回傳資料中所有可選日期。"""
    return sorted(dataframe["dataDate"].dt.date.unique().tolist())


def weather_for_date(dataframe: pd.DataFrame, selected_date) -> pd.DataFrame:
    """篩選指定日期的全台天氣資料。"""
    return dataframe.loc[dataframe["dataDate"].dt.date == selected_date].copy()
