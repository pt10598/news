from flask import Flask, render_template, jsonify, request
from db import connect, init_db, IS_PG

app=Flask(__name__); init_db()
P='%s' if IS_PG else '?'

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/articles')
def articles():
    q=request.args.get('q','').strip(); region=request.args.get('region','all'); topic=request.args.get('topic','all')
    sql='SELECT * FROM articles WHERE 1=1'; args=[]
    if q:
        like=f'%{q}%'; sql+=f' AND (title LIKE {P} OR summary LIKE {P} OR source LIKE {P} OR topic LIKE {P})'; args += [like]*4
    if region!='all': sql+=f' AND region={P}'; args.append(region)
    if topic!='all': sql+=f' AND topic={P}'; args.append(topic)
    sql+=' ORDER BY discovered_at DESC LIMIT 250'
    with connect() as c: data=[dict(r) for r in c.execute(sql,args).fetchall()]
    for r in data:
        for k,v in list(r.items()):
            if hasattr(v,'isoformat'): r[k]=v.isoformat()
    return jsonify(data)

@app.get('/api/stats')
def stats():
    with connect() as c:
        if IS_PG:
            total=c.execute("SELECT count(*) n FROM articles WHERE discovered_at >= NOW()-INTERVAL '1 day'").fetchone()['n']
            recent=c.execute("SELECT count(*) n FROM articles WHERE discovered_at >= NOW()-INTERVAL '5 minutes'").fetchone()['n']
            breaking=c.execute("SELECT count(*) n FROM articles WHERE is_breaking=TRUE AND discovered_at >= NOW()-INTERVAL '1 day'").fetchone()['n']
        else:
            total=c.execute("SELECT count(*) n FROM articles WHERE discovered_at >= datetime('now','-1 day')").fetchone()['n']
            recent=c.execute("SELECT count(*) n FROM articles WHERE discovered_at >= datetime('now','-5 minutes')").fetchone()['n']
            breaking=c.execute("SELECT count(*) n FROM articles WHERE is_breaking=1 AND discovered_at >= datetime('now','-1 day')").fetchone()['n']
        sources=c.execute('SELECT count(DISTINCT source) n FROM articles').fetchone()['n']
        lat=c.execute('SELECT AVG(latency_seconds) n FROM articles WHERE latency_seconds >= 0').fetchone()['n']
    return jsonify(total=total,recent=recent,sources=sources,breaking=breaking,avg_latency=round(float(lat or 0),1))

@app.route('/api/topics',methods=['GET','POST'])
def topics():
    if request.method=='POST':
        d=request.get_json(force=True); name=(d.get('name') or '').strip(); keywords=(d.get('keywords') or '').strip()
        if not name or not keywords:return jsonify(error='name and keywords required'),400
        with connect() as c:
            try:c.execute(f'INSERT INTO watch_topics(name,keywords) VALUES({P},{P})',(name,keywords))
            except Exception:return jsonify(error='topic exists'),409
        return jsonify(ok=True)
    with connect() as c: data=[dict(r) for r in c.execute('SELECT * FROM watch_topics WHERE enabled=1 ORDER BY id DESC').fetchall()]
    return jsonify(data)
