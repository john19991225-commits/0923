"""台灣即時氣象地圖風格的 Streamlit 儀表板。"""

import sqlite3

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from weather_data import DB_PATH, available_dates, load_weather_data, weather_for_date
from weather_extensions import build_agriculture_alerts, generate_ai_advice
from weather_map import build_temperature_map


st.set_page_config(page_title="台灣即時氣象地圖", page_icon="🌦️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background: #080d19; color: #e5e7eb; }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: rgba(15,23,42,.98); border-right: 1px solid #25324a; }
    .block-container { max-width: 100%; padding: .8rem 1.2rem 1.5rem; }
    h1 { font-size: 1.55rem !important; margin: 0 !important; }
    .hero { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:.65rem; }
    .brand { color:#f8fafc; font-size:1.35rem; font-weight:800; letter-spacing:.02em; }
    .live { color:#7dd3fc; font-size:.82rem; border:1px solid #075985; background:#082f49; padding:5px 10px; border-radius:999px; }
    .legend { border:1px solid #334155; border-radius:12px; padding:10px 14px; background:rgba(15,23,42,.92); margin-top:8px; }
    .gradient { height:10px; border-radius:8px; background:linear-gradient(90deg,#2c7bb6,#5aa2cf,#abd9e9,#7fcdbb,#d9ef8b,#fee08b,#fdae61,#f46d43,#d73027); }
    .ticks { display:flex; justify-content:space-between; color:#94a3b8; font-size:11px; margin-top:4px; }
    [data-testid="stMetric"] { background:#111827; border:1px solid #263449; border-radius:12px; padding:10px 14px; }
    iframe { border-radius:14px; border:1px solid #334155 !important; }
    .stTabs [data-baseweb="tab-list"] { gap:8px; }
    .stTabs [data-baseweb="tab"] { background:#111827; border-radius:9px; padding:8px 16px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_weather_data(db_path: str) -> pd.DataFrame:
    return load_weather_data(db_path)


def render_details(dataframe: pd.DataFrame, selected_region: str) -> None:
    region_data = dataframe.loc[dataframe["regionName"] == selected_region].sort_values("dataDate")
    latest = region_data.iloc[-1]
    cols = st.columns(3)
    cols[0].metric("最低溫", f"{latest['mint']:.1f} °C")
    cols[1].metric("最高溫", f"{latest['maxt']:.1f} °C")
    cols[2].metric("日溫差", f"{latest['maxt'] - latest['mint']:.1f} °C")
    chart = region_data.set_index("dataDate")[["maxt", "mint"]].rename(columns={"maxt": "最高溫", "mint": "最低溫"})
    st.line_chart(chart, color=["#fb7185", "#38bdf8"])
    if st.button("產生 AI 旅遊與穿搭建議", type="primary", use_container_width=True):
        try:
            with st.spinner("正在產生建議..."):
                st.success(generate_ai_advice(selected_region, latest["mint"], latest["maxt"]))
        except Exception as exc:
            st.error(f"AI 建議產生失敗：{exc}")


def main() -> None:
    try:
        weather_data = cached_weather_data(str(DB_PATH))
    except (FileNotFoundError, sqlite3.Error, pd.errors.DatabaseError) as exc:
        st.error(f"無法讀取天氣資料：{exc}")
        st.info("請先執行 `python fetch_weather.py` 建立資料庫。")
        return
    if weather_data.empty:
        st.warning("資料庫目前沒有可顯示的天氣資料。")
        return

    dates = available_dates(weather_data)
    regions = sorted(weather_data["regionName"].unique().tolist())

    with st.sidebar:
        st.markdown("## 🌦️ 地圖控制台")
        selected_date = st.select_slider("預報日期", options=dates, value=dates[-1], format_func=str)
        st.markdown("#### 圖層")
        show_boundaries = st.toggle("🌡️ 縣市氣溫色階", value=True)
        show_labels = st.toggle("🏷️ 氣溫數字標籤", value=True)
        show_stations = st.toggle("📍 測站點位", value=True)
        dark_basemap = st.radio("底圖", ["深色", "街道圖"], horizontal=True) == "深色"
        st.divider()
        selected_region = st.selectbox("快速查看縣市", regions)
        st.caption("地圖右上角也可即時切換圖層與底圖。")

    daily_data = weather_for_date(weather_data, selected_date)
    updated = daily_data["dataDate"].max().strftime("%Y-%m-%d")
    st.markdown(
        f"<div class='hero'><div><div class='brand'>台灣即時氣象地圖</div>"
        f"<div style='color:#94a3b8;font-size:.85rem'>中央氣象署開放資料視覺化</div></div>"
        f"<div class='live'>● 資料日期 {updated}</div></div>", unsafe_allow_html=True,
    )

    map_state = st_folium(
        build_temperature_map(daily_data, show_boundaries, show_labels, show_stations, dark_basemap),
        use_container_width=True, height=650, returned_objects=["last_object_clicked_tooltip"],
    )
    clicked = map_state.get("last_object_clicked_tooltip") if map_state else None
    if clicked:
        clicked_region = clicked.split(" ")[0]
        if clicked_region in regions:
            selected_region = clicked_region

    st.markdown("""
    <div class="legend"><div style="display:flex;gap:12px;align-items:center">
      <b>最高溫 °C</b><div style="flex:1"><div class="gradient"></div>
      <div class="ticks"><span>&lt;20</span><span>20</span><span>25</span><span>30</span><span>&gt;30</span></div></div>
    </div></div>
    """, unsafe_allow_html=True)

    detail_tab, alert_tab, data_tab = st.tabs([f"📊 {selected_region} 詳細預報", "🌾 農業防災警示", "📋 全台資料"])
    with detail_tab:
        render_details(weather_data, selected_region)
    with alert_tab:
        alerts = build_agriculture_alerts(daily_data.to_dict("records"))
        if alerts:
            st.warning(f"偵測到 {len(alerts)} 個地區需要留意")
            st.dataframe(pd.DataFrame(alerts).rename(columns={"regionName": "地區", "level": "等級", "message": "警示內容"}), use_container_width=True, hide_index=True)
        else:
            st.success("目前沒有低溫、高溫或劇烈日溫差警示。")
    with data_tab:
        table = daily_data.rename(columns={"regionName": "縣市", "dataDate": "日期", "mint": "最低溫", "maxt": "最高溫"})
        st.dataframe(table, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
