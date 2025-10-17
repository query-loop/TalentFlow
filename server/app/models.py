from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, String, Integer, Text, DateTime
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
import os


# Resolve a stable default SQLite path relative to this file (server/app)
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SQLITE_DIR = os.path.abspath(os.path.join(_HERE, "..", ".run"))
_DEFAULT_SQLITE_PATH = os.path.join(_DEFAULT_SQLITE_DIR, "talentflow.sqlite")
_DEFAULT_DB_URL = f"sqlite:///{_DEFAULT_SQLITE_PATH}"

# Allow override via env; otherwise, use the stable absolute default
_ALT_TURSO_URL = os.environ.get("TURSO_URL")
DB_URL = os.environ.get("DATABASE_URL", _ALT_TURSO_URL or _DEFAULT_DB_URL)
LIBSQL_AUTH_TOKEN = os.environ.get("LIBSQL_AUTH_TOKEN") or os.environ.get("TURSO_TOKEN") or os.environ.get("TURSO_AUTH_TOKEN")
# When set to a truthy value, do NOT fall back to local SQLite if remote libsql is unavailable
DB_REQUIRE_REMOTE = os.environ.get("DATABASE_REQUIRE_REMOTE") or os.environ.get("TURSO_REQUIRE_REMOTE")


class Base(DeclarativeBase):
    pass


class GeneratedResume(Base):
    __tablename__ = "generated_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job: Mapped[str] = mapped_column(Text)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    skills: Mapped[str] = mapped_column(Text)  # JSON string
    experience: Mapped[str] = mapped_column(Text)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def _ensure_sqlite_dir(url: str):
    try:
        u = make_url(url)
        if u.drivername.startswith("sqlite") and u.database and u.database != ":memory:":
            os.makedirs(os.path.dirname(u.database), exist_ok=True)
    except Exception:
        # Best-effort; if parsing fails, fall back to creating default dir when using default URL
        if url == _DEFAULT_DB_URL:
            os.makedirs(_DEFAULT_SQLITE_DIR, exist_ok=True)

def _to_sqlalchemy_url(url: str) -> str:
    """If using libsql://, translate to sqlite+libsql:// and inject auth/tls params when available."""
    if url.startswith("libsql://"):
        rest = url[len("libsql://"):]
        base, q = (rest.split("?", 1) + [""])[:2]
        # Some servers redirect to add trailing slash; include it proactively to avoid 308
        # Ensure trailing slash, which some gateways expect
        if not base.endswith("/"):
            base = base + "/"
        params = []
        if q:
            params.append(q)
        # Force TLS and HTTP/1.1 to avoid redirects or protocol issues
        if "tls=" not in q:
            params.append("tls=1")
        if "use_http_1_1=" not in q:
            params.append("use_http_1_1=1")
        qp = ("?" + "&".join(p for p in params if p)) if params else ""
        return f"sqlite+libsql://{base}{qp}"
    return url

# Compute final URL and prepare engine kwargs
FINAL_DB_URL = _to_sqlalchemy_url(DB_URL)

# Ensure local sqlite file directory exists
try:
    _parsed = make_url(FINAL_DB_URL)
except Exception:
    _parsed = None

if _parsed and _parsed.drivername == "sqlite" and _parsed.database and _parsed.database != ":memory:":
    _ensure_sqlite_dir(FINAL_DB_URL)

_engine_kwargs = {"echo": False, "future": True}

