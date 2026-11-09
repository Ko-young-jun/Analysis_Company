from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root='data'):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'economy.sqlite3'
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS series(id TEXT PRIMARY KEY, metadata TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, finished_at TEXT);
            CREATE TABLE IF NOT EXISTS observations(
              run_id INTEGER NOT NULL REFERENCES runs(id), series_id TEXT NOT NULL REFERENCES series(id),
              country TEXT NOT NULL, period TEXT NOT NULL, value REAL,
              release_date TEXT, provider_updated TEXT, status TEXT NOT NULL, raw_path TEXT,
              PRIMARY KEY(run_id,series_id,country,period));
            CREATE INDEX IF NOT EXISTS observation_lookup ON observations(series_id,country,period,run_id);
            CREATE TABLE IF NOT EXISTS attempts(
              id INTEGER PRIMARY KEY, run_id INTEGER REFERENCES runs(id), series_id TEXT,
              url TEXT, status TEXT, message TEXT, rows INTEGER, raw_path TEXT, created_at TEXT);
            ''')

    def connect(self):
        c = sqlite3.connect(self.db, timeout=30)
        c.execute('PRAGMA foreign_keys=ON')
        return c

    def register(self, meta):
        required = {'id', 'name', 'category', 'unit', 'frequency', 'source', 'source_url', 'adjustment', 'price_basis', 'note'}
        if not required <= meta.keys():
            raise ValueError('지표 메타데이터 필수 필드 누락')
        with self.connect() as c:
            previous = c.execute('SELECT metadata FROM series WHERE id=?', (meta['id'],)).fetchone()
            if previous:
                old = json.loads(previous[0])
                for key in ('unit', 'frequency', 'source', 'adjustment', 'price_basis'):
                    if old[key] != meta[key]:
                        raise ValueError(f'{key} 변경은 새로운 지표 ID를 사용해야 합니다')
            c.execute('INSERT INTO series VALUES(?,?) ON CONFLICT(id) DO UPDATE SET metadata=excluded.metadata',
                      (meta['id'], json.dumps(meta, ensure_ascii=False)))

    def catalog(self):
        with self.connect() as c:
            return [json.loads(r[0]) for r in c.execute('SELECT metadata FROM series ORDER BY id')]

    def begin_run(self):
        with self.connect() as c:
            return c.execute('INSERT INTO runs(started_at) VALUES(?)', (now(),)).lastrowid

    def finish_run(self, run):
        with self.connect() as c:
            c.execute('UPDATE runs SET finished_at=? WHERE id=?', (now(), run))

    def raw(self, body: bytes, suffix='json'):
        directory = self.root / 'raw'
        directory.mkdir(exist_ok=True)
        path = directory / f'{hashlib.sha256(body).hexdigest()}.{suffix}'
        if not path.exists():
            with path.open('xb') as f:
                f.write(body)
        return str(path.relative_to(self.root))

    def attempt(self, run, series, url, status, message='', rows=0, raw_path=None):
        with self.connect() as c:
            c.execute('INSERT INTO attempts(run_id,series_id,url,status,message,rows,raw_path,created_at) VALUES(?,?,?,?,?,?,?,?)',
                      (run, series, url, status, message, rows, raw_path, now()))

    def save_observations(self, run, series, rows, raw_path=None):
        meta = next(m for m in self.catalog() if m['id'] == series)
        values = []
        seen = set()
        for row in rows:
            period = str(row['period'])
            try:
                p = pd.Period(period, freq={'A': 'Y'}.get(meta['frequency'], meta['frequency']))
            except (ValueError, TypeError) as exc:
                raise ValueError(f'잘못된 기준기간: {period}') from exc
            if str(p) != period:
                raise ValueError(f'기준기간 표준형 필요: {period} → {p}')
            key = (row['country'], period)
            if key in seen:
                raise ValueError('중복 관측값')
            seen.add(key)
            value = row['value']
            if value is not None and (isinstance(value, bool) or not math.isfinite(float(value))):
                raise ValueError('유효하지 않은 수치')
            release = row.get('release_date')
            if release:
                datetime.fromisoformat(release)
            values.append((run, series, key[0], period, value, release,
                           row.get('provider_updated'), row.get('status', '미확인'), raw_path))
        with self.connect() as c:
            c.executemany('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?)', values)

    def frame(self, as_of=None):
        with self.connect() as c:
            q = '''SELECT o.*, r.started_at AS retrieved_at FROM observations o JOIN runs r ON r.id=o.run_id
                 WHERE r.finished_at IS NOT NULL AND o.run_id=(SELECT MAX(i.run_id) FROM observations i JOIN runs ri ON ri.id=i.run_id WHERE ri.finished_at IS NOT NULL AND i.series_id=o.series_id
                   AND i.country=o.country AND i.period=o.period AND i.run_id<=?)'''
            df = pd.read_sql_query(q, c, params=(as_of if as_of is not None else 2**63-1,))
        if df.empty:
            return df
        meta = pd.DataFrame(self.catalog()).drop(columns=['country'], errors='ignore').rename(columns={'id':'series_id'})
        return df.merge(meta, on='series_id', validate='many_to_one').sort_values(['series_id','country','period'])

    def history(self, series, country):
        with self.connect() as c:
            return pd.read_sql_query('SELECT * FROM observations WHERE series_id=? AND country=? ORDER BY run_id,period', c, params=(series,country))

    def attempts(self):
        with self.connect() as c:
            return pd.read_sql_query('SELECT * FROM attempts ORDER BY id DESC', c)

    def runs(self):
        with self.connect() as c:
            return pd.read_sql_query('SELECT * FROM runs ORDER BY id DESC', c)
