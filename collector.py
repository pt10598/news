import os,time,sqlite3,hashlib,feedparser
from datetime import datetime, timezone

DB=os.getenv('SQLITE_PATH','news.db'); POLL=max(5,int(os.getenv('POLL_SECONDS','5')))
# Public/demo feeds. For commercial use, review each provider's terms/licensing.
FEEDS=[
 ('CNA 國際','國外','https://feeds.feedburner.com/rsscna/intworld'),
 ('CNA 產經','國內','https://feeds.feedburner.com/rsscna/finance'),
 ('BBC World','國外','https://feeds.bbci.co.uk/news/world/rss.xml'),
 ('BBC Business','國外','https://feeds.bbci.co.uk/news/business/rss.xml'),
 ('The Guardian World','國外','https://www.theguardian.com/world/rss'),
]
extra=os.getenv('EXTRA_FEEDS','').strip()
for i,u in enumerate([x.strip() for x in extra.split(',') if x.strip()]): FEEDS.append((f'Extra {i+1}','國外',u))

def init():
 c=sqlite3.connect(DB); c.execute('''CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, region TEXT,title TEXT NOT NULL,url TEXT UNIQUE NOT NULL,summary TEXT,published_at TEXT,discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,sentiment TEXT DEFAULT '分析中',topic TEXT DEFAULT '未分類')'''); c.commit(); c.close()

def collect(name,region,url):
 d=feedparser.parse(url)
 if getattr(d,'bozo',False) and not d.entries: return 0
 c=sqlite3.connect(DB); n=0
 for e in d.entries[:40]:
  link=e.get('link','').strip(); title=e.get('title','').strip()
  if not link or not title: continue
  summary=e.get('summary','')[:2000]
  published=e.get('published', e.get('updated',''))
  try:
   c.execute('INSERT OR IGNORE INTO articles(source,region,title,url,summary,published_at) VALUES(?,?,?,?,?,?)',(name,region,title,link,summary,published)); n += c.total_changes>0
  except Exception: pass
 c.commit(); c.close(); return n

init(); print(f'collector started: {POLL}s')
while True:
 start=time.time(); added=0
 for f in FEEDS:
  try: added += collect(*f)
  except Exception as ex: print('feed error',f[0],ex)
 print(datetime.now(timezone.utc).isoformat(),'added',added)
 time.sleep(max(0,POLL-(time.time()-start)))
