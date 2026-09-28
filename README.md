# PulseWire – Media Intelligence V1

A deployable Flask demo for high-frequency RSS/Atom news discovery.

## Local
```bash
pip install -r requirements.txt
python collector.py
# in another terminal
flask --app app run
```
Open http://127.0.0.1:5000

## Heroku
Create an app, deploy this folder, then scale both processes:
```bash
heroku ps:scale web=1 collector=1
```
`POLL_SECONDS=5` is the default. The collector polls each configured feed in a loop and the browser refreshes its feed every 5 seconds.

## Important production notes
- V1 uses SQLite only to make the downloaded demo immediately runnable. On Heroku, SQLite is ephemeral: migrate the article repository to Heroku Postgres before production.
- Review provider terms, robots rules, licensing and rate limits before commercial ingestion.
- Five-second polling means the platform checks frequently; it does not guarantee a publisher's feed/API exposes an article within five seconds of publication.
- For scale: use Postgres + Redis queue + separate per-source collectors + SSE/WebSocket push.

## Next build
1. Postgres repository layer
2. Source management UI and health/latency metrics
3. AI topic, entity, sentiment and Chinese summaries
4. Event clustering and breaking-news detection
5. Multi-tenant accounts and alert rules
