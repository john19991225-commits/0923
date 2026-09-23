"""排程執行入口：推播指定地區最新天氣與農業警示到 LINE。"""

import argparse
import sys

from weather_data import load_weather_data
from weather_extensions import build_agriculture_alerts, fallback_advice, push_line_message


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def build_daily_message(region: str) -> str:
    dataframe = load_weather_data()
    region_data = dataframe.loc[dataframe["regionName"] == region].sort_values("dataDate")
    if region_data.empty:
        raise ValueError(f"找不到地區：{region}")
    row = region_data.iloc[-1]
    date_text = row["dataDate"].strftime("%Y-%m-%d")
    advice = fallback_advice(region, row["mint"], row["maxt"])
    alerts = build_agriculture_alerts([row.to_dict()])
    alert_text = f"\n⚠️ {alerts[0]['message']}" if alerts else ""
    return f"🌤️ {date_text} 天氣提醒\n{advice}{alert_text}"


def main() -> None:
    parser = argparse.ArgumentParser(description="推播每日天氣到 LINE")
    parser.add_argument("--region", default="臺北市", help="要推播的縣市名稱")
    parser.add_argument("--dry-run", action="store_true", help="只顯示訊息，不實際推播")
    args = parser.parse_args()
    message = build_daily_message(args.region)
    if args.dry_run:
        print(message)
    else:
        push_line_message(message)
        print("LINE 天氣提醒已送出。")


if __name__ == "__main__":
    main()
