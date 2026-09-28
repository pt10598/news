import os,time,re,calendar,json,html
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import feedparser, requests
from bs4 import BeautifulSoup
from db import connect,init_db,IS_PG

P='%s' if IS_PG else '?'
UA='PulseWire-MediaIntelligence/1.2 (+media-monitoring; contact configured by operator)'
SOURCES=json.loads(Path(os.getenv('SOURCES_FILE','sources.json')).read_text(encoding='utf-8'))
last_run={}

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

def health(source,ok,count=0,error=None,ms=None):
    now=datetime.now(timezone.utc)
    with connect() as c:
        if IS_PG:
            c.execute('''INSERT INTO source_health(source_id,source_name,last_checked,last_success,last_error,last_count,response_ms,status)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(source_id) DO UPDATE SET source_name=EXCLUDED.source_name,last_checked=EXCLUDED.last_checked,last_success=CASE WHEN EXCLUDED.status='ok' THEN EXCLUDED.last_checked ELSE source_health.last_success END,last_error=EXCLUDED.last_error,last_count=EXCLUDED.last_count,response_ms=EXCLUDED.response_ms,status=EXCLUDED.status''',
            (source['id'],source['name'],now,now if ok else None,error,count,ms,'ok' if ok else 'error'))
        else:
            c.execute('''INSERT INTO source_health(source_id,source_name,last_checked,last_success,last_error,last_count,response_ms,status)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET source_name=excluded.source_name,last_checked=excluded.last_checked,last_success=CASE WHEN excluded.status='ok' THEN excluded.last_checked ELSE source_health.last_success END,last_error=excluded.last_error,last_count=excluded.last_count,response_ms=excluded.response_ms,status=excluded.status''',
            (source['id'],source['name'],now.isoformat(),now.isoformat() if ok else None,error,count,ms,'ok' if ok else 'error'))

def insert_items(source,items):
    now=datetime.now(timezone.utc); added=0
    with connect() as c:
        topics=[dict(x) for x in c.execute('SELECT name,keywords FROM watch_topics WHERE enabled=1').fetchall()]
        for item in items[:80]:
            link=item.get('url','').strip(); title=re.sub('<[^>]+>','',html.unescape(item.get('title',''))).strip()
            if not link or not title: continue
            summary=re.sub('<[^>]+>',' ',item.get('summary',''))[:3000]; pd=item.get('published_at')
            latency=max(0,(now-pd).total_seconds()) if pd else None
            topic=classify(title+' '+summary,topics); breaking=bool(re.search(r'breaking|快訊|速報|urgent|重大',title,re.I))
            vals=(source['name'],source['region'],title,link,summary,pd,topic,breaking,latency,source['id'])
            if IS_PG:
                cur=c.execute('''INSERT INTO articles(source,region,title,url,summary,published_at,topic,is_breaking,latency_seconds,source_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(url) DO NOTHING RETURNING id''',vals)
                added += 1 if cur.fetchone() else 0
            else:
                v=list(vals); v[5]=pd.isoformat() if pd else None; v[7]=int(v[7])
                cur=c.execute('''INSERT OR IGNORE INTO articles(source,region,title,url,summary,published_at,topic,is_breaking,latency_seconds,source_id)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',v); added += max(0,cur.rowcount)
    return added

def rss(source):
    d=feedparser.parse(source['url'],request_headers={'User-Agent':UA})
    if getattr(d,'bozo',False) and not d.entries: raise RuntimeError(str(getattr(d,'bozo_exception','RSS parse failed')))
    return [{'title':e.get('title',''),'url':e.get('link',''),'summary':e.get('summary',''),'published_at':pub_dt(e)} for e in d.entries]

def cna_page(source):
    r=requests.get(source['url'],headers={'User-Agent':UA},timeout=8); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser'); out=[]
    for a in soup.select('a[href*="/news/"]'):
        title=' '.join(a.stripped_strings); href=a.get('href','')
        if len(title)<8 or not href: continue
        if href.startswith('/'): href='https://www.cna.com.tw'+href
        if href.startswith('https://www.cna.com.tw/news/'): out.append({'title':title,'url':href,'summary':'','published_at':None})
    seen={}; return [seen.setdefault(x['url'],x) for x in out if x['url'] not in seen]

def fetch(source):
    if source['type']=='rss': return rss(source)
    if source['id']=='cna_all': return cna_page(source)
    return []

def run_source(s):
    t=time.time()
    try:
        items=fetch(s); added=insert_items(s,items); ms=round((time.time()-t)*1000); health(s,True,len(items),None,ms)
        print(datetime.now(timezone.utc).isoformat(),s['name'],'items',len(items),'added',added,'ms',ms); return added
    except Exception as ex:
        ms=round((time.time()-t)*1000); health(s,False,0,str(ex)[:500],ms); print('source error',s['name'],ex); return 0

init_db(); enabled=[s for s in SOURCES if s.get('enabled')]
print(f'PulseWire collector v1.2 real sources: {len(enabled)} enabled / {len(SOURCES)} registry')
while True:
    now=time.time(); due=[]
    for s in enabled:
        if now-last_run.get(s['id'],0) >= max(5,int(s.get('interval',30))): due.append(s); last_run[s['id']]=now
    for s in due: run_source(s)
    time.sleep(1)
