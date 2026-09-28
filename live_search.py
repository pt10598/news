import re, calendar, urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import feedparser
from db import connect, IS_PG

P='%s' if IS_PG else '?'

def _dt(e):
    for k in ('published_parsed','updated_parsed'):
        t=e.get(k)
        if t:
            try:return datetime.fromtimestamp(calendar.timegm(t),timezone.utc)
            except Exception:pass
    for k in ('published','updated'):
        if e.get(k):
            try:
                d=parsedate_to_datetime(e[k]); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except Exception:pass
    return None

def _clean(s): return re.sub(r'<[^>]+>',' ',s or '').strip()

def search_and_store(query, region='all', limit=80):
    query=(query or '').strip()
    if not query:return {'found':0,'inserted':0,'query':query}
    # Google News RSS is used as a discovery index; stored URLs still link outward to the news result/source.
    suffix=' when:7d'
    q=urllib.parse.quote(query+suffix)
    urls=[]
    if region in ('all','國內'):
        urls.append(('新聞搜尋・台灣','國內',f'https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant'))
    if region in ('all','國外'):
        urls.append(('News Search・Global','國外',f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'))
    now=datetime.now(timezone.utc); found=inserted=0
    with connect() as c:
        for search_source,reg,url in urls:
            d=feedparser.parse(url,request_headers={'User-Agent':'PulseWire-MediaIntelligence/1.3'})
            for e in d.entries[:limit]:
                title=_clean(e.get('title','')); link=e.get('link','').strip(); summary=_clean(e.get('summary',''))[:3000]
                if not title or not link:continue
                # Google News titles commonly end in " - Publisher"; preserve publisher separately when possible.
                source=search_source
                if ' - ' in title:
                    head,pub=title.rsplit(' - ',1)
                    if pub.strip(): title,source=head.strip(),pub.strip()
                pd=_dt(e); latency=max(0,(now-pd).total_seconds()) if pd else None; found+=1
                try:
                    if IS_PG:
                        cur=c.execute('''INSERT INTO articles(source,region,title,url,summary,published_at,topic,is_breaking,latency_seconds,source_id)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(url) DO NOTHING RETURNING id''',
                        (source,reg,title,link,summary,pd,query,False,latency,'live-search'))
                        inserted += 1 if cur.fetchone() else 0
                    else:
                        cur=c.execute('''INSERT OR IGNORE INTO articles(source,region,title,url,summary,published_at,topic,is_breaking,latency_seconds,source_id)
                        VALUES(?,?,?,?,?,?,?,?,?,?)''',(source,reg,title,link,summary,pd.isoformat() if pd else None,query,0,latency,'live-search'))
                        inserted += max(cur.rowcount,0)
                except Exception as ex: print('live search insert',ex)
    return {'found':found,'inserted':inserted,'query':query}
