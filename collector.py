import os,time,re,calendar,feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from db import connect,init_db,IS_PG

P='%s' if IS_PG else '?'; POLL=max(5,int(os.getenv('POLL_SECONDS','5')))
FEEDS=[
 ('CNA 國際','國外','https://feeds.feedburner.com/rsscna/intworld'),
 ('CNA 產經','國內','https://feeds.feedburner.com/rsscna/finance'),
 ('BBC World','國外','https://feeds.bbci.co.uk/news/world/rss.xml'),
 ('BBC Business','國外','https://feeds.bbci.co.uk/news/business/rss.xml'),
 ('The Guardian World','國外','https://www.theguardian.com/world/rss'),
]
extra=os.getenv('EXTRA_FEEDS','').strip()
for i,u in enumerate([x.strip() for x in extra.split(',') if x.strip()]):FEEDS.append((f'Extra {i+1}','國外',u))

def pub_dt(e):
    for key in ('published_parsed','updated_parsed'):
        t=e.get(key)
        if t:
            try:return datetime.fromtimestamp(calendar.timegm(t),timezone.utc)
            except:pass
    for key in ('published','updated'):
        s=e.get(key)
        if s:
            try:
                d=parsedate_to_datetime(s); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except:pass
    return None

def classify(text,topics):
    low=text.lower()
    for t in topics:
        keys=[x.strip().lower() for x in t['keywords'].split(',') if x.strip()]
        if any(k in low for k in keys):return t['name']
    base={'AI/科技':['ai','人工智慧','nvidia','晶片','semiconductor','chip'], '財經':['stock','market','economy','finance','經濟','股市'], '國際':['war','election','government','president','戰爭','政府']}
    for name,keys in base.items():
        if any(k in low for k in keys):return name
    return '未分類'

def collect(name,region,url):
    d=feedparser.parse(url,request_headers={'User-Agent':'PulseWire-MediaIntelligence/1.1'})
    if getattr(d,'bozo',False) and not d.entries:return 0
    now=datetime.now(timezone.utc); added=0
    with connect() as c:
        topics=[dict(x) for x in c.execute('SELECT name,keywords FROM watch_topics WHERE enabled=1').fetchall()]
        for e in d.entries[:50]:
            link=e.get('link','').strip(); title=re.sub('<[^>]+>','',e.get('title','')).strip()
            if not link or not title:continue
            summary=e.get('summary','')[:3000]; pd=pub_dt(e); latency=max(0,(now-pd).total_seconds()) if pd else None
            topic=classify(title+' '+re.sub('<[^>]+>',' ',summary),topics)
            # Heuristic only: true AI/event clustering can replace this later.
            breaking=bool(re.search(r'breaking|快訊|速報|urgent',title,re.I))
            try:
                if IS_PG:
                    cur=c.execute('''INSERT INTO articles(source,region,title,url,summary,published_at,topic,is_breaking,latency_seconds)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(url) DO NOTHING RETURNING id''',(name,region,title,link,summary,pd,topic,breaking,latency))
                    added += 1 if cur.fetchone() else 0
                else:
                    cur=c.execute('''INSERT OR IGNORE INTO articles(source,region,title,url,summary,published_at,topic,is_breaking,latency_seconds)
                    VALUES(?,?,?,?,?,?,?,?,?)''',(name,region,title,link,summary,pd.isoformat() if pd else None,topic,int(breaking),latency))
                    added += cur.rowcount if cur.rowcount>0 else 0
            except Exception as ex:print('insert error',name,ex)
    return added

init_db();print(f'PulseWire collector v1.1 started: {POLL}s / {len(FEEDS)} feeds')
while True:
    start=time.time();added=0
    for f in FEEDS:
        try:added+=collect(*f)
        except Exception as ex:print('feed error',f[0],ex)
    print(datetime.now(timezone.utc).isoformat(),'added',added)
    time.sleep(max(0,POLL-(time.time()-start)))
