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


def load_api_key_from_env() -> str:
    """從環境變數或 .env 檔案中自動讀取 CWA_API_KEY"""
    key = os.environ.get("CWA_API_KEY", "").strip()
    if key:
        return key

    candidate_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "myplan", ".env"),
        ".env"
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("CWA_API_KEY="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("CWA-"):
                            return line
            except Exception:
                pass
    return ""


def fetch_cwa_weather_json(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    【步驟 4】API 資料取得
    使用 requests 向中央氣象署 API 發送請求並取得 JSON 格式天氣資料。
    若無提供 API Key 或網路異常，則自動切換為展示資料。
    """
    if not api_key:
        api_key = load_api_key_from_env()

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


# =======================================================================
# 第二階段 (Phase 2) - 資料清洗與 SQLite 資料庫儲存
# 對應步驟：
#   - 步驟 7: 資料整理與預覽 (使用 Pandas 觀察資料)
#   - 步驟 8: 建立 SQLite 資料庫 (儲存氣溫資料)
#   - 步驟 9: 資料庫設計 (TemperatureForecasts 資料表與 UNIQUE 約束)
#   - 步驟 10: 查詢資料驗證 (使用 SQL 檢查資料)
#   - 步驟 20: 程式碼品質與優化 (防重複插入機制)
# =======================================================================

import sqlite3

try:
    import pandas as pd
except ImportError:
    pd = None

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "data.db")


def records_to_dataframe(records: List[Dict[str, Any]]) -> Any:
    """
    【步驟 7】資料整理與預覽
    使用 Pandas 將萃取的氣溫資料轉為結構化 DataFrame，並進行排序與清洗檢視。
    """
    if pd is None:
        print("[警告] 尚未安裝 pandas 套件，跳過 DataFrame 轉換。")
        return None

    df = pd.DataFrame(records)
    if not df.empty:
        df["mint"] = pd.to_numeric(df["mint"], errors="coerce")
        df["maxt"] = pd.to_numeric(df["maxt"], errors="coerce")
        df = df.sort_values(by=["regionName", "dataDate"]).reset_index(drop=True)

    print("\n" + "=" * 55)
    print(" 📊  步驟 7：使用 Pandas 觀察與預覽氣溫資料")
    print("=" * 55)
    print("資料前 5 筆預覽 (df.head())：")
    print(df.head())
    print("\n氣溫統計描述 (df[['mint', 'maxt']].describe())：")
    print(df[["mint", "maxt"]].describe())
    return df


def init_database(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    【步驟 8 & 9】建立 SQLite 資料庫與 Schema 設計
    建立 data/ 目錄與 data.db，創建 TemperatureForecasts 資料表。
    使用 UNIQUE(regionName, dataDate) 配合 INSERT OR REPLACE 保證重複執行不重複插入 (步驟 20 優化)。
    """
    db_folder = os.path.dirname(db_path)
    if db_folder and not os.path.exists(db_folder):
        os.makedirs(db_folder, exist_ok=True)
        print(f"[目錄] 已自動建立資料庫目錄: {db_folder}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS TemperatureForecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        regionName TEXT NOT NULL,
        dataDate TEXT NOT NULL,
        mint REAL NOT NULL,
        maxt REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(regionName, dataDate)
    );
    """
    cursor.execute(create_table_sql)
    conn.commit()
    print(f"[資料庫] 成功連接並初始化資料庫: {db_path}")
    print("[資料庫] 資料表 TemperatureForecasts 結構確認就緒。")
    return conn


def save_to_database(records_or_df: Any, db_path: str = DB_PATH) -> int:
    """
    【步驟 8 & 20】插入氣溫資料（防重複插入 UPSERT 機制）
    使用 INSERT OR REPLACE INTO 語法，當相同地區與相同日期再次寫入時自動更新，
    不會產生重複的髒資料。
    """
    conn = init_database(db_path)
    cursor = conn.cursor()

    # 若傳入的是 DataFrame 轉成 records，否則直接使用 list
    if pd is not None and isinstance(records_or_df, pd.DataFrame):
        rows = records_or_df[["regionName", "dataDate", "mint", "maxt"]].values.tolist()
    elif isinstance(records_or_df, list):
        rows = [(r["regionName"], r["dataDate"], r["mint"], r["maxt"]) for r in records_or_df]
    else:
        print("[錯誤] 無效的資料格式，無法寫入資料庫。")
        conn.close()
        return 0

    upsert_sql = """
    INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, mint, maxt)
    VALUES (?, ?, ?, ?);
    """
    cursor.executemany(upsert_sql, rows)
    conn.commit()
    inserted_count = len(rows)
    conn.close()

    print(f"[寫入] 成功儲存 {inserted_count} 筆氣溫記錄至 SQLite 資料庫 ({db_path})！")
    return inserted_count


def verify_database(db_path: str = DB_PATH) -> None:
    """
    【步驟 10】查詢資料驗證 (使用 SQL 檢查資料)
    執行課程指定 SQL 驗證指令：
      1. SELECT DISTINCT regionName FROM TemperatureForecasts;
      2. SELECT * FROM TemperatureForecasts WHERE regionName = '...';
      3. 總筆數統計
    """
    if not os.path.exists(db_path):
        print(f"[錯誤] 資料庫檔案不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 55)
    print(" 🔍  步驟 10：查詢資料驗證 (使用 SQL 檢查資料)")
    print("=" * 55)

    # 1. 統計總筆數
    cursor.execute("SELECT COUNT(*) FROM TemperatureForecasts;")
    total_count = cursor.fetchone()[0]
    print(f"[SQL 驗證 1] 總筆數查詢: 共 {total_count} 筆氣溫預報紀錄。")

    # 2. 查詢所有不重複地區
    cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName;")
    distinct_regions = [row[0] for row in cursor.fetchall()]
    print(f"[SQL 驗證 2] 收錄地區清單 ({len(distinct_regions)} 個地區)：")
    print("      " + "、".join(distinct_regions[:10]) + ("..." if len(distinct_regions) > 10 else ""))

    # 3. 示範條件查詢（例如北部、中部或特定縣市）
    sample_region = distinct_regions[0] if distinct_regions else "中部地區"
    cursor.execute(
        "SELECT id, regionName, dataDate, mint, maxt FROM TemperatureForecasts WHERE regionName = ? ORDER BY dataDate;",
        (sample_region,)
    )
    sample_rows = cursor.fetchall()
    print(f"\n[SQL 驗證 3] 條件查詢示範 (WHERE regionName = '{sample_region}')：")
    print(f"{'ID':<4} | {'地區':<8} | {'預報日期':<12} | {'最低溫 (MinT)':<10} | {'最高溫 (MaxT)':<10}")
    print("-" * 55)
    for row in sample_rows:
        print(f"{row[0]:<4} | {row[1]:<8} | {row[2]:<12} | {row[3]:>6.1f} °C   | {row[4]:>6.1f} °C")

    conn.close()
    print("=" * 55 + "\n")


if __name__ == "__main__":
    print("=== 正在啟動氣象資料管線 (Phase 1 & Phase 2) ===")

    # ---------------- 階段一 ----------------
    # 步驟 4: 取得 JSON
    raw_json = fetch_cwa_weather_json()

    # 步驟 5 & 6: 解析並萃取氣溫
    parsed_records = parse_and_extract_temperatures(raw_json)

    # ---------------- 階段二 ----------------
    # 步驟 7: Pandas 觀察與預覽
    df_weather = records_to_dataframe(parsed_records)

    # 步驟 8 & 9: 建立 SQLite 資料庫並寫入資料 (含重複執行不重複插入)
    save_to_database(df_weather if df_weather is not None else parsed_records)

    # 步驟 10: 執行 SQL 查詢驗證
    verify_database()
