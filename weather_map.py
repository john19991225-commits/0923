"""類 Windy 風格的台灣縣市氣溫互動地圖。"""

import json
from pathlib import Path

import folium
from folium.plugins import Fullscreen, LocateControl
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
COUNTY_GEOJSON = BASE_DIR / "data" / "tw_counties.geojson"

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

NAME_ALIASES = {
    "台北市": "臺北市", "台中市": "臺中市", "台南市": "臺南市",
    "台東縣": "臺東縣", "桃園縣": "桃園市",
}


def normalize_region(name: str) -> str:
    return NAME_ALIASES.get(name, name)


def temperature_color(temperature: float) -> str:
    if temperature < 20:
        return "#2c7bb6"
    if temperature < 25:
        return "#7fcdbb"
    if temperature <= 30:
        return "#fdae61"
    return "#d73027"


def _load_counties(dataframe: pd.DataFrame, geojson_path: Path) -> dict | None:
    if not geojson_path.is_file():
        return None
    counties = json.loads(geojson_path.read_text(encoding="utf-8"))
    values = {normalize_region(str(row.regionName)): row for row in dataframe.itertuples(index=False)}
    for feature in counties["features"]:
        name = normalize_region(feature["properties"].get("name", ""))
        feature["properties"]["display_name"] = name
        row = values.get(name)
        feature["properties"]["mint"] = float(row.mint) if row else None
        feature["properties"]["maxt"] = float(row.maxt) if row else None
    return counties


def build_temperature_map(
    dataframe: pd.DataFrame,
    show_boundaries: bool = True,
    show_labels: bool = True,
    show_stations: bool = True,
    dark_basemap: bool = True,
    geojson_path: Path = COUNTY_GEOJSON,
) -> folium.Map:
    """建立含縣市色階、標籤、定位與底圖切換的互動地圖。"""
    weather_map = folium.Map(
        location=[23.72, 121.0], zoom_start=7, min_zoom=6, max_zoom=12,
        tiles=None, control_scale=True, prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap © CARTO", name="深色底圖", show=dark_basemap,
    ).add_to(weather_map)
    folium.TileLayer("OpenStreetMap", name="街道圖", show=not dark_basemap).add_to(weather_map)

    counties = _load_counties(dataframe, geojson_path)
    if counties and show_boundaries:
        def style(feature):
            value = feature["properties"].get("maxt")
            return {
                "fillColor": temperature_color(value) if value is not None else "#374151",
                "color": "#e5e7eb", "weight": 1.1, "fillOpacity": 0.56,
            }

        folium.GeoJson(
            counties, name="縣市氣溫色階", style_function=style,
            highlight_function=lambda _: {"weight": 2.5, "color": "#ffffff", "fillOpacity": 0.75},
            tooltip=folium.GeoJsonTooltip(
                fields=["display_name", "mint", "maxt"],
                aliases=["縣市", "最低溫", "最高溫"],
                localize=True, sticky=True,
            ),
        ).add_to(weather_map)

    label_layer = folium.FeatureGroup(name="氣溫數字標籤", show=show_labels)
    station_layer = folium.FeatureGroup(name="測站點位", show=show_stations)
    for row in dataframe.itertuples(index=False):
        coordinates = REGION_COORDINATES.get(str(row.regionName))
        if coordinates is None:
            continue
        average = (float(row.mint) + float(row.maxt)) / 2
        popup = folium.Popup(
            f"<div style='min-width:170px;color:#111827'><b style='font-size:16px'>{row.regionName}</b>"
            f"<hr style='margin:7px 0'><b>{row.maxt:.1f}°</b> / {row.mint:.1f}°C"
            f"<br>平均溫度 {average:.1f}°C</div>", max_width=250,
        )
        folium.CircleMarker(
            coordinates, radius=6, color="#ffffff", weight=1.5,
            fill=True, fill_color=temperature_color(float(row.maxt)), fill_opacity=0.95,
            tooltip=f"{row.regionName} {row.mint:.0f}–{row.maxt:.0f}°C", popup=popup,
        ).add_to(station_layer)
        folium.Marker(
            coordinates,
            icon=folium.DivIcon(html=(
                "<div style='transform:translate(-50%,-42px);white-space:nowrap;"
                "background:rgba(15,23,42,.88);border:1px solid rgba(255,255,255,.45);"
                "border-radius:10px;padding:3px 7px;color:white;font:700 12px sans-serif;"
                f"box-shadow:0 2px 8px #0008'>{row.regionName}<br>{row.maxt:.0f}°</div>"
            )),
        ).add_to(label_layer)

    station_layer.add_to(weather_map)
    label_layer.add_to(weather_map)
    LocateControl(strings={"title": "定位我的位置"}, flyTo=True).add_to(weather_map)
    Fullscreen(position="topleft", title="全螢幕", title_cancel="離開全螢幕").add_to(weather_map)
    folium.LayerControl(position="topright", collapsed=False).add_to(weather_map)
    return weather_map
