"""Streamlit 台灣天氣預報互動儀表板。"""

import sqlite3

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from weather_data import DB_PATH, available_dates, load_weather_data, weather_for_date
from weather_extensions import build_agriculture_alerts, generate_ai_advice
from weather_map import build_temperature_map


st.set_page_config(page_title="台灣天氣預報儀表板", page_icon="🌤️", layout="wide")


@st.cache_data(show_spinner=False)
def cached_weather_data(db_path: str) -> pd.DataFrame:
    return load_weather_data(db_path)


def render_region_forecast(dataframe: pd.DataFrame) -> None:
    regions = sorted(dataframe["regionName"].unique().tolist())
    selected_region = st.selectbox("選擇地區", regions)
    region_data = dataframe.loc[dataframe["regionName"] == selected_region].copy()
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
    table_data = table_data.rename(columns={"dataDate": "日期", "mint": "最低溫", "maxt": "最高溫"})
    st.dataframe(
        table_data, use_container_width=True, hide_index=True,
        column_config={
            "最低溫": st.column_config.NumberColumn(format="%.1f °C"),
            "最高溫": st.column_config.NumberColumn(format="%.1f °C"),
            "日溫差": st.column_config.NumberColumn(format="%.1f °C"),
        },
    )

    st.subheader("AI 旅遊與穿搭建議")
    st.caption("未設定 OPENAI_API_KEY 時，系統會使用內建規則產生建議。")
    if st.button("產生建議", type="primary"):
        try:
            with st.spinner("正在整理建議..."):
                advice = generate_ai_advice(selected_region, latest["mint"], latest["maxt"])
            st.success(advice)
        except Exception as exc:
            st.error(f"AI 建議產生失敗：{exc}")


def render_map(dataframe: pd.DataFrame) -> None:
    dates = available_dates(dataframe)
    selected_date = st.date_input("選擇地圖日期", value=dates[-1], min_value=dates[0], max_value=dates[-1])
    daily_data = weather_for_date(dataframe, selected_date)
    if daily_data.empty:
        st.warning("這個日期沒有可顯示的氣溫資料。")
        return

    st.caption("🔵 <20°C　🟢 20–25°C　🟠 25–30°C　🔴 >30°C（依最高溫著色）")
    st_folium(build_temperature_map(daily_data), use_container_width=True, height=580)


def render_alerts(dataframe: pd.DataFrame) -> None:
    dates = available_dates(dataframe)
    selected_date = st.selectbox("警示日期", dates, index=len(dates) - 1, format_func=str)
    daily_data = weather_for_date(dataframe, selected_date)
    alerts = build_agriculture_alerts(daily_data.to_dict("records"))
    if not alerts:
        st.success("目前沒有低溫、高溫或劇烈日溫差警示。")
        return
    st.warning(f"偵測到 {len(alerts)} 個地區需要留意")
    st.dataframe(pd.DataFrame(alerts).rename(columns={"regionName": "地區", "level": "等級", "message": "警示內容"}),
                 use_container_width=True, hide_index=True)


def main() -> None:
    st.title("🌤️ 台灣天氣預報儀表板")
    st.caption("資料來源：交通部中央氣象署開放資料")
    try:
        weather_data = cached_weather_data(str(DB_PATH))
    except (FileNotFoundError, sqlite3.Error, pd.errors.DatabaseError) as exc:
        st.error(f"無法讀取天氣資料：{exc}")
        st.info("請先執行 `python fetch_weather.py` 建立資料庫。")
        return
    if weather_data.empty:
        st.warning("資料庫目前沒有可顯示的天氣資料。")
        return

    forecast_tab, map_tab, alert_tab = st.tabs(["📈 地區預報", "🗺️ 全台地圖", "🌾 農業警示"])
    with forecast_tab:
        render_region_forecast(weather_data)
    with map_tab:
        render_map(weather_data)
    with alert_tab:
        render_alerts(weather_data)


if __name__ == "__main__":
    main()
