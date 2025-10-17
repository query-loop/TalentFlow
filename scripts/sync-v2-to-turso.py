#!/usr/bin/env python3
"""
Sync pipelines_v2 rows from a local SQLite DB to Turso (libsql).

Usage:
  LOCAL_DB_URL=sqlite:////absolute/path/to/talentflow.sqlite \
  TURSO_URL=libsql://<your-db>.turso.io \
  TURSO_TOKEN=<token> \
  python scripts/sync-v2-to-turso.py

Defaults:
  - LOCAL_DB_URL defaults to the dev sqlite file at server/.run/talentflow.sqlite if it exists.
  - Remote picks DATABASE_URL or TURSO_URL; requires LIBSQL_AUTH_TOKEN/TURSO_TOKEN.
"""
from __future__ import annotations
import os, sys
from sqlalchemy import create_engine, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOCAL = os.path.join(ROOT, 'server', '.run', 'talentflow.sqlite')

def to_sa_url(url: str) -> str:
    if url.startswith('libsql://'):
        return 'sqlite+libsql://' + url[len('libsql://'):]
    return url

def main():
    local_url = os.environ.get('LOCAL_DB_URL') or (f'sqlite:///{DEFAULT_LOCAL}' if os.path.exists(DEFAULT_LOCAL) else None)
    remote_url_raw = os.environ.get('DATABASE_URL') or os.environ.get('TURSO_URL')
    token = os.environ.get('LIBSQL_AUTH_TOKEN') or os.environ.get('TURSO_TOKEN') or os.environ.get('TURSO_AUTH_TOKEN')
    if not local_url:
        print('LOCAL_DB_URL not set and default dev DB not found. Nothing to sync.')
        return 2
    if not remote_url_raw:
        print('Set DATABASE_URL or TURSO_URL for the remote (Turso).')
        return 2

    remote_url = to_sa_url(remote_url_raw)
    local_engine = create_engine(local_url, future=True)
    ca = {}
    if remote_url.startswith('sqlite+libsql://') and token:
        ca['auth_token'] = token
    remote_engine = create_engine(remote_url, future=True, connect_args=ca)

    with local_engine.connect() as L, remote_engine.connect() as R:
        # Ensure remote table exists
        R.exec_driver_sql('CREATE TABLE IF NOT EXISTS pipelines_v2 (\n'
                          '  id TEXT PRIMARY KEY,\n'
                          '  name TEXT NOT NULL,\n'
                          '  company TEXT,\n'
                          '  created_at_ms INTEGER NOT NULL,\n'
                          '  jd_id TEXT,\n'
                          '  resume_id TEXT,\n'
                          '  statuses_json TEXT NOT NULL\n'
                          ')')

        ids_remote = {row[0] for row in R.exec_driver_sql('SELECT id FROM pipelines_v2').fetchall()}
        rows_local = L.exec_driver_sql('SELECT id,name,company,created_at_ms,jd_id,resume_id,statuses_json FROM pipelines_v2').fetchall()
        to_insert = [r for r in rows_local if r[0] not in ids_remote]
        print(f'Local rows: {len(rows_local)}; Remote existing: {len(ids_remote)}; To insert: {len(to_insert)}')
        if not to_insert:
            print('Nothing to sync.')
            return 0
        R.execute(text('BEGIN'))
        try:
            for r in to_insert:
                R.exec_driver_sql(
                    'INSERT INTO pipelines_v2 (id,name,company,created_at_ms,jd_id,resume_id,statuses_json) VALUES (?,?,?,?,?,?,?)',
                    r
                )
            R.execute(text('COMMIT'))
            print('Sync complete.')
        except Exception as e:
            R.execute(text('ROLLBACK'))
            print('Sync failed:', e)
            return 1

if __name__ == '__main__':
    sys.exit(main())