if _parsed and _parsed.drivername == "sqlite+libsql":
    # Provide auth token via connect args; driver expects 'auth_token'
    _ca = {}
    if LIBSQL_AUTH_TOKEN:
        _ca["auth_token"] = LIBSQL_AUTH_TOKEN
    if _ca:
        _engine_kwargs["connect_args"] = _ca
    # Enable connection health checks for remote DB
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(FINAL_DB_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db():
    global engine, SessionLocal, FINAL_DB_URL
    # Skip create_all when pointing to remote libsql without auth; app can still start.
    try:
        parsed = make_url(FINAL_DB_URL)
    except Exception:
        parsed = None
    if parsed and parsed.drivername == "sqlite+libsql" and not LIBSQL_AUTH_TOKEN:
        return
    # Try a quick connection test; if libsql fails (e.g., redirect), fall back to local sqlite for dev.
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as e:
        if parsed and parsed.drivername == "sqlite+libsql":
            if DB_REQUIRE_REMOTE:
                # Explicitly configured to require remote DB; surface the error
                raise
            print(f"[models] libsql connection failed: {e}. Falling back to local SQLite at {_DEFAULT_SQLITE_PATH}.")
            FINAL_DB_URL = _DEFAULT_DB_URL
            _ensure_sqlite_dir(FINAL_DB_URL)
            engine = create_engine(FINAL_DB_URL, echo=False, future=True)
            SessionLocal.configure(bind=engine)
        else:
            # Re-raise for non-libsql errors
            raise
    # Ensure directory exists for sqlite file (covered by _ensure_sqlite_dir)
    Base.metadata.create_all(engine)
    # Ensure a write-through alias `v2_pipeline` exists for compatibility (as a view + INSTEAD OF triggers).
    try:
        with engine.connect() as conn:
            # Detect if v2_pipeline exists as a table; if so, migrate rows and drop it to avoid duplication.
            try:
                row = conn.exec_driver_sql(
                    "SELECT name, type FROM sqlite_master WHERE name='v2_pipeline'"
                ).fetchone()
            except Exception:
                row = None
            if row and row[1] == 'table':
                # Migrate any rows that don't already exist into pipelines_v2
                try:
                    conn.exec_driver_sql(
                        "INSERT INTO pipelines_v2 (id,name,company,created_at_ms,jd_id,resume_id,statuses_json) "
                        "SELECT vp.id, vp.name, vp.company, vp.created_at_ms, vp.jd_id, vp.resume_id, vp.statuses_json "
                        "FROM v2_pipeline vp WHERE NOT EXISTS (SELECT 1 FROM pipelines_v2 p WHERE p.id = vp.id)"
                    )
                except Exception as e:
                    print(f"[models] v2_pipeline data copy skipped/failed: {e}")
                # Drop the physical table to replace with a view
                try:
                    conn.exec_driver_sql("DROP TABLE IF EXISTS v2_pipeline")
                except Exception as e:
                    print(f"[models] failed to drop legacy v2_pipeline table: {e}")

            # Create view if not exists
            conn.exec_driver_sql(
                "CREATE VIEW IF NOT EXISTS v2_pipeline AS "
                "SELECT id, name, company, created_at_ms, jd_id, resume_id, statuses_json FROM pipelines_v2"
            )

            # Create INSTEAD OF triggers to make the view writable (insert/update/delete)
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS v2_pipeline_insert "
                "INSTEAD OF INSERT ON v2_pipeline BEGIN "
                "INSERT INTO pipelines_v2 (id,name,company,created_at_ms,jd_id,resume_id,statuses_json) "
                "VALUES (NEW.id,NEW.name,NEW.company,NEW.created_at_ms,NEW.jd_id,NEW.resume_id,NEW.statuses_json); END;"
            )
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS v2_pipeline_update "
                "INSTEAD OF UPDATE ON v2_pipeline BEGIN "
                "UPDATE pipelines_v2 SET name=NEW.name, company=NEW.company, created_at_ms=NEW.created_at_ms, "
                "jd_id=NEW.jd_id, resume_id=NEW.resume_id, statuses_json=NEW.statuses_json WHERE id=OLD.id; END;"
            )
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS v2_pipeline_delete "
                "INSTEAD OF DELETE ON v2_pipeline BEGIN "
                "DELETE FROM pipelines_v2 WHERE id=OLD.id; END;"
            )
    except Exception as e:
        # Non-fatal; some backends may not support VIEW/TRIGGER creation or may lack permissions
        print(f"[models] skipping v2_pipeline alias provisioning: {e}")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at_ms: Mapped[int] = mapped_column(Integer)
    jd_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resume_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    statuses_json: Mapped[str] = mapped_column(Text)  # JSON string for statuses


class ResumeLibrary(Base):
    __tablename__ = "resume_library"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(50))  # e.g., 'uploaded' | 'draft'
    source: Mapped[str] = mapped_column(String(100))  # e.g., 'upload' | 'generate'
    text: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Dedicated V2 pipelines table to decouple from v1 and avoid ID filtering edge cases
class PipelineV2Record(Base):
    __tablename__ = "pipelines_v2"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at_ms: Mapped[int] = mapped_column(Integer)
    jd_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    resume_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Store both statuses and artifacts JSON as a single JSON string for simplicity
    statuses_json: Mapped[str] = mapped_column(Text)
