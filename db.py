import os, sqlite3
from datetime import datetime, timezone

DATABASE_URL=os.getenv('DATABASE_URL','').strip()
SQLITE_PATH=os.getenv('SQLITE_PATH','news.db')
IS_PG=DATABASE_URL.startswith('postgres')

def connect():
    if IS_PG:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    c=sqlite3.connect(SQLITE_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    with connect() as c:
        if IS_PG:
            c.execute('''CREATE TABLE IF NOT EXISTS articles(
              id BIGSERIAL PRIMARY KEY, source TEXT, region TEXT, title TEXT NOT NULL,
              url TEXT UNIQUE NOT NULL, summary TEXT, published_at TIMESTAMPTZ,
              discovered_at TIMESTAMPTZ DEFAULT NOW(), analyzed_at TIMESTAMPTZ,
              sentiment TEXT DEFAULT '分析中', sentiment_score DOUBLE PRECISION,
              topic TEXT DEFAULT '未分類', importance INTEGER DEFAULT 0,
              is_breaking BOOLEAN DEFAULT FALSE, latency_seconds DOUBLE PRECISION, source_id TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS source_health(source_id TEXT PRIMARY KEY, source_name TEXT, last_checked TIMESTAMPTZ, last_success TIMESTAMPTZ, last_error TEXT, last_count INTEGER DEFAULT 0, response_ms INTEGER, status TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS watch_topics(
              id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, keywords TEXT NOT NULL,
              enabled BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW())''')
            c.execute('CREATE INDEX IF NOT EXISTS idx_articles_discovered ON articles(discovered_at DESC)')
            try: c.execute('ALTER TABLE articles ADD COLUMN source_id TEXT')
            except Exception: pass
            try: c.execute('ALTER TABLE articles ADD COLUMN source_id TEXT')
            except Exception: pass
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS articles(
              id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, region TEXT, title TEXT NOT NULL,
              url TEXT UNIQUE NOT NULL, summary TEXT, published_at TEXT,
              discovered_at TEXT DEFAULT CURRENT_TIMESTAMP, analyzed_at TEXT,
              sentiment TEXT DEFAULT '分析中', sentiment_score REAL,
              topic TEXT DEFAULT '未分類', importance INTEGER DEFAULT 0,
              is_breaking INTEGER DEFAULT 0, latency_seconds REAL, source_id TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS source_health(source_id TEXT PRIMARY KEY, source_name TEXT, last_checked TEXT, last_success TEXT, last_error TEXT, last_count INTEGER DEFAULT 0, response_ms INTEGER, status TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS watch_topics(
              id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, keywords TEXT NOT NULL,
              enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('CREATE INDEX IF NOT EXISTS idx_articles_discovered ON articles(discovered_at DESC)')

def rows(sql,args=()):
    with connect() as c:
        cur=c.execute(sql,args); return [dict(x) for x in cur.fetchall()]

def one(sql,args=()):
    with connect() as c:
        r=c.execute(sql,args).fetchone(); return dict(r) if r else None
