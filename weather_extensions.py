"""第六階段：農業警示、AI 建議與 LINE 推播。"""

import json
import os
from typing import Any

import requests


def build_agriculture_alerts(records, cold_threshold: float = 10, hot_threshold: float = 35,
                             range_threshold: float = 10) -> list[dict[str, Any]]:
    """依低溫、高溫與劇烈日溫差產生農業防災警示。"""
    alerts = []
    for row in records:
        region = row["regionName"]
        mint, maxt = float(row["mint"]), float(row["maxt"])
        reasons = []
        if mint <= cold_threshold:
            reasons.append(f"低溫 {mint:.1f}°C，注意寒害")
        if maxt >= hot_threshold:
            reasons.append(f"高溫 {maxt:.1f}°C，注意熱害與灌溉")
        if maxt - mint >= range_threshold:
            reasons.append(f"日溫差 {maxt - mint:.1f}°C")
        if reasons:
            alerts.append({"regionName": region, "level": "警戒", "message": "；".join(reasons)})
    return alerts


def fallback_advice(region: str, mint: float, maxt: float) -> str:
    """沒有 AI 金鑰時仍可使用的規則式穿搭與行程建議。"""
    if mint < 15:
        clothes = "保暖外套、長袖與圍巾"
    elif mint < 22:
        clothes = "薄外套搭配長袖"
    elif maxt >= 30:
        clothes = "透氣短袖、防曬用品與充足飲水"
    else:
        clothes = "輕便衣物，早晚可備薄外套"
    range_note = "早晚溫差較大，建議洋蔥式穿搭。" if maxt - mint >= 8 else "日溫差平穩。"
    return f"{region}預報 {mint:.0f}–{maxt:.0f}°C，建議準備{clothes}。{range_note}"


def generate_ai_advice(region: str, mint: float, maxt: float, api_key: str | None = None) -> str:
    """透過 OpenAI Responses API 產生繁體中文建議，未設定金鑰則回退規則建議。"""
    key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    if not key:
        return fallback_advice(region, mint, maxt)

    prompt = (
        f"請用繁體中文，針對{region}最低溫{mint:.1f}°C、最高溫{maxt:.1f}°C，"
        "提供 80 字內的旅遊行程與穿搭建議。不要捏造降雨資訊。"
    )
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": os.getenv("OPENAI_MODEL", "gpt-6-luna"), "input": prompt},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("output_text"):
        return payload["output_text"].strip()
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "").strip()
    raise ValueError("AI 回應中沒有文字內容")


def push_line_message(message: str, user_id: str | None = None,
                      channel_token: str | None = None) -> None:
    """使用 LINE Messaging API 推播文字訊息。"""
    token = (channel_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")).strip()
    target = (user_id or os.getenv("LINE_USER_ID", "")).strip()
    if not token or not target:
        raise ValueError("請設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_USER_ID")
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps({"to": target, "messages": [{"type": "text", "text": message}]}),
        timeout=15,
    )
    response.raise_for_status()
