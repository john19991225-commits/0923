"""Streamlit 台灣天氣預報互動儀表板。"""

import sqlite3

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from live_weather import (
    fetch_live_stations,
    fetch_radar_metadata,
    fetch_typhoons,
    fetch_warnings,
)
from weather_data import DB_PATH, available_dates, load_weather_data, weather_for_date
from weather_extensions import build_agriculture_alerts, generate_ai_advice
from weather_map import build_live_weather_map, build_temperature_map


st.set_page_config(page_title="台灣天氣預報儀表板", page_icon="🌤️", layout="wide")

LAYER_OPTIONS = {
    "🌡️ 氣溫": "temperature",
    "🌧️ 雨量": "precipitation",
    "🛰️ 雷達": "radar",
    "🌀 颱風": "typhoon",
    "💨 風速風向": "wind",
    "💧 濕度": "humidity",
    "⛅ 天氣": "weather",
    "📍 測站點位": "stations",
}


@st.cache_data(show_spinner=False)
def cached_weather_data(db_path: str) -> pd.DataFrame:
    return load_weather_data(db_path)


@st.cache_data(ttl=600, show_spinner=False)
def cached_live_stations() -> tuple[pd.DataFrame, dict]:
    return fetch_live_stations()


@st.cache_data(ttl=300, show_spinner=False)
def cached_radar() -> dict | None:
    return fetch_radar_metadata()


@st.cache_data(ttl=900, show_spinner=False)
def cached_typhoons() -> list[dict]:
    return fetch_typhoons()


@st.cache_data(ttl=600, show_spinner=False)
def cached_warnings() -> list[dict]:
    return fetch_warnings()


def _metric_extreme(dataframe: pd.DataFrame, column: str, maximum: bool = True) -> tuple[str, str]:
    valid = dataframe.dropna(subset=[column])
    if valid.empty:
        return "—", "無資料"
    row = valid.loc[valid[column].idxmax() if maximum else valid[column].idxmin()]
    return f"{row[column]:.1f}", str(row["stationName"])


