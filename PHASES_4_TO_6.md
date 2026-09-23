# 第 4～6 階段使用說明

## 啟動互動儀表板

```powershell
python -m pip install -r requirements.txt
python fetch_weather.py
streamlit run app.py
```

儀表板包含三個頁籤：地區預報、全台氣溫地圖與農業警示。地圖可依資料庫內的日期切換，並依最高溫顯示藍、綠、橘、紅色標記。

## AI 旅遊與穿搭建議

未設定 `OPENAI_API_KEY` 時會自動使用離線規則，不影響儀表板操作。若要使用 OpenAI Responses API，請複製 `.env.example` 的變數到 `.env`，填入金鑰；目前預設使用 `gpt-6-luna`，可透過 `OPENAI_MODEL` 更換。

> 現有程式會讀取作業系統環境變數。PowerShell 可用 `$env:OPENAI_API_KEY="..."` 設定當次工作階段。

## LINE 每日推播

先在 LINE Developers 建立 Messaging API channel，設定以下環境變數：

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`

預覽訊息，不實際送出：

```powershell
python push_daily_weather.py --region 臺北市 --dry-run
```

實際推播：

```powershell
python push_daily_weather.py --region 臺北市
```

可將實際推播命令加入 Windows 工作排程器，每天早晨執行。金鑰與 Token 不可提交到 Git；`.env` 已由 `.gitignore` 排除。

## 測試

```powershell
python -m unittest discover -s tests -v
```
