# PulseWire V1.2 — Real Sources

即時新聞與輿情監測 MVP。Collector 使用 sources.json 管理來源，每個來源有自己的輪詢秒數；主迴圈每秒排程，最低 5 秒。

## 已啟用真實來源
- 中央社：即時頁 + 政治 / 國際 / 產經 / 科技 RSS
- 自由時報：即時 / 政治 / 國際 / 財經 RSS
- BBC：World / Business RSS
- The Guardian：World / Business RSS

TVBS、聯合、ETtoday、CNN、Reuters、AP 已放入 registry，但預設 disabled；正式啟用前應逐站確認穩定抓取方式、robots/條款與商業授權。

## 新增功能
- sources.json 來源 registry
- 每來源獨立 interval
- source_health 健康度：最後檢查、成功時間、錯誤、回應毫秒、抓到筆數
- /api/sources/health
- 每篇新聞記錄 source_id 與 latency_seconds
- CNA 即時頁 HTML collector（不等待 RSS）

## 本機
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
# 另一個 terminal
python collector.py

## Heroku
建立 Heroku Postgres，設定 DATABASE_URL 後：
- web: gunicorn app:app
- worker: python collector.py

注意：5 秒代表 PulseWire 最快每 5 秒檢查一次指定來源，不代表來源發布後保證 5 秒內可取得；RSS/API/網站本身的更新延遲仍會影響實際 latency。

## 商業授權
此專案只提供技術整合骨架。新聞標題、摘要、全文、圖片、RSS/API 的商業使用權依各來源條款而定。正式出售給媒體公司前，請建立來源授權清單並取得必要授權。

## V1.3 Live Search
- Search first checks the local PulseWire database.
- Clicking Search (or Enter) calls `/api/live-search`, queries live news search RSS for the keyword, de-duplicates by URL, stores results, then refreshes the dashboard.
- Search terms are stored as the article topic for live-search results, so they can be filtered/analyzed later.
- This is a discovery/indexing mechanism. Commercial deployments must review each underlying publisher's licensing/terms before displaying or storing content beyond permitted metadata/snippets.
