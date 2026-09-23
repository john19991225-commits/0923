"""台灣縣市氣溫地圖。"""

import json
from pathlib import Path

import folium
from folium.plugins import Fullscreen, LocateControl
import pandas as pd


COUNTY_GEOJSON = Path(__file__).resolve().parent / "data" / "tw_counties.geojson"


REGION_COORDINATES = {
    "基隆市": (25.1283, 121.7419), "臺北市": (25.0375, 121.5637),
    "台北市": (25.0375, 121.5637), "新北市": (25.0120, 121.4657),
    "桃園市": (24.9937, 121.3010), "新竹市": (24.8138, 120.9675),
    "新竹縣": (24.8390, 121.0177), "苗栗縣": (24.5602, 120.8214),
    "臺中市": (24.1477, 120.6736), "台中市": (24.1477, 120.6736),
    "彰化縣": (24.0756, 120.5440), "南投縣": (23.9609, 120.9719),
    "雲林縣": (23.7092, 120.4313), "嘉義市": (23.4801, 120.4491),
    "嘉義縣": (23.4518, 120.2555), "臺南市": (22.9999, 120.2269),
    "台南市": (22.9999, 120.2269), "高雄市": (22.6273, 120.3014),
    "屏東縣": (22.5519, 120.5488), "宜蘭縣": (24.7021, 121.7378),
    "花蓮縣": (23.9911, 121.6112), "臺東縣": (22.7554, 121.1500),
    "台東縣": (22.7554, 121.1500), "澎湖縣": (23.5712, 119.5793),
    "金門縣": (24.4494, 118.3767), "連江縣": (26.1605, 119.9517),
}


def temperature_color(temperature: float) -> str:
    if temperature < 20:
        return "blue"
    if temperature < 25:
        return "green"
    if temperature <= 30:
        return "orange"
    return "red"


def build_temperature_map(dataframe: pd.DataFrame) -> folium.Map:
    weather_map = folium.Map(location=[23.7, 121.0], zoom_start=7, tiles="OpenStreetMap")
    for row in dataframe.itertuples(index=False):
        coordinates = REGION_COORDINATES.get(row.regionName)
        if coordinates is None:
            continue
        average = (float(row.mint) + float(row.maxt)) / 2
        popup = (
            f"<b>{row.regionName}</b><br>"
            f"最低溫：{row.mint:.1f} °C<br>"
            f"最高溫：{row.maxt:.1f} °C<br>"
            f"平均溫：{average:.1f} °C"
        )
        folium.CircleMarker(
            location=coordinates, radius=9,
            color=temperature_color(float(row.maxt)), fill=True, fill_opacity=0.8,
            tooltip=f"{row.regionName}：{row.mint:.0f}–{row.maxt:.0f} °C",
            popup=folium.Popup(popup, max_width=240),
        ).add_to(weather_map)
    return weather_map


def observation_color(mode: str, value: float | None) -> str:
    """依即時觀測圖層與數值回傳顏色。"""
    if value is None:
        return "#64748b"
    if mode == "temperature":
        if value < 15: return "#2c7bb6"
        if value < 20: return "#5aa2cf"
        if value < 24: return "#7fcdbb"
        if value < 28: return "#fee08b"
        if value < 32: return "#fdae61"
        return "#d73027"
    if mode == "precipitation":
        if value <= 0: return "#475569"
        if value < 2: return "#38bdf8"
        if value < 10: return "#22c55e"
        if value < 30: return "#facc15"
        if value < 50: return "#f97316"
        return "#ef4444"
    if mode == "humidity":
        if value < 50: return "#facc15"
        if value < 70: return "#34d399"
        if value < 85: return "#38bdf8"
        return "#2563eb"
    if mode == "wind":
        if value < 2: return "#86efac"
        if value < 5: return "#facc15"
        if value < 10: return "#fb923c"
        return "#ef4444"
    return "#38bdf8"


def weather_icon(description: str) -> str:
    if any(word in description for word in ("雷", "電閃")): return "⛈️"
    if any(word in description for word in ("雨", "陣雨")): return "🌧️"
    if any(word in description for word in ("霧", "靄")): return "🌫️"
    if "陰" in description: return "☁️"
    if "雲" in description: return "⛅"
    return "☀️"


def _station_popup(row) -> folium.Popup:
    def show(value, unit=""):
        return "—" if value is None or pd.isna(value) else f"{value:.1f}{unit}"
    html = (
        f"<div style='min-width:220px;color:#0f172a;font-family:sans-serif'>"
        f"<b style='font-size:16px'>{row.stationName}</b><br>"
        f"<span style='color:#64748b'>{row.county}{row.town}｜{row.obsTime}</span><hr>"
        f"天氣：{weather_icon(str(row.weather))} {row.weather}<br>"
        f"氣溫：<b>{show(row.temperature, '°C')}</b>　濕度：{show(row.humidity, '%')}<br>"
        f"雨量：{show(row.precipitation, ' mm')}　風速：{show(row.windSpeed, ' m/s')}<br>"
        f"風向：{show(row.windDirection, '°')}　氣壓：{show(row.pressure, ' hPa')}</div>"
    )
    return folium.Popup(html, max_width=300)


