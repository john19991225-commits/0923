"""
=======================================================================
專案名稱：Taiwan Weather Forecast 台灣天氣預報應用
模組名稱：第一階段 (Phase 1) - 氣象資料取得與解析
對應課程步驟：
  - 步驟 3: 中央氣象署 CWA Open Data 平台
  - 步驟 4: API 資料取得 (使用 Requests 取得 JSON)
  - 步驟 5: JSON 資料結構解析 (定位 location 與 weatherElement)
  - 步驟 6: 提取最高與最低氣溫 (提取 MinT / MaxT，轉換成結構化資料)
=======================================================================
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# 設定標準輸出為 UTF-8 編碼，防止 Windows 命令提示字元 (CP950) 拋出 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import requests
except ImportError:
    requests = None

# 中央氣象署 (CWA) 一般天氣預報 (36小時) 資料集代碼
CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"


def get_mock_weather_data() -> Dict[str, Any]:
    """
    提供符合中央氣象署 CWA JSON 結構的範例測試資料。
    當使用者尚未設定 CWA_API_KEY 時，提供流暢的除錯與展示體驗。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "success": "true",
        "result": {"resource_id": "F-C0032-001"},
        "records": {
            "datasetDescription": "三十六小時天氣預報 (展示範例)",
            "location": [
                {
                    "locationName": "北部地區",
                    "weatherElement": [
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "22", "parameterUnit": "C"}
                                }
                            ]
                        },
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "28", "parameterUnit": "C"}
                                }
                            ]
                        }
                    ]
                },
                {
                    "locationName": "中部地區",
                    "weatherElement": [
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "23", "parameterUnit": "C"}
                                }
                            ]
                        },
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "31", "parameterUnit": "C"}
                                }
                            ]
                        }
                    ]
                },
                {
                    "locationName": "南部地區",
                    "weatherElement": [
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "24", "parameterUnit": "C"}
                                }
                            ]
                        },
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "32", "parameterUnit": "C"}
                                }
                            ]
                        }
                    ]
                },
                {
                    "locationName": "東部地區",
                    "weatherElement": [
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "21", "parameterUnit": "C"}
                                }
                            ]
                        },
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": f"{today} 06:00:00",
                                    "endTime": f"{today} 18:00:00",
                                    "parameter": {"parameterName": "27", "parameterUnit": "C"}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }


def fetch_cwa_weather_json(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    【步驟 4】API 資料取得
    使用 requests 向中央氣象署 API 發送請求並取得 JSON 格式天氣資料。
    若無提供 API Key 或網路異常，則自動切換為展示資料。
    """
    if not api_key:
        api_key = os.environ.get("CWA_API_KEY", "").strip()

    if not api_key:
        print("[資訊] 未偵測到 CWA_API_KEY 環境變數，切換至「離線展示資料模式」。")
        print("      提示：若要取得中央氣象署即時資料，請至 https://opendata.cwa.gov.tw/ 申請金鑰。")
        return get_mock_weather_data()

    if requests is None:
        print("[警告] 尚未安裝 requests 套件，切換至展示資料。請執行: pip install requests")
        return get_mock_weather_data()

    params = {
        "Authorization": api_key,
        "format": "JSON"
    }

    try:
        print(f"[連線] 正在發送 GET 請求至 CWA API...")
        response = requests.get(CWA_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print("[成功] 成功自中央氣象署 API 取得即時 JSON 資料！")
        return data
    except Exception as e:
        print(f"[錯誤] API 連線失敗 ({e})，自動降級切換至「展示資料模式」。")
        return get_mock_weather_data()


def parse_and_extract_temperatures(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    【步驟 5 & 6】JSON 資料結構解析 & 提取最高與最低氣溫
    走訪 records -> location，定位 MinT (最低溫) 與 MaxT (最高溫)，
    轉換為結構化資料清單：
    [
        {"regionName": "北部地區", "dataDate": "2026-09-23", "mint": 22.0, "maxt": 28.0},
        ...
    ]
    """
    records = json_data.get("records", {})
    locations = records.get("location", [])
    
    extracted_results: List[Dict[str, Any]] = []

    for loc in locations:
        region_name = loc.get("locationName", "未知地區")
        weather_elements = loc.get("weatherElement", [])
        
        mint_dict: Dict[str, float] = {}
        maxt_dict: Dict[str, float] = {}

        for elem in weather_elements:
            elem_name = elem.get("elementName", "")
            time_entries = elem.get("time", [])

            # 提取最低氣溫 MinT
            if elem_name == "MinT":
                for entry in time_entries:
                    start_time = entry.get("startTime", "")
                    date_str = start_time.split(" ")[0] if " " in start_time else start_time
                    val = float(entry.get("parameter", {}).get("parameterName", 0))
                    mint_dict[date_str] = val

            # 提取最高氣溫 MaxT
            elif elem_name == "MaxT":
                for entry in time_entries:
                    start_time = entry.get("startTime", "")
                    date_str = start_time.split(" ")[0] if " " in start_time else start_time
                    val = float(entry.get("parameter", {}).get("parameterName", 0))
                    maxt_dict[date_str] = val

        # 整合 MinT 與 MaxT 至同一筆日期的記錄
        all_dates = sorted(set(list(mint_dict.keys()) + list(maxt_dict.keys())))
        for d in all_dates:
            extracted_results.append({
                "regionName": region_name,
                "dataDate": d,
                "mint": mint_dict.get(d, 0.0),
                "maxt": maxt_dict.get(d, 0.0)
            })

    return extracted_results


def print_extracted_data(records: List[Dict[str, Any]]) -> None:
    """
    格式化印出第一階段萃取出的氣象數據表格。
    """
    print("\n" + "=" * 55)
    print(" 🌤️  第一階段成果：全台地區氣溫預報萃取結果")
    print("=" * 55)
    print(f"{'地區 (regionName)':<15} | {'預報日期 (dataDate)':<14} | {'最低溫 (MinT)':<10} | {'最高溫 (MaxT)':<10}")
    print("-" * 55)
    for r in records:
        print(f"{r['regionName']:<15} | {r['dataDate']:<14} | {r['mint']:>6.1f} °C   | {r['maxt']:>6.1f} °C")
    print("=" * 55)
    print(f"總計成功解析 {len(records)} 筆結構化氣象資料。\n")


if __name__ == "__main__":
    print("=== 正在啟動第一階段：氣象資料 API 取得與 JSON 解析 ===")
    
    # 步驟 4: 取得 JSON
    raw_json = fetch_cwa_weather_json()
    
    # 步驟 5 & 6: 解析並萃取氣溫
    parsed_records = parse_and_extract_temperatures(raw_json)
    
    # 呈現結果
    print_extracted_data(parsed_records)