def render_live_map() -> None:
    """呈現與參考網站相同的八種即時地圖模式。"""
    control1, control2, control3, control4, control5 = st.columns([2.2, 1.2, 1, 1, 1])
    layer_label = control1.selectbox("圖層", list(LAYER_OPTIONS), key="live_layer")
    basemap_label = control2.radio("底圖", ["深色", "街道圖"], horizontal=True, key="live_basemap")
    show_labels = control3.toggle("數字標籤", value=True, key="live_labels")
    show_stations = control4.toggle("測站點位", value=True, key="live_stations")
    show_counties = control5.toggle("縣市界線", value=True, key="live_counties")
    mode = LAYER_OPTIONS[layer_label]

    try:
        with st.spinner("正在取得中央氣象署即時資料..."):
            stations, meta = cached_live_stations()
    except Exception as exc:
        st.error(f"即時氣象資料載入失敗：{exc}")
        st.info("請確認 `.env` 中已有有效的 `CWA_API_KEY`。")
        return

    top_left, top_right = st.columns([5, 1])
    state = "舊快取" if meta.get("stale") else "快取" if meta.get("cached") else "即時"
    top_left.caption(f"資料來源：中央氣象署｜{state}資料｜觀測時間：{meta.get('updated', '—')}｜共 {len(stations)} 站")
    if top_right.button("🔄 更新資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    max_temp, max_temp_station = _metric_extreme(stations, "temperature")
    min_temp, min_temp_station = _metric_extreme(stations, "temperature", maximum=False)
    max_rain, max_rain_station = _metric_extreme(stations, "precipitation")
    max_wind, max_wind_station = _metric_extreme(stations, "windSpeed")
    cards = st.columns(4)
    cards[0].metric("最高溫", f"{max_temp} °C", max_temp_station, delta_color="off")
    cards[1].metric("最低溫", f"{min_temp} °C", min_temp_station, delta_color="off")
    cards[2].metric("最大雨量", f"{max_rain} mm", max_rain_station, delta_color="off")
    cards[3].metric("最大風速", f"{max_wind} m/s", max_wind_station, delta_color="off")

    warnings = cached_warnings()
    if warnings:
        with st.expander(f"⚠️ 氣象警特報（{len(warnings)}）", expanded=True):
            for warning in warnings:
                st.warning(f"**{warning['title']}**　{warning['issueTime']}\n\n{warning['content']}")
    else:
        st.success("✅ 目前無氣象警特報")

    radar = cached_radar() if mode == "radar" else None
    typhoons = cached_typhoons() if mode == "typhoon" else []
    if mode == "radar" and radar is None:
        st.warning("雷達圖層暫時無法取得，仍顯示測站位置。")
    if mode == "typhoon" and not typhoons:
        st.info("目前沒有活動中的熱帶氣旋。")

    st_folium(
        build_live_weather_map(
            stations, mode=mode,
            basemap="dark" if basemap_label == "深色" else "osm",
            show_labels=show_labels, show_stations=show_stations,
            show_counties=show_counties,
            radar=radar, typhoons=typhoons,
        ),
        use_container_width=True, height=650,
        key=f"live-map-{mode}-{basemap_label}-{show_labels}-{show_stations}-{show_counties}",
    )

    legends = {
        "temperature": "氣溫色階：🔵 <15　🟦 15–20　🟢 20–24　🟡 24–28　🟠 28–32　🔴 ≥32°C",
        "precipitation": "雨量色階：灰 0　藍 <2　綠 2–10　黃 10–30　橘 30–50　紅 ≥50 mm",
        "humidity": "濕度色階：黃 <50　綠 50–70　藍 70–85　深藍 ≥85%",
        "wind": "風速色階：綠 <2　黃 2–5　橘 5–10　紅 ≥10 m/s；箭頭顯示風向",
        "radar": "雷達回波圖資：RainViewer；可使用地圖右上角切換圖層。",
        "typhoon": "粉紅實線為分析路徑，黃色虛線為預報路徑。",
        "weather": "天氣圖示依各測站即時天氣描述顯示。",
        "stations": "點擊測站可查看完整即時觀測資料。",
    }
    st.caption(legends[mode])


def render_region_forecast(dataframe: pd.DataFrame) -> None:
    regions = sorted(dataframe["regionName"].unique().tolist())
    selected_region = st.selectbox("選擇地區", regions, key="region_selector")
    region_data = dataframe.loc[dataframe["regionName"] == selected_region].copy()
    latest = region_data.sort_values("dataDate").iloc[-1]

    # 地區改變時使用不同容器 key，避免瀏覽器保留上一個地區的局部畫面。
    with st.container(key=f"region-panel-{selected_region}"):
        st.caption(f"目前顯示：{selected_region}")
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
            table_data, width="stretch", hide_index=True,
            column_config={
                "最低溫": st.column_config.NumberColumn(format="%.1f °C"),
                "最高溫": st.column_config.NumberColumn(format="%.1f °C"),
                "日溫差": st.column_config.NumberColumn(format="%.1f °C"),
            },
        )

        st.subheader("AI 旅遊與穿搭建議")
        st.caption("未設定 OPENAI_API_KEY 時，系統會使用內建規則產生建議。")
        if st.button("產生建議", type="primary", key=f"advice-{selected_region}"):
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

    live_tab, forecast_tab, map_tab, alert_tab = st.tabs([
        "🗺️ 即時氣象地圖", "📈 地區預報", "🌡️ 預報地圖", "🌾 農業與 AI",
    ])
    with live_tab:
        render_live_map()
    with forecast_tab:
        render_region_forecast(weather_data)
    with map_tab:
        render_map(weather_data)
    with alert_tab:
        render_alerts(weather_data)


if __name__ == "__main__":
    main()