def build_live_weather_map(
    stations: pd.DataFrame,
    mode: str = "temperature",
    basemap: str = "dark",
    show_labels: bool = True,
    show_stations: bool = True,
    show_counties: bool = True,
    radar: dict | None = None,
    typhoons: list[dict] | None = None,
) -> folium.Map:
    """建立即時氣象圖層地圖，對應參考網站的主要八種模式。"""
    weather_map = folium.Map(location=[23.7, 121.0], zoom_start=7, tiles=None, control_scale=True)
    folium.TileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap © CARTO", name="深色", show=basemap == "dark",
    ).add_to(weather_map)
    folium.TileLayer("OpenStreetMap", name="街道圖", show=basemap == "osm").add_to(weather_map)

    if show_counties and COUNTY_GEOJSON.is_file():
        counties = json.loads(COUNTY_GEOJSON.read_text(encoding="utf-8"))
        folium.GeoJson(
            counties, name="縣市界線",
            style_function=lambda _: {
                "fillColor": "transparent", "fillOpacity": 0.02,
                "color": "#e2e8f0", "weight": 1.2, "opacity": 0.85,
            },
            highlight_function=lambda _: {"weight": 2.5, "color": "#ffffff"},
            tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["縣市"]),
        ).add_to(weather_map)

    if mode == "radar" and radar:
        frame = radar["frame"]
        path = frame.get("path", "")
        timestamp = frame.get("time", "")
        folium.TileLayer(
            tiles=f"{radar['host']}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
            attr="RainViewer", name=f"雷達 {timestamp}", overlay=True,
            opacity=0.72, show=True,
        ).add_to(weather_map)

    if mode == "typhoon":
        for cyclone in typhoons or []:
            analysis = [
                [float(p["CoordinateLatitude"]), float(p["CoordinateLongitude"])]
                for p in cyclone.get("analysis", []) if p.get("CoordinateLatitude") and p.get("CoordinateLongitude")
            ]
            forecast = [
                [float(p["CoordinateLatitude"]), float(p["CoordinateLongitude"])]
                for p in cyclone.get("forecast", []) if p.get("CoordinateLatitude") and p.get("CoordinateLongitude")
            ]
            if analysis:
                folium.PolyLine(analysis, color="#fb7185", weight=3, tooltip=f"{cyclone['name']} 過去路徑").add_to(weather_map)
                folium.Marker(analysis[-1], tooltip=cyclone["name"], icon=folium.DivIcon(html="<div style='font-size:28px'>🌀</div>")).add_to(weather_map)
            if forecast:
                start = [analysis[-1]] if analysis else []
                folium.PolyLine(start + forecast, color="#facc15", weight=3, dash_array="8 7", tooltip="預報路徑").add_to(weather_map)

    if mode not in ("radar", "typhoon") or show_stations:
        for row in stations.itertuples(index=False):
            location = [row.latitude, row.longitude]
            popup = _station_popup(row)
            if mode == "weather":
                icon = weather_icon(str(row.weather))
                folium.Marker(location, popup=popup, tooltip=f"{row.stationName} {row.weather}", icon=folium.DivIcon(
                    html=f"<div style='font-size:22px;filter:drop-shadow(0 1px 2px #000)'>{icon}</div>"
                )).add_to(weather_map)
                continue
            if mode == "stations" or mode in ("radar", "typhoon"):
                value, unit, color = None, "", "#38bdf8"
            elif mode == "precipitation":
                value, unit = row.precipitation, "mm"
                color = observation_color(mode, value)
            elif mode == "humidity":
                value, unit = row.humidity, "%"
                color = observation_color(mode, value)
            elif mode == "wind":
                value, unit = row.windSpeed, "m/s"
                color = observation_color(mode, value)
            else:
                value, unit = row.temperature, "°"
                color = observation_color("temperature", value)

            tooltip = f"{row.stationName}：{'—' if value is None or pd.isna(value) else f'{value:.1f}{unit}'}"
            folium.CircleMarker(
                location, radius=5 if mode == "stations" else 7,
                color="#f8fafc", weight=1, fill=True, fill_color=color,
                fill_opacity=0.9, tooltip=tooltip, popup=popup,
            ).add_to(weather_map)
            if mode == "wind" and row.windDirection is not None and not pd.isna(row.windDirection):
                folium.Marker(location, icon=folium.DivIcon(html=(
                    f"<div style='transform:rotate({row.windDirection:.0f}deg);color:white;font-size:18px;"
                    "text-shadow:0 1px 3px #000'>↑</div>"
                ))).add_to(weather_map)
            elif show_labels and value is not None and not pd.isna(value) and mode not in ("stations", "radar", "typhoon"):
                folium.Marker(location, icon=folium.DivIcon(html=(
                    "<div style='transform:translate(7px,-23px);white-space:nowrap;color:white;"
                    "font:700 11px sans-serif;text-shadow:0 1px 3px #000'>"
                    f"{value:.0f}{unit}</div>"
                ))).add_to(weather_map)

    LocateControl(strings={"title": "定位我的位置"}, flyTo=True).add_to(weather_map)
    Fullscreen(position="topleft", title="全螢幕", title_cancel="離開全螢幕").add_to(weather_map)
    folium.LayerControl(position="topright", collapsed=True).add_to(weather_map)
    return weather_map
