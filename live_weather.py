"""中央氣象署即時測站、警特報與颱風資料服務。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from fetch_weather import load_api_key_from_env


BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = BASE_DIR / "data" / "live_weather_cache.json"
CWA_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"


def _number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if result > -90 else None
    except (TypeError, ValueError):
        return None


def parse_stations(payload: dict[str, Any]) -> pd.DataFrame:
    """將 O-A0003-001 回應整理為即時觀測 DataFrame。"""
    stations = payload.get("records", {}).get("Station", [])
    rows = []
    for station in stations:
        geo = station.get("GeoInfo", {})
        coordinates = geo.get("Coordinates", [])
        coordinate = next((item for item in coordinates if item.get("CoordinateName") == "WGS84"), coordinates[0] if coordinates else {})
        weather = station.get("WeatherElement", {})
        now = weather.get("Now") or {}
        rows.append({
            "stationName": station.get("StationName", "未知測站"),
            "stationId": station.get("StationId", ""),
            "county": geo.get("CountyName", ""),
            "town": geo.get("TownName", ""),
            "latitude": _number(coordinate.get("StationLatitude")),
            "longitude": _number(coordinate.get("StationLongitude")),
            "obsTime": station.get("ObsTime", {}).get("DateTime", ""),
            "weather": weather.get("Weather") or "無資料",
            "temperature": _number(weather.get("AirTemperature")),
            "humidity": _number(weather.get("RelativeHumidity")),
            "precipitation": _number(now.get("Precipitation")),
            "windSpeed": _number(weather.get("WindSpeed")),
            "windDirection": _number(weather.get("WindDirection")),
            "pressure": _number(weather.get("AirPressure")),
            "uvIndex": _number(weather.get("UVIndex")),
        })
    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        return dataframe
    return dataframe.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def fetch_live_stations(force: bool = False, max_age_seconds: int = 600) -> tuple[pd.DataFrame, dict[str, Any]]:
    """取得即時測站資料；API 失敗時自動使用本地快取。"""
    cached = None
    if CACHE_PATH.is_file():
        try:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            age = datetime.now(timezone.utc).timestamp() - cached.get("cached_at", 0)
            if not force and age < max_age_seconds:
                return parse_stations(cached["payload"]), {"cached": True, "stale": False, "updated": cached.get("updated", "")}
        except (OSError, ValueError, KeyError):
            cached = None

    api_key = load_api_key_from_env()
    if not api_key:
        if cached:
            return parse_stations(cached["payload"]), {"cached": True, "stale": True, "updated": cached.get("updated", "")}
        raise ValueError("缺少 CWA_API_KEY，無法取得即時測站資料")

    try:
        response = requests.get(
            f"{CWA_URL}/O-A0003-001",
            params={"Authorization": api_key, "format": "JSON"}, timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        dataframe = parse_stations(payload)
        if dataframe.empty:
            raise ValueError("CWA API 未回傳有效測站")
        updated = str(dataframe["obsTime"].max())
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps({
            "cached_at": datetime.now(timezone.utc).timestamp(),
            "updated": updated, "payload": payload,
        }, ensure_ascii=False), encoding="utf-8")
        return dataframe, {"cached": False, "stale": False, "updated": updated}
    except (requests.RequestException, ValueError, OSError):
        if cached:
            return parse_stations(cached["payload"]), {"cached": True, "stale": True, "updated": cached.get("updated", "")}
        raise


def fetch_radar_metadata() -> dict[str, Any] | None:
    """取得 RainViewer 最新雷達圖磚資訊。"""
    try:
        response = requests.get("https://api.rainviewer.com/public/weather-maps.json", timeout=12)
        response.raise_for_status()
        payload = response.json()
        frames = payload.get("radar", {}).get("past", [])
        if payload.get("host") and frames:
            return {"host": payload["host"], "frame": frames[-1]}
    except (requests.RequestException, ValueError):
        pass
    return None


def _fetch_dataset(dataset_id: str) -> dict[str, Any]:
    api_key = load_api_key_from_env()
    if not api_key:
        return {}
    response = requests.get(
        f"{CWA_URL}/{dataset_id}",
        params={"Authorization": api_key, "format": "JSON"}, timeout=15,
    )
    response.raise_for_status()
    return response.json().get("records", {})


def fetch_warnings() -> list[dict[str, str]]:
    """取得目前氣象警特報摘要。"""
    try:
        records = _fetch_dataset("W-C0033-002").get("record", [])
        warnings = []
        for record in records:
            info = record.get("datasetInfo", {})
            content = record.get("contents", {}).get("content", {}).get("contentText", "")
            warnings.append({
                "title": info.get("datasetDescription", "氣象特報"),
                "issueTime": info.get("issueTime", ""),
                "content": " ".join(content.split()),
            })
        return warnings
    except (requests.RequestException, ValueError, AttributeError):
        return []


def fetch_typhoons() -> list[dict[str, Any]]:
    """取得活動中熱帶氣旋的分析與預報路徑。"""
    try:
        container = _fetch_dataset("W-C0034-005").get("TropicalCyclones", {})
        cyclones = container.get("TropicalCyclone", []) if isinstance(container, dict) else []
        if isinstance(cyclones, dict):
            cyclones = [cyclones]
        result = []
        for cyclone in cyclones:
            analysis = cyclone.get("AnalysisData", {}).get("Fix", [])
            forecast = cyclone.get("ForecastData", {}).get("Fix", [])
            if isinstance(analysis, dict):
                analysis = [analysis]
            if isinstance(forecast, dict):
                forecast = [forecast]
            result.append({
                "name": f"熱帶氣旋 TD{cyclone.get('CwaTdNo', '')}",
                "analysis": analysis, "forecast": forecast,
            })
        return result
    except (requests.RequestException, ValueError, AttributeError):
        return []
