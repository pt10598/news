# PulseWire – Media Intelligence V1.1

High-frequency domestic/international news discovery demo for a media-intelligence SaaS.

## Included
- 5-second collector loop (configurable with `POLL_SECONDS`)
- Taiwan + international RSS/Atom source layer
- SQLite zero-config local mode
- Automatic PostgreSQL mode when `DATABASE_URL` exists (Heroku-ready)
- URL deduplication
- Publication → discovery latency measurement
- Breaking flag heuristic
- Search + domestic/international filters
- Custom watch topics and keyword tagging
- AI-ready fields: sentiment, sentiment_score, analyzed_at, importance

## Local
```bash
pip install -r requirements.txt
python collector.py
# another terminal
flask --app app run
```
Open http://127.0.0.1:5000

## Heroku
Add Heroku Postgres, deploy this folder, then:
```bash
heroku config:set POLL_SECONDS=5
heroku ps:scale web=1 collector=1
```
Heroku supplies `DATABASE_URL`; PulseWire will then use PostgreSQL automatically.

## Environment
- `POLL_SECONDS=5`
- `EXTRA_FEEDS=https://example.com/feed.xml,https://example.org/rss`
- `DATABASE_URL=...` (automatic on Heroku Postgres)

## Important
Five-second polling means PulseWire checks a configured source frequently. It cannot guarantee a publisher exposes a new article within five seconds. Review each publisher's licensing, RSS/API terms, robots policy and rate limits before commercial ingestion.

## V1.2 recommended
1. AI analyzer worker: Chinese translation, summary, sentiment, entities
2. Redis queue so AI never blocks ingestion
3. Event clustering + real breaking detection based on cross-source velocity
4. Source health dashboard and per-source latency percentiles
5. Multi-tenant login + alert rules
