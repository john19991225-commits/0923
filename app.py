"""第三階段：Streamlit 互動式天氣預報儀表板。"""

from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "data.db"


st.set_page_config(
    page_title="台灣天氣預報儀表板",
    page_icon="🌤️",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_weather_data(db_path: str) -> pd.DataFrame:
    """從 SQLite 載入氣溫預報，並完成前端需要的型別整理。"""
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

    dataframe["dataDate"] = pd.to_datetime(
        dataframe["dataDate"], errors="coerce"
    )
    dataframe["mint"] = pd.to_numeric(dataframe["mint"], errors="coerce")
    dataframe["maxt"] = pd.to_numeric(dataframe["maxt"], errors="coerce")
    dataframe = dataframe.dropna(
        subset=["regionName", "dataDate", "mint", "maxt"]
    )
    return dataframe.sort_values(["regionName", "dataDate"]).reset_index(drop=True)


def render_dashboard(dataframe: pd.DataFrame) -> None:
    """呈現地區篩選、摘要、溫度趨勢圖與資料表格。"""
    st.title("🌤️ 台灣天氣預報儀表板")
    st.caption("資料來源：交通部中央氣象署開放資料")

    regions = sorted(dataframe["regionName"].unique().tolist())
    selected_region = st.selectbox("選擇地區", regions)
    region_data = dataframe.loc[
        dataframe["regionName"] == selected_region
    ].copy()

    if region_data.empty:
        st.warning("目前沒有這個地區的預報資料。")
        return

    latest = region_data.sort_values("dataDate").iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("最新最低溫", f"{latest['mint']:.1f} °C")
    col2.metric("最新最高溫", f"{latest['maxt']:.1f} °C")
    col3.metric("最新日溫差", f"{latest['maxt'] - latest['mint']:.1f} °C")

    st.subheader(f"{selected_region}氣溫趨勢")
    chart_data = (
        region_data.set_index("dataDate")[["maxt", "mint"]]
        .rename(columns={"maxt": "最高溫", "mint": "最低溫"})
        .sort_index()
    )
    st.line_chart(chart_data, color=["#E4572E", "#2E86AB"])

    st.subheader("預報明細")
    table_data = region_data[["dataDate", "mint", "maxt"]].copy()
    table_data["日溫差"] = table_data["maxt"] - table_data["mint"]
    table_data["dataDate"] = table_data["dataDate"].dt.strftime("%Y-%m-%d")
    table_data = table_data.rename(
        columns={"dataDate": "日期", "mint": "最低溫", "maxt": "最高溫"}
    )
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "最低溫": st.column_config.NumberColumn(format="%.1f °C"),
            "最高溫": st.column_config.NumberColumn(format="%.1f °C"),
            "日溫差": st.column_config.NumberColumn(format="%.1f °C"),
        },
    )


def main() -> None:
    try:
        weather_data = load_weather_data(str(DB_PATH))
    except (FileNotFoundError, sqlite3.Error, pd.errors.DatabaseError) as exc:
        st.error(f"無法讀取天氣資料：{exc}")
        st.info("請先執行 `python fetch_weather.py` 建立資料庫。")
        return

    if weather_data.empty:
        st.warning("資料庫目前沒有可顯示的天氣資料。")
        st.info("請先執行 `python fetch_weather.py` 更新資料。")
        return

    render_dashboard(weather_data)


if __name__ == "__main__":
    main()
