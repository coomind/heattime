from contextlib import contextmanager
from pathlib import Path
import sqlite3,json
from fastapi.encoders import jsonable_encoder

class Repository:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS resources(kind TEXT,id TEXT,body TEXT NOT NULL,PRIMARY KEY(kind,id))")
    @contextmanager
    def connect(self):
        conn=sqlite3.connect(self.path,timeout=30)
        try:
            with conn:yield conn
        finally:conn.close()
    def put(self,kind,id,body,conn=None):
        text=json.dumps(jsonable_encoder(body),ensure_ascii=False,allow_nan=False)
        sql="INSERT INTO resources VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body"
        if conn is not None:conn.execute(sql,(kind,id,text))
        else:
            with self.connect() as con:con.execute(sql,(kind,id,text))
        return json.loads(text)
    def get(self,kind,id,conn=None):
        if conn is not None:row=conn.execute("SELECT body FROM resources WHERE kind=? AND id=?",(kind,id)).fetchone()
        else:
            with self.connect() as con:row=con.execute("SELECT body FROM resources WHERE kind=? AND id=?",(kind,id)).fetchone()
        if not row:raise KeyError(f'{kind}/{id}')
        return json.loads(row[0])
    def list(self,kind):
        with self.connect() as conn:rows=conn.execute("SELECT body FROM resources WHERE kind=? ORDER BY id",(kind,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def delete(self,kind,id):
        with self.connect() as conn:conn.execute("DELETE FROM resources WHERE kind=? AND id=?",(kind,id))
