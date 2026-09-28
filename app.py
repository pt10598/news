import os, sqlite3
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
DB = os.getenv('SQLITE_PATH','news.db')

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS articles(
          id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, region TEXT,
          title TEXT NOT NULL, url TEXT UNIQUE NOT NULL, summary TEXT,
          published_at TEXT, discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
          sentiment TEXT DEFAULT '分析中', topic TEXT DEFAULT '未分類')''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_articles_discovered ON articles(discovered_at DESC)')
init_db()

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/articles')
def articles():
    q=request.args.get('q','').strip(); region=request.args.get('region','all')
    sql='SELECT * FROM articles WHERE 1=1'; args=[]
    if q: sql+=' AND (title LIKE ? OR summary LIKE ? OR source LIKE ?)'; args += [f'%{q}%']*3
    if region!='all': sql+=' AND region=?'; args.append(region)
    sql+=' ORDER BY discovered_at DESC LIMIT 250'
    with conn() as c: rows=[dict(r) for r in c.execute(sql,args)]
    return jsonify(rows)

@app.get('/api/stats')
def stats():
    with conn() as c:
        total=c.execute("SELECT count(*) n FROM articles WHERE discovered_at >= datetime('now','-1 day')").fetchone()['n']
        recent=c.execute("SELECT count(*) n FROM articles WHERE discovered_at >= datetime('now','-5 minutes')").fetchone()['n']
        sources=c.execute("SELECT count(DISTINCT source) n FROM articles").fetchone()['n']
    return jsonify(total=total,recent=recent,sources=sources)
